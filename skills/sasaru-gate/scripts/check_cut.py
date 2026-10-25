# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.26,<3", "opencv-python-headless>=4.9,<5", "pyyaml>=6,<7", "jsonschema>=4.21,<5"]
# ///
"""Check one finished cut against its playbook. Every column is pass, fail, or unmeasured. Local only.

Usage: uv run --script check_cut.py <cut_dir> [--playbook <id>.md] [--video <cut.mp4>] [--voice <dry.wav>]
       [--reference-audio <ref.wav>] [--last-mora T0:T1] [--roi Y0:Y1] [--fetch-models] [--lines lines.json] [--out <gate.json>]
<cut_dir> holds cut.json (the make step's record) and the exported video. Targets come from the playbook fields;
measurement definitions and tolerances come from lines.json. Models are read from $SASARU_CACHE (default ~/.cache/sasaru).
Prints one JSON object. Exit 0 pass, 2 bad input, 3 at least one column failed or stayed unmeasured.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
from validate_playbook import get_path, has_path, load_playbook, validate  # noqa: E402

DEFAULT_LINES = HERE.parent / "lines.json"
BUNDLED_PLAYBOOKS = HERE.parents[2] / "playbooks"
CACHE = Path(os.environ.get("SASARU_CACHE", Path.home() / ".cache" / "sasaru"))
YUNET = "face_detection_yunet_2023mar.onnx"
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/" + YUNET
ASPECTS = {"9:16": 9 / 16, "4:5": 4 / 5, "1:1": 1.0, "16:9": 16 / 9}
INNER_PAUSE_MARKS = set("、，,・ 　")
SR = 16000


def r(x, n=3):
    return None if x is None else round(float(x), n)


def hex_to_bgr(h):
    h = h.lstrip("#")
    return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.int16)


def bgr_to_hex(b):
    b = [int(round(v)) for v in b]
    return "#%02X%02X%02X" % (b[2], b[1], b[0])


def dbfs(v):
    return 20 * math.log10(max(v, 1e-9))


# ---------- input ----------

def find_playbook(cut, cut_dir, explicit):
    if explicit:
        return Path(explicit)
    pid = cut.get("playbook")
    cands = []
    if cut.get("playbookPath"):
        cands.append((cut_dir / cut["playbookPath"]).resolve())
    home = Path(os.environ["SASARU_HOME"]) if os.environ.get("SASARU_HOME") else None
    for lib in [home, cut_dir.parent.parent if cut_dir.parent.name == "cuts" else None, Path.cwd() / "sasaru", BUNDLED_PLAYBOOKS.parent]:
        if lib and pid:
            cands.append(lib / "playbooks" / f"{pid}.md")
    return next((c for c in cands if c.is_file()), None)


def probe(video):
    p = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(video)],
                       capture_output=True, text=True, check=True)
    streams = json.loads(p.stdout)["streams"]
    v = next(s for s in streams if s["codec_type"] == "video")
    num, den = map(int, v["avg_frame_rate"].split("/"))
    return {"width": int(v["width"]), "height": int(v["height"]), "fps": num / den if den else 0.0,
            "hasAudio": any(s["codec_type"] == "audio" for s in streams)}


def load_audio(path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.int16).astype(np.float64) / 32768.0


# ---------- audio ----------

def envelope(x, win, hop):
    W, H = max(1, int(win * SR)), max(1, int(hop * SR))
    pad = np.pad(x, (W // 2, W - W // 2))
    c = np.concatenate([[0.0], np.cumsum(pad ** 2)])
    idx = np.arange(0, len(x), H)
    return idx / SR, np.sqrt(np.maximum(c[np.minimum(idx + W, len(c) - 1)] - c[idx], 0) / W)


def runs(mask):
    edges = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.where(edges == 1)[0], np.where(edges == -1)[0]))


def speech_map(x, m):
    hop = m["envelopeHopSec"]
    t, e = envelope(x, m["envelopeWindowSec"], hop)
    line = m["speechLineFracOfMax"] * float(e.max()) if len(e) else 0.0
    sp = e > line
    rr = runs(sp)
    segs = [(float(t[a]), float(t[b - 1] + hop)) for a, b in rr]
    onsets = [s for s, _ in segs]
    k = max(1, int(round(0.05 / hop)))
    for a, b in rr:
        for i in range(a + k, b - k):
            if e[i] != e[max(a, i - k):min(b, i + k + 1)].min():
                continue
            if e[i] <= m["valleyDepthFrac"] * min(e[a:i].max(), e[i + 1:b].max()):
                onsets.append(float(t[i]))
    return {"t": t, "e": e, "line": line, "speech": sp, "segments": segs, "onsets": sorted(onsets)}


def place(x, n, at_sec=0.0, in_sec=0.0):
    out = np.zeros(n)
    src = x[int(in_sec * SR):]
    a = int(at_sec * SR)
    if a < n:
        k = min(n - a, len(src))
        out[a:a + k] = src[:k]
    return out


def explained_by(mix, sources, win):
    """Share of the mix energy that time-varying gains on the listed sources reproduce."""
    W = max(1, int(win * SR))
    res = 0.0
    for i in range(0, len(mix), W):
        y = mix[i:i + W]
        A = np.stack([s[i:i + W] for s in sources], axis=1)
        if np.abs(A).sum() == 0:
            res += float(np.dot(y, y))
            continue
        g, *_ = np.linalg.lstsq(A, y, rcond=None)
        d = y - A @ g
        res += float(np.dot(d, d))
    tot = float(np.dot(mix, mix))
    return 1 - res / tot if tot > 0 else None


def max_window_corr(mix, ref, win):
    W = int(win * SR)
    if len(ref) < W or len(mix) < W:
        return None
    L = 1 << int(np.ceil(np.log2(len(ref) + W)))
    R = np.fft.rfft(ref, L)
    ref_sq = np.concatenate([[0.0], np.cumsum(ref ** 2)])
    best = 0.0
    for i in range(0, len(mix) - W + 1, W // 2):
        y = mix[i:i + W]
        ny = np.linalg.norm(y)
        if ny < 1e-6:
            continue
        c = np.fft.irfft(np.fft.rfft(y[::-1], L) * R, L)[W - 1:len(ref)]
        nr = np.sqrt(np.maximum(ref_sq[W:len(ref) + 1] - ref_sq[:len(ref) - W + 1], 1e-12))
        best = max(best, float(np.max(np.abs(c[:len(nr)]) / (nr * ny))))
    return best


# ---------- pixels ----------

def text_mask(fr, color, ctol, stroke, stol, k):
    core = (np.abs(fr.astype(np.int16) - color).max(axis=2) <= ctol).astype(np.uint8)
    if stroke is None:
        return core, None
    dark = (np.abs(fr.astype(np.int16) - stroke).max(axis=2) <= stol).astype(np.uint8)
    return core & cv2.dilate(dark, np.ones((k, k), np.uint8)), dark


def lines_of(mask, min_px, gap):
    rr = runs(mask.sum(axis=1) > 0)
    merged = []
    for a, b in rr:
        if merged and a - merged[-1][1] <= gap:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    out = []
    for a, b in merged:
        sub = mask[a:b]
        px = int(sub.sum())
        if px < min_px:
            continue
        cols = np.where(sub.any(axis=0))[0]
        out.append({"top": int(a), "bottom": int(b), "left": int(cols[0]), "right": int(cols[-1] + 1), "px": px})
    return out


def same_card(a, b, H, W):
    if len(a) != len(b) or not a:
        return False
    for la, lb in zip(a, b):
        if abs((la["top"] + la["bottom"]) - (lb["top"] + lb["bottom"])) / 2 > 0.012 * H:
            return False
        if abs(la["left"] - lb["left"]) > 0.02 * W or abs(la["right"] - lb["right"]) > 0.02 * W:
            return False
    pa, pb = sum(l["px"] for l in a), sum(l["px"] for l in b)
    return 0.6 < pa / max(pb, 1) < 1.67


class Layer:
    def __init__(self, cfg, style):
        self.id = cfg["id"]
        self.cfg = cfg
        self.color = hex_to_bgr(style.get("color") or cfg["color"])
        stroke = style["stroke"] if "stroke" in style else cfg.get("stroke")
        self.stroke_cfg = stroke
        self.stroke = hex_to_bgr(stroke["color"]) if stroke else None
        self.cy = (cfg.get("position") or {}).get("cy")
        self.frames = []

    def key(self):
        return (tuple(self.color), None if self.stroke is None else tuple(self.stroke))


def active(layer, t, beat_windows):
    ids = layer.cfg.get("beats") or []
    return not ids or any(beat_windows[b][0] - 1e-6 <= t < beat_windows[b][1] + 1e-6 for b in ids if b in beat_windows)


def scan(video, info, layers, m, roi, beat_windows):
    W, H, fps = info["width"], info["height"], info["fps"]
    w, h = int(W * m["detectScale"]), int(H * m["detectScale"])
    k = max(3, int(round(2 * m["strokeSearchPx1080"] * w / 1080)) | 1)
    min_px, gap = m["captionMinLinePxFrac"] * w * h, max(1, int(m["captionLineGapFrac"] * h))
    groups = {}
    for L in layers:
        groups.setdefault(L.key(), []).append(L)
    cap = cv2.VideoCapture(str(video))
    cuts, prev, i = [], None, 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        q = cv2.cvtColor(cv2.resize(fr, (W // 4, H // 4), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2HSV).astype(np.int16)
        if prev is not None and float(np.abs(q - prev).mean()) > m["hardCutHsvDelta"]:
            cuts.append(i)
        prev = q
        if layers:
            small = cv2.resize(fr, (w, h), interpolation=cv2.INTER_AREA)
            t = i / fps
            for Ls in groups.values():
                mask, _ = text_mask(small, Ls[0].color, m["captionColorTol"], Ls[0].stroke, m["strokeColorTol"], k)
                if roi:
                    mask[: int(roi[0] * h)] = 0
                    mask[int(roi[1] * h):] = 0
                found = lines_of(mask, min_px, gap)
                live = [L for L in Ls if active(L, t, beat_windows)]
                per = {L.id: [] for L in Ls}
                for ln in found:
                    if not live:
                        break
                    cy = (ln["top"] + ln["bottom"]) / 2 / h
                    best = min(live, key=lambda L: abs(cy - L.cy) if L.cy is not None else 0.25)
                    per[best.id].append(ln)
                for L in Ls:
                    L.frames.append(per[L.id])
        i += 1
    cap.release()
    return i, cuts, (w, h)


def segment(frames, wh):
    w, h = wh
    cards, cur = [], None
    for i, ls in enumerate(frames):
        if not ls:
            if cur:
                cards.append(cur)
                cur = None
            continue
        if cur and (same_card(ls, frames[i - 1], h, w) or same_card(ls, frames[cur["last"]], h, w)):
            cur["last"] = i
        else:
            if cur:
                cards.append(cur)
            cur = {"first": i, "last": i}
    if cur:
        cards.append(cur)
    return [c for c in cards if c["last"] > c["first"]]


def classify_motion(seq, stable, at_start):
    s_top = sum(l["top"] for l in stable) / len(stable)
    s_h = sum(l["bottom"] - l["top"] for l in stable) / len(stable)
    s_px = sum(l["px"] for l in stable)
    edge = []
    for ls in seq:
        top = sum(l["top"] for l in ls) / len(ls)
        hh = sum(l["bottom"] - l["top"] for l in ls) / len(ls)
        px = sum(l["px"] for l in ls)
        if abs(top - s_top) <= 1 and px >= 0.97 * s_px:
            break
        edge.append((top - s_top, hh / max(s_h, 1)))
    if not edge:
        return "cut", 0
    dy, hr = edge[0]
    if abs(hr - 1) >= 0.1:
        return ("scale-in" if at_start else "other"), len(edge)
    if abs(dy) >= 0.25 * s_h:
        return (("slide-up" if dy > 0 else "other") if at_start else "slide"), len(edge)
    return "fade", len(edge)


def measure_frame(video, idx, layer, m, roi, info, ref_lines, wh):
    W, H = info["width"], info["height"]
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, fr = cap.read()
    cap.release()
    if not ok:
        return []
    k = max(3, int(round(2 * m["strokeSearchPx1080"] * W / 1080)) | 1)
    mask, dark = text_mask(fr, layer.color, m["captionColorTol"], layer.stroke, m["strokeColorTol"], k)
    if roi:
        mask[: int(roi[0] * H)] = 0
        mask[int(roi[1] * H):] = 0
    found = lines_of(mask, m["captionMinLinePxFrac"] * W * H, max(1, int(m["captionLineGapFrac"] * H)))
    sh = H / wh[1]
    keep = [ln for ln in found if any(ln["top"] < rl["bottom"] * sh and ln["bottom"] > rl["top"] * sh for rl in ref_lines)]
    out = []
    for ln in keep:
        sub = np.zeros_like(mask)
        sub[ln["top"]:ln["bottom"], ln["left"]:ln["right"]] = mask[ln["top"]:ln["bottom"], ln["left"]:ln["right"]]
        core = fr[sub.astype(bool)]
        rings = []
        if dark is not None:
            prev = sub
            reach = 3 * max(layer.stroke_cfg.get("px1080") or 0, m["strokeSearchPx1080"])
            for rad in range(1, int(round(reach * W / 1080)) + 1):
                grown = cv2.dilate(sub, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rad + 1, 2 * rad + 1)))
                ring = (grown > 0) & (prev == 0)
                rings.append(float(dark[ring].mean()) if ring.any() else 0.0)
                prev = grown
        out.append({"heightRatio": (ln["bottom"] - ln["top"]) / H, "widthRatio": (ln["right"] - ln["left"]) / W,
                    "cx": (ln["left"] + ln["right"]) / 2 / W, "cy": (ln["top"] + ln["bottom"]) / 2 / H,
                    "left": ln["left"] / W, "right": ln["right"] / W, "top": ln["top"] / H, "bottom": ln["bottom"] / H,
                    "color": bgr_to_hex(np.median(core, axis=0)) if len(core) else None, "rings": rings})
    return out


def detect_faces(video, info, m):
    model = CACHE / YUNET
    if not model.is_file():
        return None
    det = cv2.FaceDetectorYN.create(str(model), "", (320, 320), m["faceScoreMin"])
    cap = cv2.VideoCapture(str(video))
    fps = info["fps"] or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    hits, total, at = 0, 0, []
    for i in range(0, n, max(1, int(round(m["faceStepSec"] * fps)))):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if not ok:
            continue
        s = 960 / max(fr.shape[:2])
        if s < 1:
            fr = cv2.resize(fr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        det.setInputSize((fr.shape[1], fr.shape[0]))
        _, faces = det.detect(fr)
        total += 1
        if faces is not None and len(faces):
            hits += 1
            at.append(round(i / fps, 2))
    cap.release()
    return {"sampledFrames": total, "framesWithFace": hits, "atSec": at[:20]}


# ---------- report ----------

class Report:
    def __init__(self, fm):
        self.fm = fm
        self.unmeasured_paths = (fm.get("evidence") or {}).get("unmeasured") or []
        self.columns, self.not_checked = [], []

    def add(self, cid, status, measured=None, target=None, target_from=None, method="pixels", note=None, **extra):
        c = {"id": cid, "status": status, "measured": measured, "target": target, "targetFrom": target_from, "method": method}
        if note:
            c["note"] = note
        c.update(extra)
        self.columns.append(c)

    def target(self, cid, path, measured, method="pixels"):
        """Playbook value for a column. Null listed as unmeasured gives an unmeasured column; other null means no target."""
        v = get_path(self.fm, path) if has_path(self.fm, path) else None
        if v is not None:
            return v
        if any(path == p or path.startswith(p + ".") for p in self.unmeasured_paths):
            self.add(cid, "unmeasured", measured, None, f"playbook:{path}", method, "the playbook lists this field as unmeasured")
        else:
            self.skip(cid, f"playbook:{path} is null or absent, so there is no target", measured)
        return None

    def skip(self, cid, why, measured=None):
        self.not_checked.append({"id": cid, "why": why, **({"measured": measured} if measured is not None else {})})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cut_dir")
    ap.add_argument("--playbook")
    ap.add_argument("--video")
    ap.add_argument("--voice", help="dry voice as heard in the cut; default is the voice source in cut.json")
    ap.add_argument("--reference-audio", help="the reference's audio, to show the cut does not carry it")
    ap.add_argument("--last-mora", help="T0:T1 of the closing mora in the cut, from TTS alignment; default cut.json lastMora")
    ap.add_argument("--roi", help="Y0:Y1 band (0..1) to search for captions")
    ap.add_argument("--fetch-models", action="store_true", help="download the free YuNet face detector into $SASARU_CACHE")
    ap.add_argument("--lines", default=str(DEFAULT_LINES))
    ap.add_argument("--schema", help="default: the plugin's schema/playbook.schema.json")
    ap.add_argument("--template", help="default: the plugin's templates/playbook.md")
    ap.add_argument("--out")
    a = ap.parse_args()

    def bad(msg):
        print(json.dumps({"schema": "sasaru-gate-result/1", "verdict": "bad-input", "error": msg}, ensure_ascii=False))
        sys.exit(2)

    cut_dir = Path(a.cut_dir)
    try:
        cut = json.loads((cut_dir / "cut.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        bad(f"cut.json: {e}")
    pb_path = find_playbook(cut, cut_dir, a.playbook)
    if pb_path is None or not pb_path.is_file():
        bad(f"playbook '{cut.get('playbook')}' not found; pass --playbook")
    video = Path(a.video) if a.video else (cut_dir / cut["video"] if cut.get("video") else next(iter(sorted(cut_dir.glob("*.mp4"))), None))
    if video is None or not video.is_file():
        bad("video not found; set cut.json video or pass --video")
    try:
        text = pb_path.read_text(encoding="utf-8")
        fm, body = load_playbook(pb_path)
        cfg = json.loads(Path(a.lines).read_text(encoding="utf-8"))
        info = probe(video)
    except Exception as e:  # noqa: BLE001
        bad(str(e))
    if a.fetch_models and not (CACHE / YUNET).is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(YUNET_URL, CACHE / YUNET)
    m, tol, lines = cfg["measure"], cfg["tolerance"], cfg["lines"]
    roi = tuple(float(v) for v in a.roi.split(":")) if a.roi else None
    rep = Report(fm)
    tol_t = m["minHoleSec"]

    try:
        errs, warns, _ = validate(fm, body, pb_path, a.schema, a.template, full_text=text)
    except (OSError, ValueError) as e:
        bad(str(e))
    rep.add("playbook.valid", "pass" if not errs else "fail", {"errors": errs, "warnings": warns}, method="validate_playbook",
            note="the wording check runs in validate_playbook.py with --work")

    W, H, fps = info["width"], info["height"], info["fps"]
    fmt = fm.get("format") or {}
    beats = [b for b in fm.get("beats") or [] if isinstance(b, dict)]
    ref_len = (fmt.get("durationSec") or {}).get("reference") or (beats[-1]["tOut"] if beats else None)
    styles = cut.get("captionStyle") or {}
    layers = [Layer(c, styles.get(c["id"], {})) for c in fm.get("captions") or []]

    # beat windows need the duration; scan first with windows from the record's stretch guess, then rescale
    n_probe = int(cv2.VideoCapture(str(video)).get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    est_dur = n_probe / fps if fps else 0
    stretch = est_dur / ref_len if ref_len else 1.0
    windows = {b["id"]: (b["tIn"] * stretch, b["tOut"] * stretch) for b in beats}
    n_frames, cut_frames, wh = scan(video, info, layers, m, roi, windows)
    duration = n_frames / fps if fps else 0.0
    stretch = duration / ref_len if ref_len else 1.0
    windows = {b["id"]: (b["tIn"] * stretch, b["tOut"] * stretch) for b in beats}

    def at_time(at):
        return None if not at or at.get("beat") not in windows else windows[at["beat"]][0] + at.get("offsetSec", 0) * stretch

    # ----- format -----
    if fmt.get("aspect"):
        rep.add("format.aspect", "pass" if abs(W / H - ASPECTS[fmt["aspect"]]) <= tol["aspectAbs"] else "fail", f"{W}x{H}",
                fmt["aspect"], "playbook:format.aspect")
    if fmt.get("fps"):
        rep.add("format.fps", "pass" if abs(fps - fmt["fps"]) <= tol["fpsAbs"] else "fail", r(fps), fmt["fps"], "playbook:format.fps")
    d = fmt.get("durationSec") or {}
    if "min" in d:
        ok = d["min"] - 1e-6 <= duration <= d["max"] + 1e-6
        rep.add("format.durationSec", "pass" if ok else "fail", r(duration), {"min": d["min"], "max": d["max"]},
                "playbook:format.durationSec", frames=n_frames, stretch=r(stretch), recordStretch=cut.get("stretch"))

    # ----- captions -----
    card_events = []
    measured_layers = {}
    for L in layers:
        raw = segment(L.frames, wh)
        cards = []
        for c in raw:
            span = L.frames[c["first"]:c["last"] + 1]
            st_idx = c["first"] + int(0.6 * (c["last"] - c["first"]))
            kin, nin = classify_motion(span, L.frames[st_idx], True)
            kout, nout = classify_motion(list(reversed(span)), L.frames[st_idx], False)
            ml = measure_frame(video, st_idx, L, m, roi, info, L.frames[st_idx], wh)
            if ml:
                cards.append({"tIn": c["first"] / fps, "tOut": (c["last"] + 1) / fps, "last": c["last"], "lines": ml,
                              "motionIn": kin, "inFrames": nin, "motionOut": "slide" if kout == "slide-up" else kout, "outFrames": nout})
        measured_layers[L.id] = cards
        card_events += [c["tIn"] for c in cards]

    first_has_text = any(L.frames and L.frames[0] for L in layers)
    hook = fm.get("hook") or {}
    if "firstFrameHasText" in hook:
        rep.add("hook.firstFrameHasText", "pass" if first_has_text == hook["firstFrameHasText"] else "fail", first_has_text,
                hook["firstFrameHasText"], "playbook:hook.firstFrameHasText",
                note=None if layers else "no caption layer, so only an empty first frame can be seen")

    # ----- audio maps -----
    mix = load_audio(video) if info["hasAudio"] else None
    voice_src = next((s for s in (cut.get("audio") or {}).get("sources") or [] if s.get("role") == "voice"), None)
    voice_path = Path(a.voice) if a.voice else ((cut_dir / voice_src["path"]) if voice_src and voice_src.get("path") else None)
    voice = None
    if voice_path is not None and voice_path.is_file():
        voice = place(load_audio(voice_path), len(mix) if mix is not None else int(duration * SR),
                      voice_src.get("atSec", 0) if voice_src and not a.voice else 0, voice_src.get("inSec", 0) if voice_src and not a.voice else 0)
    base = voice if voice is not None else mix
    audio_on = "voice" if voice is not None else ("mix" if mix is not None else None)
    sp = speech_map(base, m) if base is not None else None

    def nearest(t, pts):
        return min(pts, key=lambda p: abs(p - t)) if pts else None

    # ----- beats and transitions -----
    events = sorted(set(card_events + [f / fps for f in cut_frames]))
    if len(beats) >= 2:
        btol = 0.5 * min((b["tOut"] - b["tIn"]) * stretch for b in beats)
        rows, ok_all = [], True
        for b in beats[:-1]:
            t = b["tOut"] * stretch
            ev = nearest(t, events)
            hit = ev is not None and abs(ev - t) <= btol
            ok_all &= hit
            rows.append({"after": b["id"], "role": b["role"], "expectedSec": r(t), "nearestEventSec": r(ev),
                         "deltaSec": r(None if ev is None else ev - t)})
        if events:
            rep.add("beats.boundaries", "pass" if ok_all else "fail", rows, {"toleranceSec": r(btol)}, "playbook:beats",
                    note="beat ends scaled to the cut; events are caption card changes and hard cuts")
        else:
            rep.add("beats.boundaries", "unmeasured", rows, {"toleranceSec": r(btol)}, "playbook:beats",
                    note="no caption cards and no hard cuts, so nothing on screen marks a beat")
    sudden = {"hard-cut", "zoom-cut", "match-cut", "whip", "glitch"}
    exp_tr = [(tr["type"], at_time(tr.get("at"))) for tr in (fm.get("camera") or {}).get("transitions") or [] if tr.get("type") in sudden]
    got = [f / fps for f in cut_frames]
    btol_tr = 0.5 * min((b["tOut"] - b["tIn"]) * stretch for b in beats) if beats else tol_t
    matched = [nearest(t, got) for _, t in exp_tr]
    missing = [r(t) for (_, t), g in zip(exp_tr, matched) if g is None or abs(g - t) > btol_tr]
    extra = [r(g) for g in got if not any(abs(g - t) <= btol_tr for _, t in exp_tr)]
    rep.add("camera.transitions", "pass" if not missing and not extra else "fail",
            {"cutsAtSec": [r(g) for g in got]}, {"expectedAtSec": [r(t) for _, t in exp_tr]}, "playbook:camera.transitions",
            missing=missing, unexpected=extra, note="sudden transitions only; fades are not detected")
    for key in ("moves", "zooms"):
        rep.skip(f"camera.{key}", "camera motion is measured at ingest (camera_motion.py), not in the cut check")

    # ----- caption columns per layer -----
    safe = fmt.get("safeArea")
    rec_cards = cut.get("cards") or []
    deviations = {dv.get("path"): dv for dv in cut.get("deviations") or []}
    for L in layers:
        lid, lc, cards = L.id, L.cfg, measured_layers[L.id]
        P = f"captions.{lid}"
        if lc.get("writingMode") == "vertical":
            rep.add(f"{P}.cards", "unmeasured", None, None, f"playbook:{P}.writingMode",
                    note="vertical captions are not measured by this check yet")
            continue
        if not cards:
            rep.add(f"{P}.cards", "fail", 0, None, f"playbook:{P}", note="no card in this layer's colour and stroke was found")
            continue
        all_lines = [ln for c in cards for ln in c["lines"]]
        hmin = min(ln["heightRatio"] for ln in all_lines)
        base = [ln for ln in all_lines if ln["heightRatio"] <= hmin * (1 + tol["capHeightRel"])]
        base_h = float(np.median([ln["heightRatio"] for ln in base]))
        rep.add(f"{P}.cards", "pass", [{"tIn": r(c["tIn"]), "tOut": r(c["tOut"]), "lines": len(c["lines"]),
                                        "heightRatio": [r(ln["heightRatio"], 4) for ln in c["lines"]],
                                        "cx": [r(ln["cx"]) for ln in c["lines"]], "cy": [r(ln["cy"]) for ln in c["lines"]],
                                        "motionIn": c["motionIn"], "motionOut": c["motionOut"]} for c in cards],
                note="measured cards, for reading the other columns")

        dv = deviations.get(f"{P}.capHeightRatio")
        ch_t = dv.get("to") if dv else rep.target(f"{P}.capHeightRatio", f"{P}.capHeightRatio", r(base_h, 4))
        if ch_t is not None:
            rep.add(f"{P}.capHeightRatio", "pass" if abs(base_h - ch_t) / ch_t <= tol["capHeightRel"] else "fail", r(base_h, 4), ch_t,
                    f"cut.json:deviations[{P}.capHeightRatio]" if dv else f"playbook:{P}.capHeightRatio",
                    toleranceRel=tol["capHeightRel"], baseLines=len(base))
        if lc.get("role") == "headline":
            fl = lines["headlineCapHeightFloor"]
            rep.add(f"{P}.headlineFloor", "pass" if base_h >= fl else "fail", r(base_h, 4), fl, "lines:headlineCapHeightFloor")

        emph = lc.get("emphasis")
        big = [ln for ln in all_lines if ln["heightRatio"] > hmin * (1 + tol["capHeightRel"])]
        scale_m = max(ln["heightRatio"] for ln in all_lines) / base_h
        if emph and emph.get("scale"):
            ok = abs(scale_m - emph["scale"]) / emph["scale"] <= tol["emphasisRel"]
            rep.add(f"{P}.emphasis.scale", "pass" if ok else "fail", r(scale_m), emph["scale"], f"playbook:{P}.emphasis.scale",
                    toleranceRel=tol["emphasisRel"], emphasisLines=len(big))
        elif emph is None:
            rep.add(f"{P}.emphasis", "pass" if not big else "fail", {"scale": r(scale_m), "largerLines": len(big)}, None,
                    f"playbook:{P}.emphasis", note="null emphasis means one size inside the layer")
        if emph and emph.get("color"):
            rep.skip(f"{P}.emphasis.color", "the detector looks for the layer colour; a differently coloured emphasis is not seen")

        pos = lc.get("position") or {}
        for key, vals in (("cx", [ln["cx"] for ln in all_lines]), ("cy", [ln["cy"] for ln in base])):
            mv = float(np.median(vals))
            tv = rep.target(f"{P}.position.{key}", f"{P}.position.{key}", r(mv))
            if tv is not None:
                rep.add(f"{P}.position.{key}", "pass" if abs(mv - tv) <= tol["positionAbs"] else "fail", r(mv), tv,
                        f"playbook:{P}.position.{key}", toleranceAbs=tol["positionAbs"])
        widths = [ln["widthRatio"] for ln in all_lines]
        if pos.get("align") and len(all_lines) >= 2 and max(widths) - min(widths) >= 0.05:
            spread = {k: float(np.std([ln[f] for ln in all_lines])) for k, f in (("left", "left"), ("center", "cx"), ("right", "right"))}
            al = min(spread, key=spread.get)
            rep.add(f"{P}.position.align", "pass" if al == pos["align"] else "fail", al, pos["align"], f"playbook:{P}.position.align",
                    spread={k: r(v, 4) for k, v in spread.items()})
        elif pos.get("align"):
            rep.skip(f"{P}.position.align", "fewer than two lines of different width, so the anchor cannot be told apart")
        if safe:
            out = [{"cardInSec": r(c["tIn"]), "left": r(ln["left"]), "right": r(ln["right"]), "top": r(ln["top"]), "bottom": r(ln["bottom"])}
                   for c in cards for ln in c["lines"]
                   if ln["left"] < safe["left"] or ln["right"] > 1 - safe["right"] or ln["top"] < safe["top"] or ln["bottom"] > 1 - safe["bottom"]]
            rep.add(f"{P}.safeArea", "pass" if not out else "fail", {"outside": out}, safe, "playbook:format.safeArea")

        lm = max(len(c["lines"]) for c in cards)
        if lc.get("linesMax"):
            rep.add(f"{P}.linesMax", "pass" if lm <= lc["linesMax"] else "fail", lm, lc["linesMax"], f"playbook:{P}.linesMax")
        cols = [ln["color"] for ln in base if ln["color"]]
        if cols:
            med = np.median(np.array([hex_to_bgr(c) for c in cols]), axis=0)
            diff = int(np.abs(med - L.color).max())
            rep.add(f"{P}.color", "pass" if diff <= m["captionColorTol"] else "fail", bgr_to_hex(med), bgr_to_hex(L.color),
                    f"playbook:{P}.color", maxChannelDiff=diff)
        if L.stroke is not None:
            mean_r = np.array([ln["rings"] for ln in all_lines]).mean(axis=0)
            t_px = max(1, int(round((L.stroke_cfg.get("px1080") or m["strokeSearchPx1080"]) * W / 1080)))
            near = float(mean_r[:t_px].mean())
            far = float(mean_r[2 * t_px:3 * t_px].mean()) if len(mean_r) >= 3 * t_px else None
            fmin = tol["strokeRingFracMin"]
            lead = 0
            for v in mean_r[1:]:
                if v < fmin:
                    break
                lead += 1
            meas = {"nearDarkFrac": r(near, 2), "farDarkFrac": r(far, 2), "px1080Approx": r((lead + 1) * 1080 / W, 1)}
            if far is None or far >= fmin:
                rep.add(f"{P}.stroke", "unmeasured", meas, L.stroke_cfg, f"playbook:{P}.stroke",
                        note="the background (or a shadow) two to three stroke widths out is as dark as the stroke, so the stroke cannot be told apart")
            else:
                rep.add(f"{P}.stroke", "pass" if near >= fmin else "fail", meas, L.stroke_cfg, f"playbook:{P}.stroke",
                        note="presence is judged; the width is reported only")

        holds = [c["tOut"] - c["tIn"] for c in cards[:-1]]
        mh = rep.target(f"{P}.minHoldSec", f"{P}.minHoldSec", r(min(holds)) if holds else None)
        if mh is not None:
            short = [{"cardInSec": r(c["tIn"]), "heldSec": r(c["tOut"] - c["tIn"])} for c in cards[:-1] if c["tOut"] - c["tIn"] < mh - 1e-6]
            rep.add(f"{P}.minHoldSec", "pass" if not short else "fail", {"shortest": r(min(holds)) if holds else None, "short": short},
                    mh, f"playbook:{P}.minHoldSec", note="the last card is judged by lastCard")

        show = lc.get("show")
        if show == "beat-start":
            starts = [w_[0] for w_ in windows.values()]
            rows = [{"cardInSec": r(c["tIn"]), "beatStartSec": r(nearest(c["tIn"], starts))} for c in cards]
            ok = all(abs(c["tIn"] - nearest(c["tIn"], starts)) <= tol_t for c in cards)
            rep.add(f"{P}.show", "pass" if ok else "fail", rows, show, f"playbook:{P}.show", toleranceSec=tol_t)
        elif show and sp is None:
            rep.add(f"{P}.show", "unmeasured", None, show, f"playbook:{P}.show", note="no audio to find onsets")
        elif show:
            lead = lc.get("leadSec") if show == "before-onset" else 0.0
            if lead is None:
                rep.add(f"{P}.show", "unmeasured", None, show, f"playbook:{P}.leadSec", note="before-onset needs leadSec")
            else:
                mine = [cd for cd in rec_cards if cd.get("layer", lid) == lid]
                anchors = [cd.get("start", c["tIn"]) for cd, c in zip(mine, cards)] if len(mine) == len(cards) else [c["tIn"] for c in cards]
                rows, ok_all = [], True
                for c, anchor in zip(cards, anchors):
                    on = nearest(anchor + lead, sp["onsets"])
                    dlt = None if on is None else c["tIn"] - (on - lead)
                    hit = dlt is not None and abs(dlt) <= tol_t
                    ok_all &= hit
                    rows.append({"cardInSec": r(c["tIn"]), "onsetSec": r(on), "deltaSec": r(dlt), "ok": bool(hit)})
                rep.add(f"{P}.show", "pass" if ok_all else "fail", rows, {"rule": show, "leadSec": lead}, f"playbook:{P}.show",
                        method=f"pixels+{audio_on}", toleranceSec=tol_t)

        hide = lc.get("hide")
        gaps = [{"outSec": r(cards[i]["tOut"]), "nextInSec": r(cards[i + 1]["tIn"]), "blankSec": r(cards[i + 1]["tIn"] - cards[i]["tOut"])}
                for i in range(len(cards) - 1)]
        if hide == "next-card":
            ok = all(g["blankSec"] < tol_t for g in gaps)
            rep.add(f"{P}.hide", "pass" if ok else "fail", gaps, hide, f"playbook:{P}.hide", toleranceSec=tol_t,
                    note="a blank shorter than the shortest counted hole is a swap, not seconds without text")
        elif hide == "beat-end":
            ends = [w_[1] for w_ in windows.values()]
            rows = [{"outSec": r(c["tOut"]), "beatEndSec": r(nearest(c["tOut"], ends))} for c in cards[:-1]]
            ok = all(abs(c["tOut"] - nearest(c["tOut"], ends)) <= tol_t for c in cards[:-1])
            rep.add(f"{P}.hide", "pass" if ok else "fail", rows, hide, f"playbook:{P}.hide", toleranceSec=tol_t)
        elif hide == "phrase-end" and sp is not None:
            rows, ok_all = [], True
            for c in cards[:-1]:
                offs = [b_ for _, b_ in sp["segments"] if c["tIn"] - tol_t <= b_ <= c["tOut"] + tol_t]
                ref = max(offs) if offs else None
                hit = ref is not None and abs(c["tOut"] - ref) <= tol_t
                ok_all &= hit
                rows.append({"outSec": r(c["tOut"]), "speechOffSec": r(ref), "ok": bool(hit)})
            rep.add(f"{P}.hide", "pass" if ok_all else "fail", rows, hide, f"playbook:{P}.hide", method=f"pixels+{audio_on}", toleranceSec=tol_t)
        elif hide:
            rep.add(f"{P}.hide", "unmeasured", gaps, hide, f"playbook:{P}.hide", note="no audio to find phrase ends")

        last = cards[-1]
        ids = lc.get("beats") or []
        layer_end = max((windows[b][1] for b in ids if b in windows), default=duration) if ids else duration
        end_frame = int(round(layer_end * fps)) - 1
        if lc.get("lastCard") == "hold-to-end":
            ok = last["last"] >= end_frame
            rep.add(f"{P}.lastCard", "pass" if ok else "fail", {"lastCardOutSec": r(last["tOut"]), "textOnFinalFrame": last["last"] >= n_frames - 1},
                    {"holdToSec": r(layer_end)}, f"playbook:{P}.lastCard")
        elif lc.get("lastCard") == "phrase-end" and sp is not None and sp["segments"]:
            off = sp["segments"][-1][1]
            rep.add(f"{P}.lastCard", "pass" if abs(last["tOut"] - off) <= tol_t else "fail", {"lastCardOutSec": r(last["tOut"])},
                    {"speechOffSec": r(off), "toleranceSec": tol_t}, f"playbook:{P}.lastCard", method=f"pixels+{audio_on}")
        elif lc.get("lastCard"):
            rep.add(f"{P}.lastCard", "unmeasured", {"lastCardOutSec": r(last["tOut"])}, lc["lastCard"], f"playbook:{P}.lastCard")

        for key in ("motionIn", "motionOut"):
            if not lc.get(key):
                continue
            kinds = [c[key] for c in cards if not (key == "motionOut" and c is last and lc.get("lastCard") == "hold-to-end")]
            if not kinds:
                continue
            major = max(set(kinds), key=kinds.count)
            ok = major == lc[key] or (lc[key] == "pop" and major in ("scale-in", "fade"))
            rep.add(f"{P}.{key}", "pass" if ok else "fail", major, lc[key], f"playbook:{P}.{key}", perCard=kinds,
                    maxEdgeFrames=max(c["inFrames" if key == "motionIn" else "outFrames"] for c in cards))

        texts = [cd.get("text", "") for cd in rec_cards if cd.get("layer", lid) == lid]
        cpc = lc.get("charsPerCard")
        if cpc and texts:
            counts = [len([ch for ch in t if not ch.isspace()]) for t in texts]
            rep.add(f"{P}.charsPerCard", "pass" if all(cpc["min"] <= n <= cpc["max"] for n in counts) else "fail", counts, cpc,
                    f"playbook:{P}.charsPerCard", method="cut.json")
        elif cpc:
            rep.add(f"{P}.charsPerCard", "unmeasured", None, cpc, f"playbook:{P}.charsPerCard", method="cut.json",
                    note="no card text in cut.json; the check does not read glyphs")
        if texts:
            rep.add(f"{P}.cardCount", "pass" if len(texts) == len(cards) else "fail", {"pixels": len(cards), "cutJson": len(texts)}, None,
                    "cut.json:cards", method="pixels+cut.json",
                    times=[{"cutJson": [cd.get("start"), cd.get("end")], "pixels": [r(c["tIn"]), r(c["tOut"])]}
                           for cd, c in zip([cd for cd in rec_cards if cd.get("layer", lid) == lid], cards)])
        st = styles.get(lid) or {}
        font = lc.get("font") or {}
        for key, tv, src in (("fontClass", font.get("class"), "font.class"), ("weight", font.get("weight"), "font.weight"),
                             ("shadow", lc.get("shadow"), "shadow"), ("plate", lc.get("plate"), "plate")):
            if key in st and tv is not None:
                rep.add(f"{P}.{src}", "pass" if st[key] == tv else "fail", st[key], tv, f"playbook:{P}.{src}", method="cut.json")
            elif tv is not None:
                rep.skip(f"{P}.{src}", f"not readable from pixels; write captionStyle.{lid}.{key} in cut.json")
        if st.get("fontFamily"):
            fams = [f.get("family") for f in fm.get("fonts") or []]
            ok = any(f and f.lower() in st["fontFamily"].lower() for f in fams)
            rep.add(f"{P}.fontFamily", "pass" if ok else "fail", st["fontFamily"], fams, "playbook:fonts", method="cut.json")

    # ----- audio -----
    aud = fm.get("audio") or {}
    if sp is None:
        rep.add("audio.stream", "unmeasured" if aud.get("voice") != "none" or (aud.get("bgm") or {}).get("present") else "pass",
                None, None, None, method="audio", note="the cut has no audio stream")
    else:
        has_speech = bool(sp["segments"])
        if aud.get("voice"):
            rep.add("audio.voice", "pass" if has_speech == (aud["voice"] != "none") else "fail",
                    {"speech": has_speech, "segments": [[r(x, 2), r(y, 2)] for x, y in sp["segments"]]}, aud["voice"], "playbook:audio.voice",
                    method=audio_on)
        all_cards = sorted((c for cs in measured_layers.values() for c in cs), key=lambda c: c["tIn"])
        if has_speech and all_cards:
            judged = len(rec_cards) == len(all_cards)
            # cut.json times are the intended phrase starts; pixels lag them by the renderer's fade-in
            starts = [cd.get("start", c["tIn"]) for cd, c in zip(rec_cards, all_cards)] if judged else [c["tIn"] for c in all_cards]
            rows, ok_all = [], True
            for i, c in enumerate(all_cards):
                lo = starts[i] - tol_t
                hi = starts[i + 1] - tol_t if i + 1 < len(all_cards) else duration + 1
                segs = [s for s in sp["segments"] if lo <= s[0] < hi]
                inner = [(segs[j][1], segs[j + 1][0]) for j in range(len(segs) - 1) if segs[j + 1][0] - segs[j][1] >= tol_t]
                allowed = sum(ch in INNER_PAUSE_MARKS for ch in rec_cards[i].get("text", "").strip().rstrip("。.!?！？")) if judged else None
                ok = None if allowed is None else len(inner) <= allowed
                ok_all &= ok is not False
                rows.append({"cardInSec": r(c["tIn"]), "holes": [[r(x, 2), r(y, 2), r(y - x, 2)] for x, y in inner],
                             "allowedByMarks": allowed, "ok": ok})
            rep.add("audio.midPhraseHoles", ("pass" if ok_all else "fail") if judged else "unmeasured", rows, {"holeMinSec": tol_t},
                    "lines:measure.minHoleSec", method=audio_on,
                    note=("a hole inside one card is allowed only where its text has an inner comma or space"
                          if judged else "judging needs the card texts in cut.json, one per measured card"))
        if has_speech:
            last_off = sp["segments"][-1][1]
            e_end = float(sp["e"][-1])
            clean = e_end <= sp["line"]
            closing = {"lastSpeechOffSec": r(last_off, 2), "tailSec": r(duration - last_off, 2), "voiceFinishesBeforeEnd": clean}
            win = tuple(float(v) for v in a.last_mora.split(":")) if a.last_mora else (
                (cut["lastMora"]["tIn"], cut["lastMora"]["tOut"]) if cut.get("lastMora") else None)
            if win:
                sel = (sp["t"] >= win[0]) & (sp["t"] <= win[1])
                peak = float(sp["e"][sel].max()) if sel.any() else 0.0
                closing.update({"lastMoraSec": [r(win[0], 2), r(win[1], 2)], "lastMoraPeakOverLine": r(peak / sp["line"], 2)})
                rep.add("audio.closing", "pass" if clean and peak > sp["line"] else "fail", closing,
                        {"lastMoraPeakOverLine": "> 1", "voiceFinishesBeforeEnd": True}, "lines:measure.speechLineFracOfMax", method=audio_on)
            else:
                rep.add("audio.closing", "unmeasured" if clean else "fail", closing, {"voiceFinishesBeforeEnd": True},
                        "lines:measure.speechLineFracOfMax", method=audio_on,
                        note="the closing mora window comes from TTS alignment (cut.json lastMora or --last-mora)")

        bgm = aud.get("bgm") or {}
        if mix is not None:
            t_, em = envelope(mix, m["envelopeWindowSec"], m["envelopeHopSec"])
            n = min(len(em), len(sp["speech"]))
            spm, em, t_ = sp["speech"][:n], em[:n], t_[:n]
            pad = int(0.1 / m["envelopeHopSec"])
            clear = np.convolve(spm.astype(float), np.ones(2 * pad + 1), "same") == 0
            bed = float(np.median(em[clear])) if clear.any() else None
            vlev = float(np.median(em[spm])) if spm.any() else None
            present = bed is not None and dbfs(bed) > m["bedFloorDbfs"]
            if "present" in bgm:
                rep.add("audio.bgm.present", "pass" if present == bgm["present"] else "fail",
                        {"bedDbfs": r(dbfs(bed), 1) if bed else None, "present": present}, bgm["present"], "playbook:audio.bgm.present", method="mix")
            if bgm.get("present") and present and vlev:
                rel = dbfs(bed) - dbfs(vlev)
                rep.add("audio.bgm.underVoice", "pass" if rel < 0 else "fail", r(rel, 1), "< 0 dB", "playbook:audio.bgm.present", method="mix",
                        note="bed is the mix level in pauses clear of speech; voice is the mix level inside speech")
                lt = rep.target("audio.bgm.levelDbUnderVoice", "audio.bgm.levelDbUnderVoice", r(rel, 1), "mix")
                if lt is not None:
                    rep.add("audio.bgm.levelDbUnderVoice", "pass" if abs(rel - lt) <= tol["levelDbAbs"] else "fail", r(rel, 1), lt,
                            "playbook:audio.bgm.levelDbUnderVoice", method="mix", toleranceDb=tol["levelDbAbs"])
            ent = at_time(bgm.get("entersAt")) if bgm.get("present") else None
            if ent is not None:
                above = np.where(em > 10 ** (m["bedFloorDbfs"] / 20))[0]
                got_e = float(t_[above[0]]) if len(above) else None
                rep.add("audio.bgm.entersAt", "pass" if got_e is not None and abs(got_e - ent) <= tol_t else "fail", r(got_e, 2), r(ent, 2),
                        "playbook:audio.bgm.entersAt", method="mix", toleranceSec=tol_t, note="first window above the bed floor; a voice that starts first also counts")
            if bgm.get("duckUnderVoice") is not None:
                rep.skip("audio.bgm.duckUnderVoice", "needs the rendered music stem; the mix cannot separate ducking from the voice")
        for i, s in enumerate(aud.get("sfx") or []):
            rep.skip(f"audio.sfx[{i}]", f"sound effects ({s.get('cue')}) are not detected in the cut check")

    # ----- cut.json: sources, route, cost, deviations -----
    ra = cut.get("audio") or {}
    srcs = ra.get("sources") or []
    unlicensed = [s.get("role") for s in srcs if not s.get("license")]
    rep.add("cut.audio.declared", "pass" if ra.get("referenceAudioUsed") is False and not unlicensed and (srcs or mix is None) else "fail",
            {"referenceAudioUsed": ra.get("referenceAudioUsed"), "roles": [s.get("role") for s in srcs], "withoutLicense": unlicensed},
            {"referenceAudioUsed": False, "everySourceLicensed": True}, "playbook:audio.referenceAudioUsed", method="cut.json")
    if mix is not None and srcs:
        loaded, missing_files = [], []
        for s in srcs:
            p = cut_dir / s.get("path", "")
            if s.get("path") and p.is_file():
                loaded.append(place(load_audio(p), len(mix), s.get("atSec", 0), s.get("inSec", 0)))
            else:
                missing_files.append(s.get("path"))
        if missing_files:
            rep.add("cut.audio.sourcesExplainMix", "unmeasured", {"missingFiles": missing_files}, None, "cut.json:audio.sources",
                    method="mix", note="source files listed in cut.json are not in the cut folder")
        else:
            ex = explained_by(mix, loaded, m["sourceFitWindowSec"])
            rep.add("cut.audio.sourcesExplainMix", "pass" if ex is not None and ex >= tol["sourcesExplainedMin"] else "fail", r(ex),
                    {"min": tol["sourcesExplainedMin"]}, "lines:tolerance.sourcesExplainedMin", method="mix",
                    note="share of the mix energy reproduced by time-varying gains on the listed files")
    if a.reference_audio and mix is not None:
        c = max_window_corr(mix, load_audio(a.reference_audio), m["referenceWindowSec"])
        rep.add("cut.audio.notReference", "pass" if c is not None and c <= tol["referenceCorrMax"] else ("unmeasured" if c is None else "fail"),
                r(c), {"max": tol["referenceCorrMax"]}, "lines:tolerance.referenceCorrMax", method="mix")

    routes = fm.get("routes") or []
    default_route = next((rt for rt in routes if rt.get("default")), None)
    rid = cut.get("route")
    route = next((rt for rt in routes if rt.get("id") == rid), None)
    if cut.get("playbook") is not None:
        rep.add("cut.playbook", "pass" if cut["playbook"] == fm.get("id") else "fail", cut["playbook"], fm.get("id"), "playbook:id", method="cut.json")
    if route is None:
        rep.add("cut.route", "fail", rid, [rt.get("id") for rt in routes], "playbook:routes", method="cut.json", note="the route is not in the playbook")
    else:
        asked = bool(cut.get("routeRequestedByMaker"))
        ok = bool(route.get("default")) or asked
        rep.add("cut.route", "pass" if ok else "fail", {"id": rid, "requestedByMaker": asked}, {"default": (default_route or {}).get("id")},
                "playbook:routes", method="cut.json", note=None if ok else "a non-default route runs only when the maker asked for it by name")
        if cut.get("container"):
            rep.add("cut.container", "pass" if cut["container"] == route.get("container") else "fail", cut["container"], route.get("container"),
                    f"playbook:routes.{rid}.container", method="cut.json")
        if "costUsd" in cut:
            cap_usd = route["costUsdPerVideo"]["max"] if route.get("paidApi") else 0
            rep.add("cut.costUsd", "pass" if cut["costUsd"] <= cap_usd + 1e-9 else "fail", cut["costUsd"], {"max": cap_usd},
                    f"playbook:routes.{rid}.costUsdPerVideo", method="cut.json")
    for path, dv in deviations.items():
        rep.add(f"cut.deviation.{path}", "pass" if dv.get("reason") else "fail", dv.get("to"), dv.get("from"), f"playbook:{path}",
                method="cut.json", note=dv.get("reason") or "a deviation needs a reason")

    # ----- people -----
    talking = bool(route and route.get("talkingHead"))
    faces = detect_faces(video, info, m)
    if faces is None:
        rep.add("people.face", "unmeasured", None, "face" if talking else "no face", f"playbook:format.onCamera={fmt.get('onCamera')}",
                method="yunet", note=f"YuNet model not in {CACHE}; rerun with --fetch-models (free download)")
    else:
        ok = faces["framesWithFace"] > 0 if talking else faces["framesWithFace"] == 0
        rep.add("people.face", "pass" if ok else "fail", faces, "face expected (talking route)" if talking else "no face",
                f"cut.json:route={rid}" if talking else f"playbook:format.onCamera={fmt.get('onCamera')}", method="yunet",
                note="detection only; the check never compares who the face is")
    if talking:
        mt = lines["mouth"]
        if voice_path is None or not voice_path.is_file():
            rep.add("people.mouth", "unmeasured", None, mt, "lines:mouth", method="talking_gate", note="needs the dry voice (cut.json voice source or --voice)")
        else:
            cmd = ([shutil.which("uv"), "run", "--quiet", "--script"] if shutil.which("uv") else [sys.executable])
            p = subprocess.run([*cmd, str(HERE / "talking_gate.py"), str(video), str(voice_path), "--search-ms", str(mt["searchMs"])],
                               capture_output=True, text=True)
            if p.returncode != 0:
                err = (p.stderr.strip().splitlines() or ["talking_gate.py failed"])[-1]
                rep.add("people.mouth", "unmeasured", None, mt, "lines:mouth", method="talking_gate", note=err[-300:])
            else:
                mo = json.loads(p.stdout)
                edge = abs(mo["bestLagMs"]) >= mt["searchMs"] - 500 / fps
                ok = (mo["pearsonAtBestLag"] >= mt["pearsonMin"] and abs(mo["bestLagMs"]) <= mt["absLagMaxMs"] and not edge
                      and (mo["meanOpenSpeech"] > mo["meanOpenPause"] or not mt["openSpeechAbovePause"]))
                rep.add("people.mouth", "pass" if ok else "fail", mo, mt, "lines:mouth", method="talking_gate",
                        note="lag at the search edge is not trusted" if edge else None)

    st_ = [c["status"] for c in rep.columns]
    verdict = "fail" if "fail" in st_ else ("unmeasured" if "unmeasured" in st_ else "pass")
    out = {
        "schema": "sasaru-gate-result/1",
        "verdict": verdict,
        "playbook": fm.get("id"),
        "cut": cut_dir.name,
        "video": video.name,
        "probe": {"width": W, "height": H, "fps": r(fps), "frames": n_frames, "durationSec": r(duration), "stretch": r(stretch),
                  "hasAudio": info["hasAudio"], "audioMeasuredOn": audio_on},
        "summary": {s: st_.count(s) for s in ("pass", "fail", "unmeasured")},
        "failed": [c["id"] for c in rep.columns if c["status"] == "fail"],
        "unmeasured": [c["id"] for c in rep.columns if c["status"] == "unmeasured"],
        "columns": rep.columns,
        "notChecked": rep.not_checked,
    }
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).write_text(txt + "\n", encoding="utf-8")
    print(txt)
    sys.exit(0 if verdict == "pass" else 3)


if __name__ == "__main__":
    main()
