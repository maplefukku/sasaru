# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["numpy>=1.26,<3", "opencv-python-headless>=4.9,<5", "mediapipe>=0.10.14,<0.11"]
# ///
"""How closely mouth opening follows the dry voice. Optional; check_cut.py calls it only for a talkingHead route. Local only.

Usage: uv run --script talking_gate.py <cut.mp4> <voice.wav> [--search-ms 200] [--until SEC]
Openness per frame = inner-lip gap / face height (MediaPipe FaceLandmarker 13-14 over 10-152).
Reports Pearson r against the voice RMS envelope at the best lag within +-search-ms, and mean openness in speech vs pauses.
The landmark model (free) is cached in $SASARU_CACHE (default ~/.cache/sasaru). Prints JSON. Exit 0 ok, 2 bad input.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
CACHE = Path(os.environ.get("SASARU_CACHE", Path.home() / ".cache" / "sasaru"))
SR = 16000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("voice")
    ap.add_argument("--search-ms", type=float, default=200)
    ap.add_argument("--until", type=float)
    a = ap.parse_args()
    if not Path(a.video).is_file() or not Path(a.voice).is_file():
        print("video or voice not found", file=sys.stderr)
        sys.exit(2)
    model = CACHE / "face_landmarker.task"
    if not model.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, model)

    lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model)), running_mode=vision.RunningMode.VIDEO, num_faces=2))
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    op, faces, i = [], [], 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)), int(i * 1000 / fps))
        faces.append(len(res.face_landmarks))
        if res.face_landmarks:
            p = res.face_landmarks[0]
            op.append(abs(p[14].y - p[13].y) / max(1e-6, abs(p[152].y - p[10].y)))
        else:
            op.append(np.nan)
        i += 1
    op = np.array(op)

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.voice, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    y = np.frombuffer(raw, np.int16).astype(np.float64) / 32768.0
    hop = int(SR / fps)
    e = np.array([np.sqrt(np.mean(y[max(0, k * hop - hop):k * hop + hop] ** 2)) if k * hop < len(y) else 0.0 for k in range(len(op))])
    n = min(len(e), len(op), int(a.until * fps) if a.until else len(op))
    x, e = op[:n], e[:n]
    ok = ~np.isnan(x)
    best = (0, -2.0)
    span = int(a.search_ms / 1000 * fps)
    for lag in range(-span, span + 1):
        m = ok & np.roll(ok, -lag)
        if m.sum() < 3:
            continue
        rr = float(np.corrcoef(np.roll(x, -lag)[m], e[m])[0, 1])
        if rr > best[1]:
            best = (lag, rr)
    speech = e > 0.1 * e.max()
    print(json.dumps({
        "frames": int(len(op)), "scoredFrames": int(n), "faceDetectedRatio": round(float(np.mean(np.array(faces) > 0)), 3),
        "maxFacesInAFrame": int(max(faces, default=0)), "pearsonAtBestLag": round(best[1], 3), "bestLagMs": round(best[0] * 1000 / fps),
        "meanOpenSpeech": round(float(np.nanmean(x[speech])), 4) if speech.any() else None,
        "meanOpenPause": round(float(np.nanmean(x[~speech])), 4) if (~speech).any() else None,
    }, indent=1))


if __name__ == "__main__":
    main()
