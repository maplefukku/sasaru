# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "opencv-python-headless>=4.10,<6",
#   "numpy>=1.26,<3",
#   "scenedetect>=0.6.4,<0.8",
#   "librosa>=0.10,<1",
#   "soundfile>=0.12,<1",
# ]
# ///
"""Mechanical pre-processing of one reference short. Judgement stays with the agent reading the images.

Usage:
  uv run --script prep.py <video> <work_dir> --tier A|B|C [--retain-days 14] [--sheet-step 0.25]
      [--content-threshold 27] [--min-scene-frames 4] [--silence-db -40] [--json]

Writes into <work_dir>:
  source<ext>            byte-for-byte copy of the input (sha256 equals the input's)
  manifest.json          provenance (tier, sha256, ingestedAt, retainedUntil), probe summary, file list
  probe.json             raw ffprobe
  shots.json             cut candidates with detector names, scores and framing similarity
  sheets/sheet_NN.jpg    timestamped tiles; labels sit above each tile, never on the picture
  sheets/index.json
  keyframes/sNNN_{first,mid,last,sharp}.jpg   unlabeled; times in keyframes/index.json
  audio/source.wav       22.05 kHz mono (only when the input has audio)
  audio/waveform.png, audio/spectrogram.png, audio/onsets.json

Needs ffmpeg and ffprobe on PATH. Reads no keys and sends nothing over the network.
Exit codes: 0 ok, 2 bad input.
"""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

LABEL_H = 22


def log(*a):
    print(*a, file=sys.stderr)


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(src, out):
    j = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(src)]).stdout)
    (out / "probe.json").write_text(json.dumps(j, indent=2))
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        raise SystemExit(2)
    num, den = map(int, v["avg_frame_rate"].split("/"))
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    w, h = int(v["width"]), int(v["height"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    return {
        "durationSec": round(float(j["format"]["duration"]), 3),
        "fps": round(num / den, 3) if den else None,
        "width": w,
        "height": h,
        "frames": int(v["nb_frames"]) if str(v.get("nb_frames", "")).isdigit() else None,
        "hasAudio": any(s["codec_type"] == "audio" for s in j["streams"]),
        "videoCodec": v.get("codec_name"),
    }


def secs(tc):
    return float(tc.seconds) if hasattr(tc, "seconds") else float(tc.get_seconds())


def detect(src, detector):
    from scenedetect import SceneManager, open_video

    video = open_video(str(src))
    sm = SceneManager()
    sm.add_detector(detector)
    sm.detect_scenes(video)
    return [secs(s) for s, _ in sm.get_scene_list()[1:]], secs(video.duration)


def frame_at(cap, t, fps):
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(round(t * fps))))
    ok, fr = cap.read()
    return fr if ok else None


def content_score(a, b):
    ha, hb = cv2.cvtColor(a, cv2.COLOR_BGR2HSV).astype(np.float32), cv2.cvtColor(b, cv2.COLOR_BGR2HSV).astype(np.float32)
    return float(np.abs(ha - hb).mean(axis=(0, 1)).mean())


