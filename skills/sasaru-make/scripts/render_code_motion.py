# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Render a planned cut on the code-only route: HyperFrames draws the picture, ffmpeg mixes the licensed sound.

usage: render_code_motion.py <cut_dir> [--hyperframes VERSION] [--workers N] [--quality Q]
                             [--accept-license] [--html-only]

Reads <cut_dir>/cut.json written by plan.py. Writes <cut_dir>/hf/ (the composition), picture.mp4 (no sound),
mix.wav (BGM and effects from their own files), cut.mp4, and updates cut.json.

exit codes: 0 rendered, 2 input error, 3 refused (blocked step, unconfirmed rights, render failure).
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HYPERFRAMES = "0.8.196"
GSAP_URL = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"
GOOGLE_FONTS_API = "https://api.github.com/repos/google/fonts/contents/{lic}/{dir}"
LICENSE_DIRS = {"ofl": "OFL-1.1", "apache": "Apache-2.0"}
STATIC_WEIGHTS = {"thin": 100, "extralight": 200, "light": 300, "regular": 400, "medium": 500,
                  "semibold": 600, "bold": 700, "extrabold": 800, "black": 900}
EASE = {"linear": "none", "ease-in": "power2.in", "ease-out": "power2.out", "ease-in-out": "power2.inOut"}
LOUDNESS_TP = -1.5
ENV = {"HYPERFRAMES_SKIP_SKILLS": "1", "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1"}


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


def cache_dir() -> Path:
    d = Path(os.environ.get("SASARU_CACHE") or Path.home() / ".cache" / "sasaru")
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "sasaru-make"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest.with_suffix(dest.suffix + ".part"), "wb") as f:
        shutil.copyfileobj(r, f)
    dest.with_suffix(dest.suffix + ".part").rename(dest)
    return dest


def google_font(family: str) -> dict:
    """Download a Google Fonts family (OFL or Apache only) from github.com/google/fonts into the cache."""
    dirname = re.sub(r"[^a-z0-9]", "", family.lower())
    root = cache_dir() / "fonts" / dirname
    meta = root / "sasaru-font.json"
    if meta.exists():
        return json.loads(meta.read_text())
    listing = None
    for lic in LICENSE_DIRS:
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    GOOGLE_FONTS_API.format(lic=lic, dir=dirname), headers={"User-Agent": "sasaru-make"}), timeout=60) as r:
                listing, lic_dir = json.load(r), lic
                break
        except urllib.error.HTTPError:
            continue
    if listing is None:
        raise InputError(f"font {family}: not found under ofl/ or apache/ in google/fonts; give brand.font.file")
    files, license_file = [], None
    for item in listing:
        name = item["name"]
        if name.endswith(".ttf"):
            files.append({"path": str(fetch(item["download_url"], root / name)), "name": name})
        elif name in ("OFL.txt", "LICENSE.txt"):
            license_file = str(fetch(item["download_url"], root / name))
    if not files:
        raise InputError(f"font {family}: no .ttf in google/fonts/{lic_dir}/{dirname}")
    rec = {"family": family, "license": LICENSE_DIRS[lic_dir], "repoDir": f"{lic_dir}/{dirname}",
           "files": files, "licenseFile": license_file}
    meta.write_text(json.dumps(rec, indent=2))
    return rec


def font_faces(files: list[dict], css_family: str, assets: Path, idx: int) -> tuple[str, list[dict]]:
    rules, used = [], []
    for j, f in enumerate(files):
        name = f["name"]
        if "Italic" in name:
            continue
        stem = Path(name).stem
        if "[" in stem:
            weight = "100 900"
        else:
            suffix = stem.split("-")[-1].lower()
            if suffix not in STATIC_WEIGHTS:
                continue
            weight = str(STATIC_WEIGHTS[suffix])
        local = f"f{idx}-{j}.ttf"
        shutil.copyfile(f["path"], assets / local)
        rules.append(f'@font-face {{ font-family: "{css_family}"; src: url("assets/fonts/{local}"); '
                     f"font-weight: {weight}; font-style: normal; }}")
        used.append({"file": name, "sha256": sha256(Path(f["path"])), "weight": weight})
    return "\n".join(rules), used


