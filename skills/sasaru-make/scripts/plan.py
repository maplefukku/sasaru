# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7", "jsonschema>=4.23,<5"]
# ///
"""Write the production plan cut.json for one cut from a playbook and the maker's content.

usage: plan.py <playbook.md|id> <content.yaml> [--route ID] [--duration SEC]
               [--allow-talking-head] [--home DIR] [--no-quote]

exit codes: 0 plan written, 2 input error, 3 refused (schema, talking head, rights).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import yaml

SKILL_DIR = Path(__file__).resolve().parent.parent
PLUGIN_DIR = SKILL_DIR.parent.parent
SCHEMA = PLUGIN_DIR / "schema" / "playbook.schema.json"
ADAPTERS = SKILL_DIR / "adapters"
GATE = PLUGIN_DIR / "skills" / "sasaru-gate" / "scripts" / "check_cut.py"

GENERATIVE_NEEDS = ["image-gen", "t2v", "i2v", "v2v", "tts"]
FOOTAGE_NEEDS = ["own-footage", "screen-capture", "stock-footage"]
SUDDEN = {"hard-cut", "zoom-cut", "match-cut", "whip", "glitch"}
RENDERABLE_CONTAINERS = {"hyperframes", "html-canvas"}
SOUND_LICENSES = {"CC0-1.0", "CC-BY-4.0", "own-work"}
CREDIT_LICENSES = {"CC-BY-4.0"}
FONT_LICENSES = {"OFL-1.1", "Apache-2.0"}

RESOLUTION = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}
HEADLINE_FLOOR = 0.04
HEADLINE_BASE = 0.057
ROLE_DEFAULT_CAP = {"subtitle": 0.035, "label": 0.03, "counter": 0.04}
ROLE_DEFAULT_CY = {"headline": 0.42, "subtitle": 0.66, "label": 0.2, "counter": 0.16}
# White-core height of one line per font-size em. Noto Sans JP 900 measured 0.94 on kanji lines and 0.87 on kana
# lines (white > 220, row profile); other faces differ, so the gate measures the render.
CAP_PER_EM = 0.92
# A line with no CJK glyph only reaches cap height: 0.74 em measured on a Latin word in Noto Sans JP 700.
LATIN_CAP_PER_EM = 0.74
LINE_HEIGHT = 1.2
DEFAULT_MIN_HOLD = 1.0
EMPHASIS = re.compile(r"\[\[(.+?)\]\]")


class Yaml12Loader(yaml.SafeLoader):
    """YAML 1.2 booleans and no timestamps, so yes/no/on/off stay strings and dates stay strings."""


Yaml12Loader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag not in ("tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp")]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
Yaml12Loader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF")
)


def load_yaml(text: str):
    return yaml.load(text, Loader=Yaml12Loader)


class InputError(Exception):
    pass


class Refused(Exception):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def home_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    if os.environ.get("SASARU_HOME"):
        return Path(os.environ["SASARU_HOME"]).resolve()
    return (Path.cwd() / "sasaru").resolve()


def find_playbook(ref: str, home: Path) -> Path:
    p = Path(ref)
    if p.suffix == ".md" and p.exists():
        return p.resolve()
    for cand in (home / "playbooks" / f"{ref}.md", PLUGIN_DIR / "playbooks" / f"{ref}.md"):
        if cand.exists():
            return cand
    raise InputError(f"playbook not found: {ref}")


def read_playbook(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---\n")
    if not text.startswith("---\n") or len(parts) < 3:
        raise InputError(f"{path}: no YAML frontmatter")
    fm = load_yaml(parts[1])
    validator = jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8")), format_checker=jsonschema.FormatChecker()
    )
    errors = sorted(validator.iter_errors(fm), key=lambda e: list(e.path))
    if errors:
        msgs = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors[:10]]
        raise Refused("playbook fails the schema:\n  " + "\n  ".join(msgs))
    if fm["id"] != path.stem:
        raise Refused(f"playbook id {fm['id']} does not match file name {path.stem}")
    ids = [b["id"] for b in fm["beats"]]
    beats = sorted(fm["beats"], key=lambda b: b["tIn"])
    for a, b in zip(beats, beats[1:]):
        if b["tIn"] < a["tOut"] - 1e-6:
            raise Refused(f"beats {a['id']} and {b['id']} overlap")
    refs = [z["at"]["beat"] for z in fm["camera"]["zooms"]] + [t["at"]["beat"] for t in fm["camera"]["transitions"]]
    refs += [m["beat"] for m in fm["camera"]["moves"]]
    refs += [s["at"]["beat"] for s in fm["audio"]["sfx"] if "at" in s]
    if fm["audio"]["bgm"].get("entersAt"):
        refs.append(fm["audio"]["bgm"]["entersAt"]["beat"])
    for layer in fm["captions"]:
        refs += layer["beats"]
    missing = sorted(set(refs) - set(ids))
    if missing:
        raise Refused(f"playbook points at beats that do not exist: {missing}")
    return fm


def char_width(ch: str) -> float:
    if ch.isspace():
        return 0.3
    return 1.0 if unicodedata.east_asian_width(ch) in ("W", "F", "A") else 0.6


def line_scale(line: list[dict]) -> float:
    chars = [ch for r in line for ch in r["t"] if not ch.isspace()]
    if chars and all(char_width(ch) < 1.0 for ch in chars):
        return round(CAP_PER_EM / LATIN_CAP_PER_EM, 4)
    return 1.0


def parse_card(text: str) -> list[list[dict]]:
    lines = []
    for raw in str(text).split("\n"):
        runs, pos = [], 0
        for m in EMPHASIS.finditer(raw):
            if m.start() > pos:
                runs.append({"t": raw[pos:m.start()], "em": False})
            runs.append({"t": m.group(1), "em": True})
            pos = m.end()
        if pos < len(raw):
            runs.append({"t": raw[pos:], "em": False})
        lines.append(runs)
    return lines


def plain(lines: list[list[dict]]) -> str:
    return "\n".join("".join(r["t"] for r in line) for line in lines)


def count_chars(lines: list[list[dict]]) -> int:
    return sum(1 for line in lines for r in line for ch in r["t"] if not ch.isspace())


class Plan:
    def __init__(self, pb: dict, pb_path: Path, content: dict, content_path: Path, args):
        self.pb, self.pb_path, self.c, self.c_path, self.args = pb, pb_path, content, content_path, args
        self.base = content_path.parent
        self.steps: list[dict] = []
        self.deviations: list[dict] = []
        self.warnings: list[str] = []
        self.credits: list[str] = []

    def file_record(self, rec: dict, what: str) -> dict:
        if not rec or not rec.get("file"):
            raise InputError(f"{what}: file is required")
        raw = os.path.expanduser(os.path.expandvars(str(rec["file"])))
        if "$" in raw:
            raise InputError(f"{what}: unset variable in {rec['file']}")
        path = (self.base / raw).resolve()
        if not path.exists():
            raise InputError(f"{what}: {path} does not exist")
        out = {"file": str(path), "sha256": sha256(path)}
        for k in ("license", "source", "author", "credit"):
            if rec.get(k):
                out[k] = rec[k]
        return out

    def sound_record(self, rec: dict, what: str) -> dict:
        """Copy a licensed sound file into the cut folder, where the gate reads every audio source."""
        out = self.file_record(rec, what)
        src = Path(out.pop("file"))
        dest = self.cut_dir / "audio" / f"{out['sha256'][:8]}-{src.name}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copyfile(src, dest)
        out["path"] = str(dest.relative_to(self.cut_dir))
        out["sourceFile"] = str(src)
        return out

    def route(self) -> dict:
        routes = self.pb["routes"]
        want = self.args.route or self.c.get("route")
        r = next((r for r in routes if r["id"] == want), None) if want else next(r for r in routes if r["default"])
        if r is None:
            raise InputError(f"route {want} is not in the playbook")
        if r["talkingHead"] and not self.args.allow_talking_head:
            raise Refused(
                f"route {r['id']} puts a talking person on screen. Run only when the maker names it for this cut "
                "(--allow-talking-head). See sasaru-principle-no-talking-head-by-default."
            )
        return r

    def timeline(self) -> None:
        fmt = self.pb["format"]
        band = fmt["durationSec"]
        ref = band.get("reference") or max(b["tOut"] for b in self.pb["beats"])
        dur = self.args.duration or self.c.get("durationSec") or min(max(ref, band["min"]), band["max"])
        if not band["min"] <= dur <= band["max"]:
            raise InputError(f"duration {dur}s is outside the playbook band {band['min']}–{band['max']}s")
        self.ref, self.dur, self.ratio = ref, float(dur), float(dur) / ref
        self.w, self.h = RESOLUTION[fmt["aspect"]]
        self.beats = []
        for b in sorted(self.pb["beats"], key=lambda b: b["tIn"]):
            self.beats.append({
                "id": b["id"], "role": b["role"], "refIn": b["tIn"], "refOut": b["tOut"],
                "tIn": round(b["tIn"] * self.ratio, 3), "tOut": round(b["tOut"] * self.ratio, 3),
            })
        self.beats[-1]["tOut"] = round(self.dur, 3)
        self.beat = {b["id"]: b for b in self.beats}

    def at(self, a: dict) -> float:
        return round(min((self.beat[a["beat"]]["refIn"] + a["offsetSec"]) * self.ratio, self.dur), 3)

    def safe(self) -> dict:
        return self.pb["format"].get("safeArea") or {"top": 0.0, "bottom": 0.0, "left": 0.0, "right": 0.0}

    def layers(self) -> list[dict]:
        out = []
        brand = self.c.get("brand") or {}
        layer_fonts = brand.get("layerFonts") or {}
        for L in self.pb["captions"]:
            lid, role = L["id"], L["role"]
            cap, cap_src = L["capHeightRatio"], "playbook"
            if role == "headline" and (cap is None or cap < HEADLINE_FLOOR):
                self.deviations.append({
                    "path": f"captions.{lid}.capHeightRatio", "from": cap, "to": HEADLINE_BASE,
                    "reason": "headline below 0.04 or unmeasured; raised to the headline band (sasaru-principle-captions-read-as-headlines)",
                })
                cap, cap_src = HEADLINE_BASE, "raised"
            elif cap is None:
                cap, cap_src = ROLE_DEFAULT_CAP[role], "default"
                self.deviations.append({"path": f"captions.{lid}.capHeightRatio", "from": None, "to": cap,
                                        "reason": f"unmeasured; make's default for role {role}"})
            pos = dict(L["position"])
            if pos["cx"] is None:
                pos["cx"] = 0.5
                self.deviations.append({"path": f"captions.{lid}.position.cx", "from": None, "to": 0.5, "reason": "unmeasured; centered"})
            if pos["cy"] is None:
                pos["cy"] = ROLE_DEFAULT_CY[role]
                self.deviations.append({"path": f"captions.{lid}.position.cy", "from": None, "to": pos["cy"],
                                        "reason": f"unmeasured; make's default for role {role}"})
            em = L["emphasis"]
            em_out = None
            if em:
                color = em["color"] or brand.get("accent")
                em_out = {"scale": em["scale"] or 1.0, "color": color}
            font_px = cap * self.h / CAP_PER_EM
            stroke = None
            if L["stroke"]:
                stroke = {"color": L["stroke"]["color"], "px": round(L["stroke"]["px1080"] * self.w / 1080, 2)}
            out.append({
                "id": lid, "role": role, "beats": L["beats"] or [b["id"] for b in self.beats],
                "unit": L["unit"], "writingMode": L["writingMode"],
                "font": {"class": L["font"]["class"], "weight": L["font"]["weight"],
                         "family": layer_fonts.get(lid) or self.font_family()},
                "capHeightRatio": cap, "capHeightSource": cap_src, "fontPx": round(font_px, 2),
                "emphasis": em_out, "color": brand.get("ink") or L["color"], "stroke": stroke, "shadow": L["shadow"],
                "plate": L["plate"], "position": pos, "linesMax": L["linesMax"], "charsPerCard": L["charsPerCard"],
                "motionIn": L["motionIn"], "motionOut": L["motionOut"], "show": L["show"], "leadSec": L["leadSec"],
                "hide": L["hide"], "minHoldSec": L["minHoldSec"], "lastCard": L["lastCard"],
            })
            if L["writingMode"] == "vertical":
                self.warnings.append(f"{lid}: vertical writing is rendered with CSS writing-mode; width fitting is not checked")
        return out

    def font_family(self) -> str:
        fonts = self.pb["fonts"]
        brand_font = (self.c.get("brand") or {}).get("font")
        if brand_font:
            return brand_font["family"]
        return fonts[0]["family"] if fonts else "sans-serif"

    def fonts(self) -> list[dict]:
        brand_font = (self.c.get("brand") or {}).get("font")
        out = []
        if brand_font:
            rec = {"family": brand_font["family"], "license": brand_font.get("license"), "source": brand_font.get("source")}
            if brand_font.get("file"):
                rec.update(self.file_record(brand_font, "brand.font"))
            out.append(rec)
        out += [dict(f) for f in self.pb["fonts"]]
        for f in out:
            f["redistributable"] = f.get("license") in FONT_LICENSES
            if not f["redistributable"]:
                self.warnings.append(
                    f"font {f['family']} ({f.get('license')}) is not OFL or Apache; the maker supplies the file and keeps its license record"
                )
                if not f.get("file"):
                    self.steps.append({"id": f"font-{f['family']}", "status": "要決定",
                                       "what": f"font {f['family']} has no redistributable source; give brand.font.file"})
        return out

    def cards(self, layers: list[dict]) -> list[dict]:
        beats_content = self.c.get("beats") or {}
        cards = []
        voiced = self.pb["format"]["speech"] != "none"
        for L in layers:
            for bid in [b["id"] for b in self.beats]:
                texts = (beats_content.get(bid) or {}).get(L["id"]) or []
                if isinstance(texts, str):
                    texts = [texts]
                if texts and bid not in L["beats"]:
                    self.warnings.append(f"{L['id']} does not appear in {bid}; its cards there are ignored")
                    continue
                if not texts:
                    continue
                b = self.beat[bid]
                parsed = [parse_card(t) for t in texts]
                weights = [max(count_chars(p), 2) for p in parsed]
                span = b["tOut"] - b["tIn"]
                t = b["tIn"]
                for i, (p, wt) in enumerate(zip(parsed, weights)):
                    slot = span * wt / sum(weights)
                    cards.append({"layer": L["id"], "beat": bid, "index": i, "lines": p, "text": plain(p),
                                  "slotIn": round(t, 3), "slotOut": round(t + slot, 3)})
                    t += slot
        if voiced and cards:
            self.warnings.append("voiceover onsets are estimated from character counts; replace with voice timings when available")
        order = {b["id"]: i for i, b in enumerate(self.beats)}
        for L in layers:
            mine = [c for c in cards if c["layer"] == L["id"]]
            for c in mine:
                b = self.beat[c["beat"]]
                start = c["slotIn"]
                if L["show"] == "before-onset":
                    start = max(0.0, start - (L["leadSec"] or 0.0))
                elif L["show"] == "beat-start" and c["index"] == 0:
                    start = b["tIn"]
                c["start"] = round(start, 3)
            for i, c in enumerate(mine):
                b = self.beat[c["beat"]]
                nxt = mine[i + 1] if i + 1 < len(mine) else None
                if L["hide"] == "next-card":
                    if nxt and order[nxt["beat"]] - order[c["beat"]] <= 1:
                        end = nxt["start"]
                    else:
                        end = b["tOut"]
                elif L["hide"] == "beat-end":
                    end = b["tOut"]
                else:
                    end = c["slotOut"]
                if nxt and nxt["start"] < end:
                    end = nxt["start"]
                if nxt is None and L["lastCard"] == "hold-to-end":
                    end = self.dur
                c["end"] = round(end, 3)
            self.check_layer_cards(L, mine)
        hook = next(b for b in self.beats if b["role"] == "hook")
        if self.pb["hook"]["firstFrameHasText"]:
            first = [c for c in cards if c["beat"] == hook["id"]]
            if not first or min(c["start"] for c in first) > 0:
                self.warnings.append("hook.firstFrameHasText is true but no card starts at 0 s")
            for c in first:
                if c["start"] == 0:
                    c["forceCutIn"] = True
                    self.deviations.append({"path": f"cards.{c['layer']}.{c['beat']}.{c['index']}.motionIn",
                                            "from": next(L for L in layers if L["id"] == c["layer"])["motionIn"],
                                            "to": "cut", "reason": "hook.firstFrameHasText: the first frame shows the card in full"})
        last_end = max((c["end"] for c in cards), default=0)
        if cards and last_end < self.dur:
            self.warnings.append(f"no card is on screen at the last frame ({last_end}s < {self.dur}s)")
        return sorted(cards, key=lambda c: (c["start"], c["layer"]))

    def check_layer_cards(self, L: dict, mine: list[dict]) -> None:
        hold = L["minHoldSec"] if L["minHoldSec"] is not None else DEFAULT_MIN_HOLD
        safe = self.safe()
        cx = L["position"]["cx"]
        if L["position"]["align"] == "center":
            avail = 2 * min(cx - safe["left"], 1 - safe["right"] - cx) * self.w
        elif L["position"]["align"] == "left":
            avail = (1 - safe["right"] - cx) * self.w
        else:
            avail = (cx - safe["left"]) * self.w
        for c in mine:
            n = count_chars(c["lines"])
            tag = f"{L['id']} card {c['beat']}#{c['index']}"
            if c["end"] - c["start"] < hold - 1e-6:
                self.warnings.append(f"{tag} holds {c['end'] - c['start']:.2f}s, under {hold}s")
            lo, hi = L["charsPerCard"]["min"], L["charsPerCard"]["max"]
            if not lo <= n <= hi:
                self.warnings.append(f"{tag} has {n} characters, outside {lo}–{hi}")
            if len(c["lines"]) > L["linesMax"]:
                self.warnings.append(f"{tag} has {len(c['lines'])} lines, over linesMax {L['linesMax']}")
            scale = L["emphasis"]["scale"] if L["emphasis"] else 1.0
            for line in c["lines"]:
                kinds = {r["em"] for r in line if r["t"].strip()}
                if L["emphasis"] and scale != 1.0 and kinds == {True, False}:
                    c.setdefault("mixedLines", True)
            if c.get("mixedLines"):
                self.deviations.append({"path": f"cards.{L['id']}.{c['beat']}.{c['index']}.emphasis.scale",
                                        "from": scale, "to": 1.0,
                                        "reason": "one line would mix sizes; emphasis keeps its color only on mixed lines"})
            if any(r["em"] for line in c["lines"] for r in line) and not L["emphasis"]:
                self.warnings.append(f"{tag} marks emphasis but layer {L['id']} has none; shown plain")
            width = 0.0
            c["lineScales"] = [line_scale(line) for line in c["lines"]]
            for line, ls in zip(c["lines"], c["lineScales"]):
                full = all(r["em"] for r in line if r["t"].strip()) and any(r["t"].strip() for r in line)
                s = (scale if (L["emphasis"] and full) else 1.0) * ls
                lw = sum(char_width(ch) for r in line for ch in r["t"]) * L["fontPx"] * s
                lw += 2 * (L["stroke"]["px"] if L["stroke"] else 0)
                width = max(width, lw)
            fit = min(1.0, avail * 0.98 / width) if width else 1.0
            c["fitScale"] = round(fit, 4)
            if fit < 1.0:
                eff = L["capHeightRatio"] * fit
                self.deviations.append({"path": f"cards.{L['id']}.{c['beat']}.{c['index']}.size", "from": 1.0,
                                        "to": round(fit, 3), "reason": "card wider than the safe area; scaled to fit"})
                if L["role"] == "headline" and eff < HEADLINE_FLOOR:
                    self.warnings.append(f"{tag} had to shrink to cap height {eff:.3f}, under the headline floor 0.04; split the card")

    def camera(self) -> dict:
        cam = self.pb["camera"]
        moves = []
        for m in cam["moves"]:
            b = self.beat[m["beat"]]
            moves.append({"beat": m["beat"], "move": m["move"], "start": b["tIn"], "end": b["tOut"]})
        zooms = [{"t": self.at(z["at"]), "scaleFrom": z["scaleFrom"], "scaleTo": z["scaleTo"],
                  "durSec": round(z["durSec"] * self.ratio, 3), "easing": z["easing"]} for z in cam["zooms"]]
        trans = [{"t": self.at(t["at"]), "type": t["type"]} for t in cam["transitions"]]
        return {"moves": moves, "zooms": zooms, "transitions": trans}

    def sound(self, layers: list[dict], cards: list[dict], camera: dict) -> dict:
        pa = self.pb["audio"]
        ca = self.c.get("audio") or {}
        out = {"bgm": None, "sfx": [], "voice": None, "referenceAudioUsed": False, "loudnessLufs": -14}
        if ca.get("referenceAudio") or ca.get("reference"):
            raise Refused("the reference video's audio is never an input (sasaru-principle-sound-from-a-licensed-file)")
        bgm = ca.get("bgm")
        if pa["bgm"]["present"]:
            if bgm:
                rec = self.sound_record(bgm, "audio.bgm")
                self.check_sound_license(rec, "bgm")
                enters = pa["bgm"].get("entersAt")
                rec["startAt"] = self.at(enters) if enters else 0.0
                rec["offsetSec"] = float(bgm.get("offsetSec", 0))
                rec["fadeOutSec"] = 0.4
                out["bgm"] = rec
            else:
                self.steps.append({"id": "bgm", "status": "要決定",
                                   "what": "the playbook has BGM; give audio.bgm with file, license, source"})
        elif bgm:
            self.warnings.append("the playbook has no BGM; audio.bgm is ignored")
        files = {s["type"]: s for s in (ca.get("sfx") or [])}
        for s in pa["sfx"]:
            cue = s["cue"]
            src = files.get(s["type"])
            if not src:
                self.steps.append({"id": f"sfx-{s['type']}", "status": "要決定",
                                   "what": f"no file for sfx type {s['type']} (cue {cue}); give audio.sfx[{{type: {s['type']}}}]"})
                continue
            rec = self.sound_record(src, f"audio.sfx {s['type']}")
            self.check_sound_license(rec, f"sfx {s['type']}")
            if "at" in s:
                times = [self.at(s["at"])]
            elif cue == "card-in":
                first = layers[0]["id"] if layers else None
                times = [c["start"] for c in cards if c["layer"] == first]
            elif cue == "cut":
                times = [b["tIn"] for b in self.beats[1:]]
            elif cue == "zoom":
                times = [z["t"] for z in camera["zooms"]]
            elif cue == "payoff":
                times = [b["tIn"] for b in self.beats if b["role"] == "payoff"]
            elif cue == "beat-drop" and out["bgm"]:
                times = [out["bgm"]["startAt"]]
            else:
                times = []
                self.warnings.append(f"sfx {s['type']} cue {cue} has no time; give at in the playbook")
            gain = float(src.get("gainDb", -6))
            for t in times:
                out["sfx"].append({**rec, "type": s["type"], "cue": cue, "t": t, "gainDb": gain})
        voice_kind = pa["voice"]
        if self.pb["format"]["speech"] == "voiceover" or voice_kind != "none":
            v = ca.get("voice")
            if voice_kind == "own-voiceover":
                if v and v.get("file"):
                    rec = self.sound_record(v, "audio.voice")
                    rec["license"] = rec.get("license", "own-work")
                    out["voice"] = rec
                else:
                    self.steps.append({"id": "voice", "status": "要決定", "what": "own voiceover: give audio.voice.file"})
            elif voice_kind == "tts-voiceover" and isinstance(v, dict) and v.get("file"):
                out["voice"] = self.sound_record(v, "audio.voice")
                self.check_sound_license(out["voice"], "voice")
            elif voice_kind == "tts-voiceover":
                text = (v or {}).get("text") or "\n".join(c["text"] for c in cards if c["layer"] == (layers[0]["id"] if layers else ""))
                self.adapter_step("tts", {"text": text, "durationSec": self.dur}, beat=None)
            if out["bgm"] and (out["voice"] or voice_kind == "tts-voiceover"):
                level = self.pb["audio"]["bgm"].get("levelDbUnderVoice")
                level = level if level is not None else (bgm or {}).get("levelDbUnderVoice")
                if level is None:
                    self.steps.append({"id": "bgm-level", "status": "要決定",
                                       "what": "BGM level under the voice is unmeasured; give audio.bgm.levelDbUnderVoice (no default)"})
                else:
                    out["bgm"]["levelDbUnderVoice"] = level
        sources = []
        if out["voice"]:
            sources.append({"role": "voice", "path": out["voice"]["path"], "license": out["voice"].get("license"),
                            "atSec": 0.0, "inSec": 0.0})
        if out["bgm"]:
            b = out["bgm"]
            sources.append({"role": "bgm", "path": b["path"], "license": b.get("license"),
                            "atSec": b["startAt"], "inSec": b["offsetSec"]})
        for s in out["sfx"]:
            sources.append({"role": "sfx", "path": s["path"], "license": s.get("license"), "atSec": s["t"], "inSec": 0.0})
        out["sources"] = sources
        return out

    def check_sound_license(self, rec: dict, what: str) -> None:
        lic = rec.get("license")
        if lic in CREDIT_LICENSES:
            if not rec.get("credit"):
                raise Refused(f"{what}: {lic} needs a credit line (credit)")
            self.credits.append(rec["credit"])
        if lic not in SOUND_LICENSES:
            rec["needsRightsConfirmation"] = True
            self.steps.append({"id": f"rights-{what}", "status": "要承認",
                               "what": f"{what} license {lic!r} is not a default source (CC0-1.0, CC-BY-4.0, own-work); "
                                       "the maker confirms the rights, then render with --accept-license"})

    def adapter_step(self, need: str, payload: dict, beat: str | None) -> None:
        script = ADAPTERS / f"{need.replace('-', '_')}.py"
        sid = f"{need}-{beat}" if beat else need
        req = {"need": need, "cutId": self.cut_id, "beat": beat, "durationSec": payload.get("durationSec"),
               "aspect": self.pb["format"]["aspect"], "fps": self.pb["format"]["fps"],
               "prompt": payload.get("prompt"), "text": payload.get("text"), "inputs": payload.get("inputs", [])}
        req = {k: v for k, v in req.items() if v is not None or k in ("need", "cutId", "beat")}
        req_path = self.cut_dir / "requests" / f"{sid}.json"
        req_path.parent.mkdir(parents=True, exist_ok=True)
        req_path.write_text(json.dumps(req, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        step = {"id": sid, "need": need, "beat": beat, "request": str(req_path)}
        if not script.exists():
            step.update(status="未実装", what=f"adapter {script.name} is not in adapters/; this step is skipped")
            self.steps.append(step)
            return
        step["sendCommand"] = (f"uv run --script {script} run --request {req_path} "
                               f"--out {self.cut_dir / 'generated' / sid} --cap-usd <approved> --yes")
        if self.args.no_quote:
            step.update(status="要承認", what="quote skipped (--no-quote); quote, then send only after approval")
            self.steps.append(step)
            return
        try:
            res = subprocess.run(["uv", "run", "--script", str(script), "quote", "--request", str(req_path)],
                                 capture_output=True, text=True, timeout=120)
            quote = json.loads(res.stdout) if res.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            quote = None
        if quote is None:
            step.update(status="要承認", what="quote failed; check the adapter, then quote again")
        else:
            step.update(status="要承認", quote=quote,
                        what=f"quote {quote.get('usdMin')}–{quote.get('usdMax')} USD; send only after the maker approves")
        self.steps.append(step)

    def visuals(self, route: dict) -> dict:
        assets = self.c.get("assets") or {}
        footage = []
        for bid, rec in assets.items():
            if bid not in self.beat:
                raise InputError(f"assets.{bid}: no such beat")
            r = self.file_record(rec, f"assets.{bid}")
            r["beat"] = bid
            r["kind"] = rec.get("kind", "own-footage")
            footage.append(r)
        needs = route["needs"]
        for need in needs:
            if need in FOOTAGE_NEEDS and not any(f["kind"] == need for f in footage):
                self.steps.append({"id": need, "status": "要決定",
                                   "what": f"route {route['id']} needs {need}; give assets.<beat> with kind {need}"})
        gens = self.c.get("generate") or {}
        for need in [n for n in needs if n in GENERATIVE_NEEDS and n != "tts"]:
            mine = {b: g for b, g in gens.items() if g.get("need") == need}
            if not mine:
                self.adapter_step(need, {}, beat=None)
                if self.steps[-1]["status"] != "未実装":
                    self.steps[-1].update(status="要決定", what=f"no prompt for {need} in content.generate")
            for bid, g in mine.items():
                b = self.beat[bid]
                self.adapter_step(need, {"prompt": g.get("prompt"), "inputs": g.get("inputs", []),
                                         "durationSec": round(b["tOut"] - b["tIn"], 3)}, beat=bid)
        if "tts" in needs and self.pb["audio"]["voice"] != "tts-voiceover":
            v = (self.c.get("audio") or {}).get("voice")
            self.adapter_step("tts", {"text": v.get("text") if isinstance(v, dict) else None,
                                      "durationSec": self.dur}, beat=None)
        brand = self.c.get("brand") or {}
        sudden = [t for t in self.pb["camera"]["transitions"] if t["type"] in SUDDEN]
        if sudden and not brand.get("groundAlt"):
            covered = {f["beat"] for f in footage}
            bare = [t["at"]["beat"] for t in sudden if t["at"]["beat"] not in covered]
            if bare:
                self.warnings.append(f"transitions into {bare} change nothing on a plain background; give brand.groundAlt")
        return {"background": {"color": brand.get("ground", "#111111"), "pattern": brand.get("pattern", "plain"),
                               "patternColor": brand.get("patternColor"), "groundAlt": brand.get("groundAlt")},
                "footage": footage}

    def build(self) -> dict:
        self.cut_id = self.c.get("cut")
        if not self.cut_id or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", self.cut_id):
            raise InputError("content.cut must be a kebab-case cut id")
        self.cut_dir = home_dir(self.args.home) / "cuts" / self.cut_id
        self.cut_dir.mkdir(parents=True, exist_ok=True)
        route = self.route()
        self.timeline()
        layers = self.layers()
        fonts = self.fonts()
        cards = self.cards(layers)
        camera = self.camera()
        visuals = self.visuals(route)
        audio = self.sound(layers, cards, camera)
        if route["container"] not in RENDERABLE_CONTAINERS:
            self.steps.append({"id": "compose", "status": "未実装",
                               "what": f"container {route['container']} has no renderer in sasaru-make; "
                                       "render_code_motion.py renders hyperframes and html-canvas"})
        else:
            if route["container"] == "html-canvas":
                self.deviations.append({"path": "routes.container", "from": "html-canvas", "to": "hyperframes",
                                        "reason": "HTML is rendered through HyperFrames, sasaru-make's default container"})
            blocked = [s["id"] for s in self.steps if s["status"] in ("要決定", "未実装") and s["id"] in FOOTAGE_NEEDS]
            self.steps.append({"id": "compose", "status": "blocked" if blocked else "todo",
                               "what": "render the picture with HyperFrames, mix sound with ffmpeg",
                               "command": f"uv run --script {SKILL_DIR / 'scripts' / 'render_code_motion.py'} {self.cut_dir}"})
        self.steps.append({"id": "gate", "status": "todo", "what": "cut check by sasaru-gate (check_cut.py)",
                           "command": f"uv run --script {GATE} {self.cut_dir} --fetch-models --out {self.cut_dir / 'gate.json'}"})
        fmt = self.pb["format"]
        for c in cards:
            c["emphasis"] = any(r["em"] for line in c["lines"] for r in line)
        caption_style = {}
        for L in layers:
            st = {"fontFamily": L["font"]["family"], "fontClass": L["font"]["class"], "weight": L["font"]["weight"],
                  "shadow": L["shadow"], "plate": L["plate"], "color": L["color"]}
            caption_style[L["id"]] = st
        explicit = bool(self.args.route or self.c.get("route"))
        return {
            "schema": "sasaru-cut/1",
            "cutId": self.cut_id,
            "plannedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "playbook": self.pb["id"],
            "playbookPath": os.path.relpath(self.pb_path, self.cut_dir),
            "playbookSha256": sha256(self.pb_path),
            "playbookStatus": self.pb["status"],
            "content": {"path": str(self.c_path), "sha256": sha256(self.c_path)},
            "video": "cut.mp4",
            "route": route["id"],
            "routeRequestedByMaker": explicit and not route["default"],
            "container": route["container"],
            "routeInfo": {k: route[k] for k in ("needs", "paidApi", "talkingHead", "status")},
            "stretch": round(self.ratio, 4),
            "costUsd": 0,
            "captionStyle": caption_style,
            "format": {"aspect": fmt["aspect"], "fps": fmt["fps"], "width": self.w, "height": self.h,
                       "durationSec": self.dur, "band": fmt["durationSec"], "referenceSec": self.ref,
                       "stretch": round(self.ratio, 4), "safeArea": self.safe(),
                       "onCamera": fmt["onCamera"], "speech": fmt["speech"]},
            "beats": self.beats,
            "layers": layers,
            "cards": cards,
            "camera": camera,
            "visuals": visuals,
            "audio": audio,
            "fonts": fonts,
            "credits": self.credits,
            "steps": self.steps,
            "deviations": self.deviations,
            "warnings": self.warnings,
            "render": None,
        }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("playbook")
    ap.add_argument("content")
    ap.add_argument("--route")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--allow-talking-head", action="store_true")
    ap.add_argument("--home")
    ap.add_argument("--no-quote", action="store_true")
    args = ap.parse_args()
    try:
        home = home_dir(args.home)
        pb_path = find_playbook(args.playbook, home)
        pb = read_playbook(pb_path)
        c_path = Path(args.content).resolve()
        if not c_path.exists():
            raise InputError(f"content not found: {c_path}")
        content = load_yaml(c_path.read_text(encoding="utf-8")) or {}
        plan = Plan(pb, pb_path, content, c_path, args).build()
    except InputError as e:
        print(f"input error: {e}", file=sys.stderr)
        return 2
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 3
    out = home_dir(args.home) / "cuts" / plan["cutId"] / "cut.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "cutJson": str(out),
        "route": plan["route"],
        "durationSec": plan["format"]["durationSec"],
        "stretch": plan["format"]["stretch"],
        "cards": len(plan["cards"]),
        "steps": {s["id"]: s["status"] for s in plan["steps"]},
        "deviations": len(plan["deviations"]),
        "warnings": plan["warnings"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
