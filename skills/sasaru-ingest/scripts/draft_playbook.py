# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "pyyaml>=6,<7",
# ]
# ///
"""Write one playbook draft from the measurement JSON in an ingest work directory.

Usage:
  uv run --script draft_playbook.py <work_dir> --id <playbook-id> [--platform other] [--out <path>]
      [--template <templates/playbook.md>] [--json]

Reads from <work_dir> (missing files leave their fields unmeasured; nothing is guessed as a number):
  manifest.json, shots.json, audio/onsets.json            prep.py
  captions.json, captions.ocr.json                        caption_boxes.py
  camera.json                                             camera_motion.py
  audio.json                                              audio_events.py
  people.json                                             people_voice.py
  transcript.json                                         transcribe.py
The shapes are in ../references/measurements.md.

Writes:
  <work_dir>/<id>.md          the draft (default --out). Placeholders the agent must fill start with 未記入.
  <work_dir>/source-text.json caption text and transcript, for the gate's wording check. Never commit it.
                              Entries the agent added with "from": "sheet" are kept on rewrite.
Exit codes: 0 ok, 2 bad input.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
TODO = "未記入"
EASING = {"linear": "linear", "easeIn": "ease-in", "easeOut": "ease-out", "easeInOut": "ease-in-out", "punch": "snap",
          "ease-in": "ease-in", "ease-out": "ease-out", "ease-in-out": "ease-in-out", "snap": "snap"}
MOTION_IN = {"cut", "pop", "fade", "slide-up", "typewriter", "word-by-word", "scale-in", "other"}
MOTION_OUT = {"cut", "fade", "slide", "other"}
MOVES = {"static", "handheld", "push-in", "pull-out", "pan", "tilt", "orbit"}
TRANSITIONS = {"hard-cut", "whip", "zoom-cut", "fade", "match-cut", "glitch"}
ON_CAMERA = {"none", "hands", "body-no-face", "face"}
SPEECH = {"none", "voiceover", "on-camera"}
MIN_BEAT = 0.6
TEMPLATE_LAYER = {
    "unit": "phrase", "writingMode": "horizontal", "font": {"class": "extra-bold-gothic", "weight": 900},
    "color": "#FFFFFF", "stroke": {"color": "#000000", "px1080": 8}, "shadow": True, "plate": "none",
    "charsPerCard": {"min": 2, "max": 10},
}


def load(p):
    return json.loads(p.read_text()) if p.exists() else None


def r(x, n=3):
    return None if x is None else round(float(x), n)


class Evidence:
    """One kind per path; the last call wins, so a later measurement replaces an earlier placeholder."""

    def __init__(self):
        self.kind = {}

    def _set(self, kind, paths):
        for p in paths:
            self.kind[p] = kind

    def m(self, *paths):
        self._set("measured", paths)

    def i(self, *paths):
        self._set("inferred", paths)

    def u(self, *paths):
        self._set("unmeasured", paths)

    def drop(self, *paths):
        for p in paths:
            self.kind.pop(p, None)

    def merge(self, block):
        for kind in ("measured", "inferred", "unmeasured"):
            self._set(kind, (block or {}).get(kind) or [])

    @property
    def measured(self):
        return [p for p, k in self.kind.items() if k == "measured"]

    @property
    def inferred(self):
        return [p for p, k in self.kind.items() if k == "inferred"]

    @property
    def unmeasured(self):
        return [p for p, k in self.kind.items() if k == "unmeasured"]

    def dump(self, fm=None):
        """`list[].field` expands to one `list.<item id>.field` per item, the path form the gate resolves."""
        def expand(paths):
            out = []
            for path in paths:
                head, sep, tail = path.partition("[].")
                if not sep or fm is None:
                    out.append(path)
                    continue
                out += [f"{head}.{item['id']}.{tail}" for item in fm.get(head) or []]
            return list(dict.fromkeys(out))
        return {"measured": expand(self.measured), "inferred": expand(self.inferred), "unmeasured": expand(self.unmeasured)}


def aspect_of(w, h):
    ratio = w / h
    options = {"9:16": 9 / 16, "4:5": 4 / 5, "1:1": 1.0, "16:9": 16 / 9}
    best = min(options, key=lambda k: abs(options[k] - ratio))
    return best, abs(options[best] - ratio) / options[best] < 0.03


def speech_spans(audio_ev, transcript):
    if audio_ev and audio_ev.get("speech") is not None:
        speech = audio_ev["speech"]
        if isinstance(speech, dict):
            speech = speech.get("segments") or []
        out = []
        for s in speech:
            a, b = (s.get("tIn", s.get("tStart")), s.get("tOut", s.get("tEnd"))) if isinstance(s, dict) else (s[0], s[1])
            out.append((float(a), float(b)))
        return out, "audio_events"
    if transcript and transcript.get("reliable") and transcript.get("segments"):
        return [(s["start"], s["end"]) for s in transcript["segments"]], "transcribe"
    return None, None


def boundaries(cands, dur):
    out = []
    for t in sorted(cands):
        if t < MIN_BEAT or t > dur - MIN_BEAT:
            continue
        if out and t - out[-1] < MIN_BEAT:
            continue
        out.append(round(t, 3))
    return out


def make_beats(dur, cards, transcript, onsets, cuts, ev):
    hard = [c["t"] for c in cuts if c.get("confidence") == "high"]
    src = None
    if cards:
        cands, src = [c["tIn"] for c in cards], "caption_boxes のカードの出る秒"
    elif transcript and transcript.get("reliable") and len(transcript.get("segments") or []) >= 2:
        cands, src = [s["start"] for s in transcript["segments"]], "transcribe の区間の始まり"
    elif onsets and onsets.get("silence"):
        cands, src = [b for _, b in onsets["silence"]], "prep の無音区間の終わり（silencedetect）"
    else:
        cands = []
    b = boundaries(cands + hard, dur)
    if hard and not src:
        src = "prep のハードカット"
    if not b:
        b = [round(min(1.5, dur / 3), 3)]
        src = None
    edges = [0.0] + b + [round(dur, 3)]
    n = len(edges) - 1
    beats = []
    for k in range(n):
        role = "hook" if k == 0 else "payoff" if k == n - 1 else "item"
        beats.append({"id": f"b{k + 1}", "role": role, "tIn": edges[k], "tOut": edges[k + 1],
                      "purpose": f"{TODO}: 見る人にとっての役割", "swap": f"{TODO}: 自分のコンテンツから入れるもの"})
    if src:
        ev.m("beats[].tIn", "beats[].tOut")
    else:
        ev.u("beats[].tIn", "beats[].tOut")
    ev.i("beats[].role")
    ev.u("beats[].purpose", "beats[].swap")
    return beats, src


def at(beats, t):
    for b in beats:
        if b["tIn"] <= t < b["tOut"]:
            return {"beat": b["id"], "offsetSec": r(t - b["tIn"])}
    last = beats[-1]
    return {"beat": last["id"], "offsetSec": r(max(0.0, min(t, last["tOut"]) - last["tIn"]))}


def beats_touching(beats, spans):
    ids = [b["id"] for b in beats if any(a < b["tOut"] and e > b["tIn"] for a, e in spans)]
    return [] if len(ids) == len(beats) else ids


def mode(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mode(xs) if xs else None


def caption_layers(cap, beats, onsets_speech, dur, fps, ev):
    """Return (layers, firstFrameHasText, notes). cap is captions.json or None."""
    if cap is None:
        lid = "c1"
        layer = {"id": lid, "role": "headline", "beats": [], **json.loads(json.dumps(TEMPLATE_LAYER)),
                 "capHeightRatio": None, "emphasis": None,
                 "position": {"cx": None, "cy": None, "align": "center"}, "linesMax": 1,
                 "motionIn": "cut", "motionOut": "cut", "show": "onset", "leadSec": None,
                 "hide": "next-card", "minHoldSec": None, "lastCard": "hold-to-end"}
        layer = {k: layer[k] for k in LAYER_ORDER}
        ev.u(f"captions.{lid}", "hook.firstFrameHasText")
        return [layer], False, ["caption_boxes.py が無いので、テロップの層はテンプレートの値の仮置き。"]

    cards = cap.get("cards") or []
    if not cards:
        ev.m("captions", "hook.firstFrameHasText")
        return [], bool(cap.get("firstFrameHasText", False)), ["caption_boxes.py はテロップを検出しなかった。"]

    fragment = (cap.get("playbook") or {}).get("captions")
    if fragment:
        return fragment_layers(cap, fragment, cards, beats, onsets_speech, fps, ev)

    groups = {}
    for c in cards:
        groups.setdefault(c.get("layer") or "c1", []).append(c)
    layers, notes = [], []
    for lid, cs in sorted(groups.items()):
        cs = sorted(cs, key=lambda c: c["tIn"])
        p = f"captions.{lid}"
        hs = [c["capHeightRatio"] for c in cs if c.get("capHeightRatio")]
        base = statistics.median(hs) if hs else None
        emphasis = None
        if hs and max(hs) / base >= 1.15:
            emphasis = {"scale": r(max(hs) / base, 2), "color": None}
            ev.u(f"{p}.emphasis.color")
        cx = r(statistics.median([c["cx"] for c in cs if c.get("cx") is not None]) if any(c.get("cx") is not None for c in cs) else None)
        cy = r(statistics.median([c["cy"] for c in cs if c.get("cy") is not None]) if any(c.get("cy") is not None for c in cs) else None)
        align = "center" if cx is None or abs(cx - 0.5) < 0.05 else "left" if cx < 0.5 else "right"
        holds = [c["tOut"] - c["tIn"] for c in cs]
        gaps = [b["tIn"] - a["tOut"] for a, b in zip(cs, cs[1:])]
        layer = {"id": lid, "role": "headline" if base is None or base >= 0.035 else "subtitle",
                 "beats": beats_touching(beats, [(c["tIn"], c["tOut"]) for c in cs])}
        ev.i(f"{p}.role")
        ev.m(f"{p}.beats", f"{p}.position.align", f"{p}.linesMax", f"{p}.minHoldSec")
        (ev.m if base is not None else ev.u)(f"{p}.capHeightRatio")
        (ev.m if cx is not None else ev.u)(f"{p}.position.cx")
        (ev.m if cy is not None else ev.u)(f"{p}.position.cy")
        if emphasis:
            ev.m(f"{p}.emphasis.scale")
        else:
            ev.i(f"{p}.emphasis")
        for k, default in TEMPLATE_LAYER.items():
            if cap.get(k) is not None:
                layer[k] = cap[k]
                ev.m(f"{p}.{k}")
            else:
                layer[k] = json.loads(json.dumps(default))
                ev.u(f"{p}.{k}")
        layer.update({"capHeightRatio": r(base, 4), "emphasis": emphasis,
                      "position": {"cx": cx, "cy": cy, "align": align},
                      "linesMax": int(max(c.get("lines") or 1 for c in cs))})
        mi = mode([c.get("change") for c in cs if c.get("change") in MOTION_IN])
        layer["motionIn"] = mi or "cut"
        (ev.m if mi else ev.u)(f"{p}.motionIn")
        mo = mode([c.get("changeOut") for c in cs if c.get("changeOut") in MOTION_OUT])
        layer["motionOut"] = mo or "cut"
        (ev.m if mo else ev.u)(f"{p}.motionOut")

        show, lead = "onset", None
        shown = show_from_speech(cs, onsets_speech) if onsets_speech else None
        if shown:
            show, lead = shown
            ev.m(f"{p}.show")
            if lead is not None:
                ev.m(f"{p}.leadSec")
        else:
            ev.u(f"{p}.show", f"{p}.leadSec")
        hide = "next-card" if not gaps or statistics.median(gaps) <= 0.1 else "phrase-end"
        (ev.m if gaps else ev.u)(f"{p}.hide")
        held = cs[-1]["tOut"] >= dur - 1.5 / fps
        ev.m(f"{p}.lastCard")
        layer.update({"show": show, "leadSec": lead, "hide": hide, "minHoldSec": r(min(holds), 2),
                      "lastCard": "hold-to-end" if held else "phrase-end"})
        layers.append({k: layer[k] for k in LAYER_ORDER})
        notes.append(f"{lid}: カード {len(cs)} 枚、白い芯の高さ / 画面高の中央値 {r(base, 4)}、最大 {r(max(hs), 4) if hs else None}、"
                     f"中心 ({cx}, {cy})、最短の表示 {r(min(holds), 2)} 秒。高さの測り方は {cap.get('heightMethod', '未記載')}、"
                     f"白の閾値 {cap.get('threshold', '未記載')}、見た範囲 {cap.get('roi') or '全面'}。")
    first = cap.get("firstFrameHasText")
    if first is None:
        first = cards[0]["tIn"] <= 1.0 / fps
    ev.m("hook.firstFrameHasText")
    return layers, bool(first), notes


def show_from_speech(cs, onsets_speech):
    """Median of (speech onset - card in) over cards within 0.6 s of an onset; None when no card is near one."""
    leads = []
    for c in cs:
        near = min(onsets_speech, key=lambda o: abs(o - c["tIn"]))
        if abs(near - c["tIn"]) <= 0.6:
            leads.append(near - c["tIn"])
    if not leads:
        return None
    med = statistics.median(leads)
    return ("before-onset", r(med, 2)) if med > 0.1 else ("onset", None)


def fragment_layers(cap, fragment, cards, beats, onsets_speech, fps, ev):
    """caption_boxes.py writes whole layers under playbook.captions; key them to these beats and, with speech, set show."""
    ev.merge((cap.get("playbook") or {}).get("evidence"))
    layers, notes = [], []
    for frag in fragment:
        lid = frag["id"]
        p = f"captions.{lid}"
        cs = sorted((c for c in cards if (c.get("layer") or "c1") == lid), key=lambda c: c["tIn"])
        layer = json.loads(json.dumps(frag))
        layer["beats"] = beats_touching(beats, [(c["tIn"], c["tOut"]) for c in cs])
        ev.m(f"{p}.beats")
        shown = show_from_speech(cs, onsets_speech) if onsets_speech and cs else None
        if shown:
            layer["show"], layer["leadSec"] = shown
            ev.m(f"{p}.show")
            if layer["leadSec"] is None:
                ev.drop(f"{p}.leadSec")
            else:
                ev.m(f"{p}.leadSec")
        layers.append({k: layer[k] for k in LAYER_ORDER if k in layer})
        hs = [c["capHeightRatio"] for c in cs if c.get("capHeightRatio")]
        notes.append(f"{lid}: カード {len(cs)} 枚、白い芯の高さ / 画面高の中央値 {r(statistics.median(hs), 4) if hs else None}、"
                     f"最大 {r(max(hs), 4) if hs else None}、中心 ({layer['position']['cx']}, {layer['position']['cy']})、"
                     f"最短の表示 {layer.get('minHoldSec')} 秒。高さの測り方は {cap.get('capHeightMethod') or cap.get('heightMethod', '未記載')}、"
                     f"白の閾値 {cap.get('threshold', '未記載')}、見た範囲 {cap.get('roi') or '全面'}。")
    first = cap.get("firstFrameHasText")
    if first is None:
        first = cards[0]["tIn"] <= 1.0 / fps
    ev.m("hook.firstFrameHasText")
    return layers, bool(first), notes


LAYER_ORDER = ["id", "role", "beats", "unit", "writingMode", "font", "capHeightRatio", "emphasis", "color", "stroke",
               "shadow", "plate", "position", "linesMax", "charsPerCard", "motionIn", "motionOut", "show", "leadSec",
               "hide", "minHoldSec", "lastCard"]


def moves_from_segments(cam, beats):
    """Key camera_motion.py's time segments to the beats the way its own --beats block does."""
    segs = cam["segments"]
    overall = {}
    for s in segs:
        overall[s["move"]] = overall.get(s["move"], 0.0) + s["tEnd"] - s["tStart"]
    fallback = max(overall, key=overall.get) if overall else "static"
    snaps = [(z["tStart"], z["tEnd"]) for z in cam.get("zoomEvents") or [] if z.get("easing") == "snap"]
    moves = []
    for b in beats:
        share, order = {}, []
        for s in segs:
            if s.get("kind", "").startswith("zoom") and any(abs(s["tStart"] - a) < 0.05 and abs(s["tEnd"] - e) < 0.05 for a, e in snaps):
                continue
            ov = min(b["tOut"], s["tEnd"]) - max(b["tIn"], s["tStart"])
            if ov > 0 and s["move"] in MOVES:
                share[s["move"]] = share.get(s["move"], 0.0) + ov
                if s["move"] not in order:
                    order.append(s["move"])
        picked = [m for m in order if m in ("push-in", "pull-out", "pan", "tilt") and share[m] >= 0.3]
        if share.get("handheld", 0.0) >= 0.4 * max(b["tOut"] - b["tIn"], 1e-9):
            picked.append("handheld")
        if not picked:
            picked = [max(share, key=share.get) if share else fallback]
        moves += [{"beat": b["id"], "move": m} for m in picked]
    return moves