def resolve_fonts(plan: dict, hf: Path) -> tuple[str, dict, list[dict]]:
    assets = hf / "assets" / "fonts"
    assets.mkdir(parents=True, exist_ok=True)
    families = []
    for L in plan["layers"]:
        if L["font"]["family"] not in families:
            families.append(L["font"]["family"])
    css, names, records = [], {}, []
    for i, fam in enumerate(families):
        rec = next((f for f in plan["fonts"] if f["family"] == fam), None)
        if rec is None:
            raise InputError(f"font {fam} is not in the plan's fonts")
        css_family = f"sasaru-font-{i}"
        if rec.get("file"):
            files = [{"path": rec["file"], "name": Path(rec["file"]).name}]
            if "[" not in files[0]["name"] and files[0]["name"].split("-")[-1].split(".")[0].lower() not in STATIC_WEIGHTS:
                files[0]["name"] = "Maker[wght]" + Path(rec["file"]).suffix
            got = {"license": rec.get("license"), "licenseFile": None, "repoDir": None}
        elif rec.get("redistributable"):
            got = google_font(fam)
            files = got["files"]
        else:
            raise Refused(f"font {fam} ({rec.get('license')}) is not redistributable and has no file")
        rule, used = font_faces(files, css_family, assets, i)
        if not used:
            raise InputError(f"font {fam}: no usable upright file")
        css.append(rule)
        names[fam] = css_family
        records.append({"family": fam, "license": got.get("license") or rec.get("license"),
                        "source": rec.get("source"), "repoDir": got.get("repoDir"),
                        "licenseFile": got.get("licenseFile"), "files": used})
    return "\n".join(css), names, records


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def card_html(card: dict, layer: dict, mode: str) -> str:
    em = layer["emphasis"]
    out_lines = []
    unit_i = 0
    scales = card.get("lineScales") or [1.0] * len(card["lines"])
    for line, ls in zip(card["lines"], scales):
        nonblank = [r for r in line if r["t"].strip()]
        full = bool(nonblank) and all(r["em"] for r in nonblank)
        parts = []
        for r in line:
            text = r["t"]
            if mode == "typewriter":
                pieces = list(text)
            elif mode == "word-by-word":
                pieces = [p for p in re.split(r"(\s+|(?<=[、。！？!?,.]))", text) if p]
            else:
                pieces = [text]
            inner = []
            for p in pieces:
                if mode in ("typewriter", "word-by-word") and p.strip():
                    inner.append(f'<span class="u u{unit_i}">{esc(p)}</span>')
                    unit_i += 1
                else:
                    inner.append(esc(p))
            body = "".join(inner)
            if r["em"] and em:
                style = f"color:{em['color']};" if em.get("color") else ""
                if full and em["scale"] != 1.0:
                    style += f"font-size:{em['scale']}em;"
                parts.append(f'<span class="em" style="{style}">{body}</span>')
            else:
                parts.append(body)
        size = f' style="font-size:{ls}em"' if ls != 1.0 else ""
        out_lines.append(f'<div class="ln"{size}>{"".join(parts) or "&nbsp;"}</div>')
    card["_units"] = unit_i
    return "".join(out_lines)


def layer_css(L: dict, fam: str, plan: dict) -> str:
    W, H = plan["format"]["width"], plan["format"]["height"]
    css = [f"font-family:'{fam}';", f"font-weight:{L['font']['weight']};", f"color:{L['color']};",
           f"line-height:1.2;", "white-space:pre;", f"text-align:{L['position']['align']};"]
    if L["stroke"]:
        css.append(f"-webkit-text-stroke:{2 * L['stroke']['px']}px {L['stroke']['color']};paint-order:stroke fill;")
    if L["shadow"]:
        css.append(f"text-shadow:0 {round(H * 0.003)}px {round(H * 0.009)}px rgba(0,0,0,0.45);")
    if L["plate"] != "none":
        dark = int(L["color"][1:3], 16) + int(L["color"][3:5], 16) + int(L["color"][5:7], 16) < 384
        bg = "#FFFFFF" if dark else "rgba(0,0,0,0.62)"
        radius = "999px" if L["plate"] == "pill" else "0.12em"
        css.append(f"background:{bg};border-radius:{radius};padding:0.18em 0.7em;")
    if L["writingMode"] == "vertical":
        css.append("writing-mode:vertical-rl;")
    return "".join(css)