def framing_similarity(a, b):
    """Share of ORB keypoints in `a` that find a mutual match in `b`. High means same framing (jump cut)."""
    orb = cv2.ORB_create(1000)
    ga = cv2.cvtColor(cv2.resize(a, (360, int(a.shape[0] * 360 / a.shape[1]))), cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(cv2.resize(b, (360, int(b.shape[0] * 360 / b.shape[1]))), cv2.COLOR_BGR2GRAY)
    ka, da = orb.detectAndCompute(ga, None)
    kb, db = orb.detectAndCompute(gb, None)
    if da is None or db is None or len(ka) < 20:
        return None
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    good = [x for x in m if x.distance < 40]
    return round(len(good) / len(ka), 3)


def shots(src, out, fps, threshold, min_frames):
    from scenedetect import AdaptiveDetector, ContentDetector

    content, dur = detect(src, ContentDetector(threshold=threshold, min_scene_len=min_frames))
    adaptive, _ = detect(src, AdaptiveDetector(min_scene_len=min_frames))
    tol = 2.5 / fps
    merged = []
    for name, ts in (("content", content), ("adaptive", adaptive)):
        for t in ts:
            hit = next((m for m in merged if abs(m["t"] - t) <= tol), None)
            if hit:
                hit["detectors"].append(name)
            else:
                merged.append({"t": t, "detectors": [name]})
    merged.sort(key=lambda m: m["t"])

    cap = cv2.VideoCapture(str(src))
    cuts = []
    for m in merged:
        before, after = frame_at(cap, m["t"] - 1 / fps, fps), frame_at(cap, m["t"], fps)
        score = content_score(before, after) if before is not None and after is not None else None
        sim = framing_similarity(before, after) if before is not None and after is not None else None
        both = len(m["detectors"]) == 2
        confident = both or (score is not None and score >= 2 * threshold)
        cuts.append({
            "t": round(m["t"], 3),
            "detectors": m["detectors"],
            "contentScore": None if score is None else round(score, 2),
            "framingSimilarity": sim,
            "kind": "jump-cut" if sim is not None and sim >= 0.25 else "cut",
            "confidence": "high" if confident else "low",
        })
    bounds = [0.0] + [c["t"] for c in cuts] + [dur]
    shot_list = [{"id": f"s{i + 1:03d}", "tIn": round(a, 3), "tOut": round(b, 3), "dur": round(b - a, 3)}
                 for i, (a, b) in enumerate(zip(bounds, bounds[1:]))]
    data = {
        "detectors": {"content": {"threshold": threshold, "minSceneFrames": min_frames},
                      "adaptive": {"minSceneFrames": min_frames}},
        "note": "confidence high = both detectors agree or the HSV jump is at least twice the threshold. "
                "jump-cut = framing similarity (ORB mutual matches) at least 0.25 across the boundary.",
        "cuts": cuts,
        "shots": shot_list,
    }
    (out / "shots.json").write_text(json.dumps(data, indent=2))
    return data


def labeled(img, text):
    band = np.zeros((LABEL_H, img.shape[1], 3), np.uint8)
    cv2.putText(band, text, (4, LABEL_H - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([band, img])


def sheets(src, out, dur, fps, step, cols=6, rows=4, tile_w=240):
    d = out / "sheets"
    d.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(src))
    times = [round(float(t), 3) for t in np.arange(0, dur, step)]
    per = cols * rows
    index = []
    for si in range(0, len(times), per):
        tiles = []
        for t in times[si:si + per]:
            fr = frame_at(cap, t, fps)
            if fr is None:
                continue
            h = int(fr.shape[0] * tile_w / fr.shape[1])
            tiles.append(labeled(cv2.resize(fr, (tile_w, h)), f"{t:6.2f}s"))
        if not tiles:
            continue
        tiles += [np.zeros_like(tiles[0])] * (per - len(tiles))
        grid = np.vstack([np.hstack(tiles[r * cols:(r + 1) * cols]) for r in range(rows)])
        name = f"sheet_{si // per + 1:02d}.jpg"
        cv2.imwrite(str(d / name), grid, [cv2.IMWRITE_JPEG_QUALITY, 88])
        index.append({"sheet": name, "tFrom": times[si], "tTo": times[min(si + per, len(times)) - 1],
                      "step": step, "grid": f"{cols}x{rows}"})
    (d / "index.json").write_text(json.dumps(index, indent=2))
    return index


def keyframes(src, out, shot_list, fps):
    d = out / "keyframes"
    d.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(src))
    index = []
    for s in shot_list:
        a, b = s["tIn"], s["tOut"]
        picks = {"first": a + 0.05, "mid": (a + b) / 2, "last": max(a, b - 0.07)}
        best_t, best_v = None, -1.0
        for t in np.linspace(a, max(a, b - 0.04), num=min(12, max(2, int((b - a) * fps)))):
            fr = frame_at(cap, t, fps)
            if fr is None:
                continue
            v = cv2.Laplacian(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
            if v > best_v:
                best_t, best_v = float(t), v
        if best_t is not None:
            picks["sharp"] = best_t
        for k, t in picks.items():
            fr = frame_at(cap, t, fps)
            if fr is None:
                continue
            name = f"{s['id']}_{k}.jpg"
            cv2.imwrite(str(d / name), fr, [cv2.IMWRITE_JPEG_QUALITY, 92])
            index.append({"file": name, "shot": s["id"], "pick": k, "t": round(t, 3)})
    (d / "index.json").write_text(json.dumps(index, indent=2))


def audio(src, out, silence_db):
    d = out / "audio"
    d.mkdir(exist_ok=True)
    wav = d / "source.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "22050", str(wav)])
    run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-filter_complex", "showwavespic=s=1600x300:split_channels=0",
         "-frames:v", "1", str(d / "waveform.png")])
    run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-lavfi", "showspectrumpic=s=1600x500:legend=1", str(d / "spectrogram.png")])
    import librosa

    y, sr = librosa.load(str(wav), sr=22050)
    onset_t = librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=False)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    rms = librosa.feature.rms(y=y)[0]
    sil = subprocess.run(["ffmpeg", "-v", "info", "-i", str(wav), "-af", f"silencedetect=n={silence_db}dB:d=0.25", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", sil)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", sil)]
    if len(ends) < len(starts):
        ends.append(round(len(y) / sr, 3))
    data = {
        "bpm": round(float(np.atleast_1d(tempo)[0]), 2),
        "bpmNote": "librosa beat_track estimate; double and half tempo not checked. audio_events.py owns the final value.",
        "beats": [round(float(b), 3) for b in beats],
        "onsets": [round(float(t), 3) for t in onset_t],
        "silence": [[round(max(0.0, a), 3), round(b, 3)] for a, b in zip(starts, ends)],
        "silenceDb": silence_db,
        "rmsMax": round(float(rms.max()), 4),
        "note": "onsets mix beats, SFX and speech. silencedetect finds nothing under continuous BGM.",
    }
    (d / "onsets.json").write_text(json.dumps(data, indent=2))
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("work_dir")
    ap.add_argument("--tier", required=True, choices=["A", "B", "C"], help="A own work, B licensed, C third-party public (analysis only)")
    ap.add_argument("--retain-days", type=int, default=14, help="days to keep the local copy; recorded as retainedUntil")
    ap.add_argument("--sheet-step", type=float, default=0.25)
    ap.add_argument("--content-threshold", type=float, default=27.0)
    ap.add_argument("--min-scene-frames", type=int, default=4)
    ap.add_argument("--silence-db", type=float, default=-40.0)
    ap.add_argument("--json", action="store_true", help="also print manifest.json to stdout")
    a = ap.parse_args()

    src_in = Path(a.video).expanduser().resolve()
    if not src_in.is_file():
        log(f"no such file: {src_in}")
        return 2
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            log(f"{tool} not on PATH")
            return 2
    out = Path(a.work_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    digest = sha256(src_in)
    src = out / f"source{src_in.suffix.lower() or '.mp4'}"
    if not src.exists() or sha256(src) != digest:
        shutil.copyfile(src_in, src)
    if sha256(src) != digest:
        log("copy does not match the input bytes")
        return 2

    try:
        p = probe(src, out)
    except (subprocess.CalledProcessError, SystemExit):
        log("ffprobe found no video stream")
        return 2
    log(f"duration={p['durationSec']}s fps={p['fps']} size={p['width']}x{p['height']} audio={p['hasAudio']}")
    sh = shots(src, out, p["fps"], a.content_threshold, a.min_scene_frames)
    log(f"cut candidates: {len(sh['cuts'])} ({sum(c['confidence'] == 'high' for c in sh['cuts'])} high)")
    sheets(src, out, p["durationSec"], p["fps"], a.sheet_step)
    keyframes(src, out, sh["shots"], p["fps"])
    files = ["probe.json", "shots.json", "sheets/index.json", "keyframes/index.json"]
    if p["hasAudio"]:
        audio(src, out, a.silence_db)
        files += ["audio/source.wav", "audio/onsets.json", "audio/waveform.png", "audio/spectrogram.png"]

    today = datetime.date.today()
    manifest = {
        "provenance": {
            "input": str(src_in),
            "copy": src.name,
            "sha256": digest,
            "rightsTier": a.tier,
            "ingestedAt": today.isoformat(),
            "retainedUntil": (today + datetime.timedelta(days=a.retain_days)).isoformat(),
            "sendOutside": a.tier != "C",
        },
        "probe": p,
        "files": files,
        "params": {"sheetStep": a.sheet_step, "contentThreshold": a.content_threshold,
                   "minSceneFrames": a.min_scene_frames, "silenceDb": a.silence_db},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    if a.json:
        print(json.dumps(manifest, ensure_ascii=False))
    log(f"done: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