def camera_block(cam, beats, cuts, ev):
    notes = []
    if cam and cam.get("transitions") is not None:
        trans = [{"at": at(beats, t.get("t", t.get("atSec"))), "type": t["type"]} for t in cam["transitions"]
                 if t.get("type") in TRANSITIONS and t.get("confidence", "high") in ("high", "medium")]
        ev.m("camera.transitions")
    else:
        trans = [{"at": at(beats, c["t"]), "type": "hard-cut"} for c in cuts if c.get("confidence") == "high"]
        ev.m("camera.transitions")
        notes.append("トランジションは prep のハードカット（確信の高いもの）だけ。種類の見分けは camera_motion.py の担当で未計測。")
    if cam and cam.get("zoomEvents") is not None:
        zooms = []
        for z in cam["zoomEvents"]:
            if z.get("transition"):
                continue
            zooms.append({"at": at(beats, z["tStart"]), "scaleFrom": r(z.get("scaleFrom", 1.0)),
                          "scaleTo": r(z.get("scaleTo", z.get("factor", 1.0))),
                          "durSec": r(z.get("durSec", z["tEnd"] - z["tStart"])), "easing": EASING.get(z.get("easing"), "linear")})
        ev.m("camera.zooms")
    else:
        zooms = []
        ev.u("camera.zooms")
    moves = []
    if cam and cam.get("segments"):
        moves = moves_from_segments(cam, beats)
        ev.m("camera.moves")
    elif cam and cam.get("moves"):
        for b in beats:
            ov = [(min(b["tOut"], m["tOut"]) - max(b["tIn"], m["tIn"]), m["move"]) for m in cam["moves"]
                  if m.get("move") in MOVES and m["tIn"] < b["tOut"] and m["tOut"] > b["tIn"]]
            moves.append({"beat": b["id"], "move": max(ov)[1] if ov else "static"})
        ev.m("camera.moves")
    elif cam and cam.get("shake") is not None:
        sh = cam["shake"]
        s = max(sh.get("txStd", 0), sh.get("tyStd", 0)) if isinstance(sh, dict) else float(sh)
        mv = "handheld" if s > 0.004 else "static"
        moves = [{"beat": b["id"], "move": mv} for b in beats]
        ev.m("camera.moves")
        notes.append(f"揺れ（並進の標準偏差 / 画面幅）{r(s, 4)}。0.004 を超えると handheld とした。")
    else:
        moves = [{"beat": b["id"], "move": "static"} for b in beats]
        ev.u("camera.moves")
    return {"moves": moves, "zooms": zooms, "transitions": trans}, notes