def background_css(bg: dict, H: int) -> str:
    color, pat = bg["color"], bg.get("pattern", "plain")
    line = bg.get("patternColor") or "rgba(255,255,255,0.08)"
    step = round(H / 30)
    if pat == "ruled":
        return (f"background-color:{color};background-image:repeating-linear-gradient(180deg,transparent 0,"
                f"transparent {step - 3}px,{line} {step - 3}px,{line} {step}px);")
    if pat == "grid":
        return (f"background-color:{color};background-image:linear-gradient({line} 2px,transparent 2px),"
                f"linear-gradient(90deg,{line} 2px,transparent 2px);background-size:{step}px {step}px;")
    return f"background-color:{color};"


def js_num(x: float) -> str:
    return f"{x:.4f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))


def build_html(plan: dict, font_css: str, names: dict, hf: Path) -> str:
    fmt = plan["format"]
    W, H, D, fps = fmt["width"], fmt["height"], fmt["durationSec"], fmt["fps"]
    layers = {L["id"]: L for L in plan["layers"]}
    order = {L["id"]: i for i, L in enumerate(plan["layers"])}
    tl: list[str] = []
    media_dir = hf / "assets" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    footage = []
    for i, f in enumerate(plan["visuals"]["footage"]):
        b = next(x for x in plan["beats"] if x["id"] == f["beat"])
        src = Path(f["file"])
        local = f"m{i}{src.suffix.lower()}"
        shutil.copyfile(src, media_dir / local)
        attrs = (f'id="m{i}" class="clip media" data-start="{js_num(b["tIn"])}" '
                 f'data-duration="{js_num(b["tOut"] - b["tIn"])}" data-track-index="0"')
        if src.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            footage.append(f'<img {attrs} src="assets/media/{local}" alt="">')
        else:
            footage.append(f'<video {attrs} src="assets/media/{local}" muted playsinline></video>')

    for m in plan["camera"]["moves"]:
        s, e = m["start"], m["end"]
        dur = max(e - s, 0.001)
        mv = m["move"]
        if mv == "static":
            tl.append(f'tl.set("#mv",{{scale:1,x:0,y:0,rotation:0}},{js_num(s)});')
        elif mv in ("push-in", "pull-out"):
            a, b = (1, 1.06) if mv == "push-in" else (1.06, 1)
            tl.append(f'tl.fromTo("#mv",{{scale:{a},x:0,y:0,rotation:0}},{{scale:{b},duration:{js_num(dur)},ease:"none"}},{js_num(s)});')
        elif mv in ("pan", "tilt"):
            prop = "x" if mv == "pan" else "y"
            tl.append(f'tl.fromTo("#mv",{{scale:1.06,{prop}:0}},{{{prop}:{-round(W * 0.03)},duration:{js_num(dur)},ease:"none"}},{js_num(s)});')
        elif mv == "orbit":
            tl.append(f'tl.fromTo("#mv",{{scale:1.06,rotation:0}},{{rotation:1.5,duration:{js_num(dur)},ease:"none"}},{js_num(s)});')
        elif mv == "handheld":
            tl.append(f'tl.set("#mv",{{scale:1.04}},{js_num(s)});')
            n = max(1, int(dur / 0.25))
            for k in range(n):
                t = s + k * dur / n
                x = round(6 * math.sin(k * 1.7), 2)
                y = round(5 * math.sin(k * 2.3 + 1), 2)
                tl.append(f'tl.to("#mv",{{x:{x},y:{y},duration:{js_num(dur / n)},ease:"sine.inOut"}},{js_num(t)});')

    for z in plan["camera"]["zooms"]:
        if z["easing"] == "snap" or z["durSec"] <= 0:
            tl.append(f'tl.set("#zm",{{scale:{z["scaleTo"]}}},{js_num(z["t"])});')
        else:
            tl.append(f'tl.fromTo("#zm",{{scale:{z["scaleFrom"]}}},{{scale:{z["scaleTo"]},duration:{js_num(z["durSec"])},'
                      f'ease:"{EASE[z["easing"]]}"}},{js_num(z["t"])});')

    alt = plan["visuals"]["background"].get("groundAlt")
    grounds = [plan["visuals"]["background"]["color"], alt] if alt else None
    sudden_i = 0
    for tr in plan["camera"]["transitions"]:
        t, kind = tr["t"], tr["type"]
        if grounds and kind in ("hard-cut", "zoom-cut", "match-cut", "whip", "glitch"):
            sudden_i += 1
            tl.append(f'tl.set("#paper",{{backgroundColor:"{grounds[sudden_i % 2]}"}},{js_num(t)});')
        if kind == "fade":
            tl.append(f'tl.fromTo("#flash",{{opacity:0}},{{opacity:1,duration:0.12,ease:"none"}},{js_num(max(0, t - 0.12))});')
            tl.append(f'tl.to("#flash",{{opacity:0,duration:0.12,ease:"none"}},{js_num(t)});')
        elif kind == "whip":
            tl.append(f'tl.fromTo("#tr",{{x:{round(W * 0.3)}}},{{x:0,duration:0.2,ease:"power3.out"}},{js_num(t)});')
        elif kind == "zoom-cut":
            tl.append(f'tl.fromTo("#tr",{{scale:1.12}},{{scale:1,duration:0.18,ease:"power3.out"}},{js_num(t)});')
        elif kind == "glitch":
            f1 = 1 / fps
            tl.append(f'tl.set("#tr",{{x:18}},{js_num(t)});tl.set("#tr",{{x:-14}},{js_num(t + 2 * f1)});'
                      f'tl.set("#tr",{{x:0}},{js_num(t + 4 * f1)});')

    cards_html = []
    styles = []
    for L in plan["layers"]:
        styles.append(f".L-{L['id']}{{{layer_css(L, names[L['font']['family']], plan)}}}")
    for i, c in enumerate(plan["cards"]):
        L = layers[c["layer"]]
        mode = "cut" if c.get("forceCutIn") else L["motionIn"]
        inner = card_html(c, L, mode)
        s, e = c["start"], c["end"]
        dur = e - s
        cx, cy = L["position"]["cx"] * W, L["position"]["cy"] * H
        shift = {"center": "-50%", "left": "0%", "right": "-100%"}[L["position"]["align"]]
        size = L["fontPx"] * c.get("fitScale", 1.0)
        cards_html.append(
            f'<div id="k{i}" class="clip card" data-start="{js_num(s)}" data-duration="{js_num(dur)}" '
            f'data-track-index="{order[L["id"]] + 1}" style="z-index:{10 + order[L["id"]]}">'
            f'<div class="anchor" style="left:{cx:.1f}px;top:{cy:.1f}px;transform:translate({shift},-50%)">'
            f'<div class="txt L-{L["id"]}" style="font-size:{size:.2f}px">{inner}</div></div></div>')
        sel = f"#k{i} .txt"
        if mode == "pop":
            tl.append(f'tl.fromTo("{sel}",{{scale:0.6,opacity:0}},{{scale:1,opacity:1,duration:0.18,ease:"back.out(2)"}},{js_num(s)});')
        elif mode == "fade":
            tl.append(f'tl.fromTo("{sel}",{{opacity:0}},{{opacity:1,duration:0.2,ease:"none"}},{js_num(s)});')
        elif mode == "slide-up":
            tl.append(f'tl.fromTo("{sel}",{{y:{round(H * 0.02)},opacity:0}},{{y:0,opacity:1,duration:0.22,ease:"power2.out"}},{js_num(s)});')
        elif mode == "scale-in":
            tl.append(f'tl.fromTo("{sel}",{{scale:1.15,opacity:0}},{{scale:1,opacity:1,duration:0.2,ease:"power2.out"}},{js_num(s)});')
        elif mode in ("typewriter", "word-by-word"):
            n = c["_units"]
            step = min(0.06 if mode == "typewriter" else 0.18, dur * 0.5 / max(n, 1))
            tl.append(f'tl.set("{sel} .u",{{opacity:0}},{js_num(s)});')
            for k in range(n):
                tl.append(f'tl.set("{sel} .u{k}",{{opacity:1}},{js_num(s + k * step)});')
        held_to_end = abs(e - D) < 1e-6
        if not held_to_end and L["motionOut"] in ("fade", "slide") and dur > 0.4:
            extra = f",y:{-round(H * 0.015)}" if L["motionOut"] == "slide" else ""
            tl.append(f'tl.to("{sel}",{{opacity:0{extra},duration:0.15,ease:"none"}},{js_num(e - 0.15)});')

    bg_css = background_css(plan["visuals"]["background"], H)
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width={W}, height={H}">
<script src="assets/gsap.min.js"></script>
<style>
{font_css}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{W}px; height:{H}px; overflow:hidden; background:{plan['visuals']['background']['color']}; }}
#root {{ position:relative; width:{W}px; height:{H}px; overflow:hidden; }}
.clip {{ position:absolute; inset:0; }}
#bg, #mv, #zm, #tr {{ position:absolute; inset:0; transform-origin:50% 50%; }}
#paper {{ position:absolute; inset:-10%; {bg_css} }}
.media {{ width:100%; height:100%; object-fit:cover; }}
.card {{ pointer-events:none; }}
.anchor {{ position:absolute; }}
.txt {{ display:inline-block; transform-origin:50% 50%; }}
#flash {{ background:#000; opacity:0; z-index:50; }}
{chr(10).join(styles)}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{js_num(D)}" data-width="{W}" data-height="{H}" data-fps="{js_num(fps)}">
<div id="bg">
<div id="mv"><div id="zm"><div id="tr"><div id="paper"></div>
{chr(10).join(footage)}
</div></div></div>
</div>
{chr(10).join(cards_html)}
<div id="flash" class="clip" data-start="0" data-duration="{js_num(D)}" data-track-index="9"></div>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(tl)}
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body>
</html>
"""


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env={**os.environ, **ENV})


def mix_audio(plan: dict, cut_dir: Path, out_wav: Path) -> dict:
    D = plan["format"]["durationSec"]
    a = plan["audio"]
    inputs, chains, labels = [], [], []
    if a.get("voice"):
        inputs += ["-i", str(cut_dir / a["voice"]["path"])]
        k = len(inputs) // 2 - 1
        chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,loudnorm=I=-20:TP={LOUDNESS_TP},"
                      f"aresample=48000,apad,atrim=0:{D}[v]")
        labels.append("[v]")
    if a.get("bgm"):
        b = a["bgm"]
        inputs += ["-i", str(cut_dir / b["path"])]
        k = len(inputs) // 2 - 1
        delay = int(round(b["startAt"] * 1000))
        level = ""
        if a.get("voice") and b.get("levelDbUnderVoice") is not None:
            level = f",loudnorm=I=-20:TP={LOUDNESS_TP},aresample=48000,volume={b['levelDbUnderVoice']}dB"
        fade = max(0.0, D - b.get("fadeOutSec", 0.4))
        chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=start={b.get('offsetSec', 0)},"
                      f"asetpts=PTS-STARTPTS{level},adelay={delay}|{delay},apad,atrim=0:{D},"
                      f"afade=t=out:st={fade}:d={b.get('fadeOutSec', 0.4)}[b]")
        labels.append("[b]")
    for j, s in enumerate(a.get("sfx", [])):
        inputs += ["-i", str(cut_dir / s["path"])]
        k = len(inputs) // 2 - 1
        delay = int(round(s["t"] * 1000))
        chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={s['gainDb']}dB,"
                      f"adelay={delay}|{delay},apad,atrim=0:{D}[s{j}]")
        labels.append(f"[s{j}]")
    if not labels:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(D),
               "-c:a", "pcm_s16le", "-fflags", "+bitexact", str(out_wav)]
        target = None
    else:
        target = plan["audio"].get("loudnessLufs", -14)
        graph = ";".join(chains) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest," \
                                   f"loudnorm=I={target}:TP={LOUDNESS_TP}:LRA=11,aresample=48000,atrim=0:{D}[out]"
        cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[out]",
               "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", "-fflags", "+bitexact", "-flags:a", "+bitexact",
               str(out_wav)]
    res = run(cmd)
    if res.returncode != 0:
        raise Refused(f"ffmpeg mix failed: {res.stderr[-800:]}")
    return {"inputs": len(labels), "loudnessTargetLufs": target, "truePeakDb": LOUDNESS_TP if target else None,
            "command": cmd}


def probe(path: Path) -> dict:
    res = run(["ffprobe", "-v", "error", "-show_entries",
               "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
               "-of", "json", str(path)])
    return json.loads(res.stdout or "{}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cut_dir")
    ap.add_argument("--hyperframes", default=HYPERFRAMES)
    ap.add_argument("--workers", default="1")
    ap.add_argument("--quality", default="delivery")
    ap.add_argument("--accept-license", action="store_true")
    ap.add_argument("--html-only", action="store_true")
    args = ap.parse_args()
    cut_dir = Path(args.cut_dir).resolve()
    cut_json = cut_dir / "cut.json"
    try:
        if not cut_json.exists():
            raise InputError(f"{cut_json} not found; run plan.py first")
        plan = json.loads(cut_json.read_text(encoding="utf-8"))
        steps = {s["id"]: s for s in plan["steps"]}
        compose = steps.get("compose")
        if not compose or compose["status"] in ("未実装", "blocked"):
            raise Refused(f"compose step is {compose and compose['status']}: {compose and compose['what']}")
        rights = [s for s in plan["steps"] if s["id"].startswith("rights-") and s["status"] == "要承認"]
        if rights and not args.accept_license:
            raise Refused("sound with a non-default license; the maker confirms rights, then --accept-license: "
                          + ", ".join(s["id"] for s in rights))
        skipped = [s["id"] for s in plan["steps"] if s["status"] in ("未実装", "要決定", "要承認") and not s["id"].startswith("rights-")]
        if shutil.which("ffmpeg") is None or shutil.which("npx") is None:
            raise InputError("ffmpeg and npx are required")

        hf = cut_dir / "hf"
        if hf.exists():
            shutil.rmtree(hf)
        (hf / "assets").mkdir(parents=True)
        gsap = fetch(GSAP_URL, cache_dir() / "vendor" / "gsap-3.14.2.min.js")
        shutil.copyfile(gsap, hf / "assets" / "gsap.min.js")
        font_css, names, font_records = resolve_fonts(plan, hf)
        (hf / "index.html").write_text(build_html(plan, font_css, names, hf), encoding="utf-8")
        (hf / "meta.json").write_text(json.dumps({"id": plan["cutId"], "name": plan["cutId"]}) + "\n")

        hfcmd = ["npx", "-y", f"hyperframes@{args.hyperframes}"]
        lint = run([*hfcmd, "lint", "--json", str(hf)], timeout=600)
        try:
            lint_json = json.loads(lint.stdout[lint.stdout.find("{"):]) if "{" in lint.stdout else {"raw": lint.stdout[-2000:]}
        except json.JSONDecodeError:
            lint_json = {"raw": lint.stdout[-2000:]}
        record = {"renderedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "container": {"name": "hyperframes", "version": args.hyperframes, "gsap": "3.14.2",
                                "gsapSha256": sha256(gsap)},
                  "composition": str(hf / "index.html"), "lint": lint_json, "fonts": font_records,
                  "skippedSteps": skipped}
        if args.html_only:
            plan["render"] = record
            cut_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"composition": record["composition"], "lintExit": lint.returncode}, indent=2))
            return 0

        picture = cut_dir / "picture.mp4"
        r = run([*hfcmd, "render", str(hf), "-o", str(picture), "--fps", str(plan["format"]["fps"]),
                 "-q", args.quality, "-w", str(args.workers), "--quiet"], timeout=3600)
        if r.returncode != 0 or not picture.exists():
            raise Refused(f"hyperframes render failed: {(r.stderr or r.stdout)[-1500:]}")
        mix = cut_dir / "mix.wav"
        mix_rec = mix_audio(plan, cut_dir, mix)
        final = cut_dir / "cut.mp4"
        D = plan["format"]["durationSec"]
        m = run(["ffmpeg", "-y", "-v", "error", "-i", str(picture), "-i", str(mix), "-map", "0:v:0", "-map", "1:a:0",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(D), "-map_metadata", "-1",
                 "-fflags", "+bitexact", "-flags:a", "+bitexact", "-movflags", "+faststart", str(final)])
        if m.returncode != 0:
            raise Refused(f"ffmpeg mux failed: {m.stderr[-800:]}")
        if plan.get("credits"):
            (cut_dir / "credits.txt").write_text("\n".join(plan["credits"]) + "\n", encoding="utf-8")
        record.update({
            "picture": {"path": str(picture), "sha256": sha256(picture)},
            "mix": {"path": str(mix), "sha256": sha256(mix), **{k: v for k, v in mix_rec.items() if k != "command"}},
            "output": {"path": str(final), "sha256": sha256(final), "probe": probe(final)},
            "soundSources": sorted({s["path"] for s in plan["audio"]["sources"]}),
        })
        plan["render"] = record
        for s in plan["steps"]:
            if s["id"] == "compose":
                s["status"] = "done"
        cut_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except InputError as e:
        print(f"input error: {e}", file=sys.stderr)
        return 2
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 3
    print(json.dumps({"cut": str(final), "sha256": record["output"]["sha256"], "durationSec": D,
                      "lintErrors": lint_json.get("errorCount", lint_json.get("errors")) if isinstance(lint_json, dict) else None,
                      "skippedSteps": skipped}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