def audio_block(probe, onsets, audio_ev, beats, cards, cuts, zooms_t, voice_kind, ev):
    notes = []
    voice = {"none": "none", "voiceover": "own-voiceover"}[voice_kind]
    if not probe["hasAudio"]:
        ev.m("audio.bgm.present", "audio.sfx", "audio.voice")
        return {"bgm": {"present": False}, "sfx": [], "voice": "none", "referenceAudioUsed": False}, ["参照に音声ストリームが無い。"]
    bpm_note = f"prep（librosa）の推定 {onsets['bpm']} BPM、倍と半分は未確認" if onsets else "BPM 未計測"
    mu = (audio_ev or {}).get("music")
    fragment = ((audio_ev or {}).get("playbook") or {}).get("audio")
    if mu is not None:
        enters = mu.get("entersAtSec", mu.get("tStart"))
        tempo = mu.get("tempo") or {}
        bpm = tempo.get("bpm", mu.get("bpm"))
        cands = tempo.get("candidates", mu.get("bpmCandidates"))
        bgm = {"present": bool(mu.get("present"))}
        ev.m("audio.bgm.present")
        if bgm["present"]:
            frag_bgm = (fragment or {}).get("bgm") or {}
            bgm["character"] = frag_bgm.get("character") or (
                (f"約 {bpm} BPM" + (f"（候補 {', '.join(str(c) for c in cands)}）" if cands else "")) if bpm else "テンポ未計測")
            ev.i("audio.bgm.character")
            bgm["entersAt"] = at(beats, enters if enters is not None else 0.0)
            (ev.m if enters is not None and mu.get("entersAtBound", "exact") == "exact" else ev.i)("audio.bgm.entersAt")
            if voice != "none":
                bgm["duckUnderVoice"] = mu.get("duckUnderVoice", mu.get("ducksUnderSpeech"))
                bgm["levelDbUnderVoice"] = r(mu.get("levelDbUnderVoice"), 1)
                frag_ev = (audio_ev or {}).get("evidence") or {}
                for key in ("duckUnderVoice", "levelDbUnderVoice"):
                    path = f"audio.bgm.{key}"
                    if bgm[key] is None:
                        ev.u(path)
                    else:
                        (ev.i if path in (frag_ev.get("inferred") or []) else ev.m)(path)
            if mu.get("levelBasis"):
                notes.append(f"声との差の測り方: {mu['levelBasis']}。")
    else:
        bgm = {"present": True, "character": f"未計測（{bpm_note}）", "entersAt": {"beat": beats[0]["id"], "offsetSec": 0.0}}
        if voice != "none":
            bgm.update({"duckUnderVoice": None, "levelDbUnderVoice": None})
            ev.u("audio.bgm.duckUnderVoice", "audio.bgm.levelDbUnderVoice")
        ev.u("audio.bgm.present", "audio.bgm.character", "audio.bgm.entersAt")
        notes.append(f"BGM の有無、入り、声との差は audio_events.py の担当で未計測。{bpm_note}。")
    raw = None
    if audio_ev and isinstance(audio_ev.get("sfx"), list):
        kept = [s for s in audio_ev["sfx"] if s.get("confidence", 1.0) >= 0.6]
        types = [x.get("type") for x in (fragment or {}).get("sfx") or []]
        raw = [{"t": float(s["t"]), "type": types[k] if k < len(types) and types[k] else (s.get("label") or "transient"),
                "beatAligned": s.get("beatAligned", False)} for k, s in enumerate(kept)]
    elif audio_ev and audio_ev.get("sfxCandidates") is not None:
        raw = [{"t": float(s["t"]), "type": str((s.get("labels") or ["unlabeled"])[0]), "beatAligned": s.get("beatAligned", False)}
               for s in audio_ev["sfxCandidates"]]
    sfx = []
    if raw is not None:
        card_t = [c["tIn"] for c in cards]
        cut_t = [c["t"] for c in cuts]
        for s in sorted(raw, key=lambda s: s["t"]):
            t = s["t"]
            near = lambda xs: any(abs(x - t) <= 0.12 for x in xs)
            cue = "card-in" if near(card_t) else "cut" if near(cut_t) else "zoom" if near(zooms_t) else "beat-drop" if s["beatAligned"] else "other"
            sfx.append({"cue": cue, "at": at(beats, t), "type": s["type"]})
        ev.m("audio.sfx")
    else:
        ev.u("audio.sfx")
    ev.i("audio.voice")
    return {"bgm": bgm, "sfx": sfx, "voice": voice, "referenceAudioUsed": False}, notes


def reference_block(people, spans, cuts, ev):
    hard = sum(1 for c in cuts if c.get("confidence") == "high")
    ev.m("source.reference.hardCuts")
    if people and "onCamera" not in people:
        people = ((people.get("playbook") or {}).get("source") or {}).get("reference")
    if people and people.get("onCamera") in ON_CAMERA and people.get("speech") in SPEECH:
        ev.m("source.reference.onCamera", "source.reference.speech")
        return {"onCamera": people["onCamera"], "speech": people["speech"], "hardCuts": hard}
    ev.u("source.reference.onCamera", "source.reference.speech")
    return {"onCamera": "none", "speech": "voiceover" if spans else "none", "hardCuts": hard}


def source_text(work, cap_ocr, transcript):
    path = work / "source-text.json"
    old = load(path) or {}
    sheet = [c for c in (old.get("captions") or []) if c.get("from") == "sheet"]
    caps = None
    if cap_ocr is not None or sheet:
        caps = sheet + [{"tIn": c.get("tIn"), "tOut": c.get("tOut"), "text": c["text"], "from": "ocr"}
                        for c in (cap_ocr or {}).get("cards", []) if c.get("text")]
    if transcript is not None:
        tr = [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in transcript.get("segments", [])]
    else:
        tr = old.get("transcript")
    data = {
        "captions": caps,
        "transcript": tr,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def body(title, headings, sec):
    out = [f"# {title}", ""]
    for h in headings:
        out += [f"## {h}", "", sec.get(h, "未計測。"), ""]
    return "\n".join(out).rstrip() + "\n"


def route_list(ref, ev):
    footage = {"id": "caption-over-footage", "default": True, "container": "ffmpeg-ass", "needs": ["own-footage"],
               "paidApi": False, "talkingHead": False,
               "costUsdPerVideo": {"min": 0, "max": 0, "basis": "自分で撮った映像に ffmpeg と ASS でテロップを焼く。生成 API を呼ばない"},
               "status": "design-only"}
    motion = {"id": "code-motion", "default": False, "container": "html-canvas", "needs": ["none"],
              "paidApi": False, "talkingHead": False,
              "costUsdPerVideo": {"min": 0, "max": 0, "basis": "ローカルで描画して ffmpeg で書き出す"},
              "status": "design-only"}
    ev.i("routes")
    if ref["onCamera"] == "none" and "source.reference.onCamera" in ev.measured:
        motion["default"], footage["default"] = True, False
        return [motion, footage]
    return [footage, motion]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work_dir")
    ap.add_argument("--id", required=True, help="kebab-case format id; describes the form, never the creator or the work")
    ap.add_argument("--platform", default="other", choices=["instagram-reels", "tiktok", "youtube-shorts", "other"])
    ap.add_argument("--out")
    ap.add_argument("--template", default=str(PLUGIN_ROOT / "templates" / "playbook.md"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    work = Path(a.work_dir).expanduser().resolve()
    manifest = load(work / "manifest.json")
    if manifest is None:
        print(f"no manifest.json in {work}; run prep.py first", file=sys.stderr)
        return 2
    import re
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", a.id) or len(a.id) > 64:
        print("--id must be kebab-case, at most 64 characters", file=sys.stderr)
        return 2
    template = Path(a.template)
    headings = [l[3:].strip() for l in template.read_text().splitlines() if l.startswith("## ")]

    probe, prov = manifest["probe"], manifest["provenance"]
    shots = load(work / "shots.json") or {"cuts": []}
    cuts = shots.get("cuts", [])
    onsets = load(work / "audio" / "onsets.json")
    cap = load(work / "captions.json")
    cap_ocr = load(work / "captions.ocr.json")
    cam = load(work / "camera.json")
    audio_ev = load(work / "audio.json")
    people = load(work / "people.json")
    transcript = load(work / "transcript.json")
    steps = (load(work / "ingest.json") or {}).get("steps", {})

    ev = Evidence()
    dur, fps = probe["durationSec"], probe["fps"]
    aspect, exact = aspect_of(probe["width"], probe["height"])
    (ev.m if exact else ev.i)("format.aspect")
    ev.m("format.fps", "format.durationSec.reference")
    ev.i("format.durationSec.min", "format.durationSec.max", "format.safeArea")

    spans, spans_from = speech_spans(audio_ev, transcript)
    cards = sorted((cap or {}).get("cards") or [], key=lambda c: c["tIn"])
    beats, beats_from = make_beats(dur, cards, transcript, onsets, cuts, ev)
    layers, first_text, cap_notes = caption_layers(cap, beats, [s for s, _ in spans] if spans else None, dur, fps, ev)
    camera, cam_notes = camera_block(cam, beats, cuts, ev)
    ref = reference_block(people, spans, cuts, ev)

    talking = ref["onCamera"] == "face" or ref["speech"] == "on-camera"
    fmt_on = "none" if ref["onCamera"] == "face" else ref["onCamera"]
    fmt_speech = "none" if ref["speech"] == "none" else "voiceover"
    if "source.reference.onCamera" in ev.measured:
        ev.i("format.onCamera", "format.speech")
    else:
        ev.u("format.onCamera", "format.speech")
    zoom_t = [z["at"]["offsetSec"] + next(b["tIn"] for b in beats if b["id"] == z["at"]["beat"]) for z in camera["zooms"]]
    audio, audio_notes = audio_block(probe, onsets, audio_ev, beats, cards, cuts, zoom_t, fmt_speech, ev)
    routes = route_list(ref, ev)
    ev.u("hook.type", "name", "summary", "audience", "fitsContent")
    ev.i("contentRoute", "subject.of", "subject.words")
    if layers:
        ev.i("fonts")

    fm = {
        "schema": "sasaru-playbook/2",
        "id": a.id,
        "name": f"{TODO}: 型の短い名前",
        "status": "measured",
        "summary": f"{TODO}: この型を一文で。何が画面に出て、どこで見る人が止まるか",
        "tags": [],
        "audience": [f"{TODO}: 誰に向けた型か"],
        "fitsContent": [f"{TODO}: この型に載せられる自分のコンテンツの種類"],
        "contentRoute": "reference-world",
        "subject": {"of": "reference-world", "words": f"{TODO}: 参照の世界で起きる出来事を一文で書く"},
        "source": {"kind": "ingested", "platform": a.platform, "rightsTier": prov["rightsTier"],
                   "ingestedAt": str(prov["ingestedAt"]), "measuredFiles": 1, "reference": ref},
        "format": {"aspect": aspect, "fps": fps,
                   "durationSec": {"min": round(max(1.0, dur * 0.75), 1), "max": round(dur * 1.5, 1), "reference": dur},
                   "onCamera": fmt_on, "speech": fmt_speech,
                   "safeArea": {"top": 0.11, "bottom": 0.25, "left": 0.03, "right": 0.18}},
        "hook": {"type": "other", "firstFrameHasText": first_text},
        "beats": beats,
        "captions": layers,
        "camera": camera,
        "audio": audio,
        "routes": routes,
        "fonts": [{"family": "Noto Sans JP", "license": "OFL-1.1", "source": "https://fonts.google.com/noto/specimen/Noto+Sans+JP"}] if layers else [],
        "rights": {"makerSupplies": ["自分で書いた台本", "自分で撮った映像か、利用の許諾が記録された素材映像",
                                     "再配布か動画内利用の許諾が記録された BGM と効果音のファイル"],
                   "neverUse": ["参照動画の映像、音、テロップの文言"] + (["参照に映る人の顔と声"] if talking or "source.reference.onCamera" in ev.unmeasured else [])},
        "evidence": None,
    }
    fm["evidence"] = ev.dump(fm)
    text_data = source_text(work, cap_ocr, transcript)

    def status(name):
        s = steps.get(name, {}).get("status")
        return {"ok": "測った", "missing": "スクリプトが無いので未計測", "failed": "失敗したので未計測", "skipped": "飛ばしたので未計測"}.get(s, "未計測")

    beat_lines = "\n".join(f"- `{b['id']}` {b['role']}（仮）{b['tIn']}–{b['tOut']} 秒。{TODO}: 役割と、次へ進ませる仕掛け。" for b in beats)
    cut_desc = (f"参照のハードカットは {ref['hardCuts']} 本（prep の確信の高いもの）。候補は全部で {len(cuts)} 本"
                + (f"、うちジャンプカット {sum(c['kind'] == 'jump-cut' for c in cuts)} 本" if cuts else "") + "。")
    talk_note = ("参照は画面の人が喋る型として読める。既定ルートは喋らない `caption-over-footage` にした。"
                 "失うものは顔と口の動きが作る視線の引きで、テロップの大きさと出し消しの間で補う（推論）。"
                 if talking else "")
    sec = {
        "構成と尺": f"参照の尺は {dur} 秒、{probe['width']}×{probe['height']}、{fps} fps（prep）。尺の帯 {fm['format']['durationSec']['min']}–{fm['format']['durationSec']['max']} 秒は参照の尺からの推論。"
                    f"ビート {len(beats)} 本の区切りの出どころは「{beats_from or '測った手がかりが無いので仮置き'}」。{cut_desc}",
        "フック": f"フックは `b1`（0–{beats[0]['tOut']} 秒）。最初のフレームに字が{'ある' if first_text else 'ない'}"
                 f"（{'caption_boxes' if cap is not None else '未計測。仮置き'}）。{TODO}: 何を見せて何を約束するか。",
        "ビート": beat_lines,
        "テロップ": " ".join(cap_notes) + f" caption_boxes: {status('caption_boxes')}。",
        "カメラとトランジションとズーム": " ".join(cam_notes) + f" camera_motion: {status('camera_motion')}。",
        "BGM と効果音": " ".join(audio_notes) + f" audio_events: {status('audio_events')}。参照の音は使わない（`referenceAudioUsed: false`）。",
        "なぜ伸びるか": f"{TODO}: 推論として書く。止まる理由、最後まで見る理由、もう一度見る理由、伸びない側に落ちない理由。{talk_note}",
        "差し替える場所": "\n".join(f"- `{b['id']}`: {TODO}" for b in beats) + "\n- 変えない部分: テロップの層の大きさ、位置、出し消しの規則、最後の一枚を絵の終わりまで残すこと。\n- 商品の置き場: この下書きは productPlacement を省いてある（置き場が無い）。アカウントの型に置き場があるなら、ビートと役割と直接さを言葉で埋めてから check-product-placement に通す。null にはしない。",
        "制作ルート": "\n\n".join(route_steps(rt, a.id) for rt in routes),
        "編集の器とフォント": ("`caption-over-footage` は ffmpeg と ASS で焼く。`code-motion` は HTML Canvas で描いて ffmpeg で書き出す。"
                           "フォントは Noto Sans JP（OFL-1.1、Google Fonts から入手）。ファイルは同梱しない。" if layers else "テロップが無いのでフォントは使わない。"),
        "素材の権利": "作る人が用意するものと使ってはいけないものは `rights` のとおり。参照の映像、音、テロップの文言、参照に映る人の顔と声は使わない。",
        "費用の目安": "どのルートも生成 API を呼ばないので、一本 0 ドル。",
        "測ったことと推論": measure_summary(steps, fm["evidence"], transcript, spans_from, text_data),
    }
    title = fm["name"]
    out = Path(a.out) if a.out else work / f"{a.id}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    y = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=None, width=1000)
    out.write_text("---\n" + y + "---\n\n" + body(title, headings, sec))
    result = {"playbook": str(out), "sourceText": str(work / "source-text.json"), "evidence": fm["evidence"]}
    print(f"draft: {out}", file=sys.stderr)
    if a.json:
        print(json.dumps(result, ensure_ascii=False))
    return 0


def route_steps(rt, pid):
    if rt["id"] == "caption-over-footage":
        steps = ["自分の映像を、playbook の縦横比と fps で撮るか用意する。顔を映さない。",
                 "ビートごとの `swap` を埋めた台本から、層ごとのテロップのカード（秒、文、強調）を JSON にする。出し消しは層の `show`、`leadSec`、`hide`、`minHoldSec`、`lastCard` に従う。",
                 "カードを ASS に書き、ffmpeg で焼く（`ffmpeg -i footage.mp4 -vf ass=cards.ass -an cut-video.mp4`）。",
                 "曲と効果音は許諾を記録した別ファイルから足す。素材の音は `bash strip_audio.sh footage.mp4 footage-silent.mp4` で外してから使う。",
                 "gate のカット検査に通す。"]
    else:
        steps = ["ビートごとの `swap` を埋めた台本から、層ごとのカードを JSON にする。",
                 "HTML Canvas で背景とカードを描き、フレームを書き出して ffmpeg で playbook の fps の動画にする。",
                 "曲と効果音は許諾を記録した別ファイルから足す。",
                 "gate のカット検査に通す。"]
    return f"### {rt['id']}\n\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))


def measure_summary(steps, d, transcript, spans_from, text_data):
    names = ["prep", "caption_boxes", "camera_motion", "audio_events", "people_voice", "transcribe"]
    lines = []
    for n in names:
        s = steps.get(n, {})
        lines.append(f"- `{n}`: {s.get('status', '記録なし')}" + (f"（{s['note']}）" if s.get("note") else ""))
    if transcript is not None:
        lines.append(f"- 文字起こしは言語 {transcript.get('language')}、平均 avg_logprob {transcript.get('meanAvgLogprob')}、"
                     f"{'信頼できる' if transcript.get('reliable') else '信頼できない'}。文言は `source-text.json` にだけ置いた。")
    if spans_from:
        lines.append(f"- 発話区間の出どころは {spans_from}。")
    if text_data["captions"] is None:
        lines.append("- テロップの文言はまだ読んでいない。シートを読んで `source-text.json` の `captions` に `\"from\": \"sheet\"` で足す。")
    lines.append(f"- 測った欄 {len(d['measured'])}、推論 {len(d['inferred'])}、未計測 {len(d['unmeasured'])}。一覧はフロントマターの `evidence`。")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
