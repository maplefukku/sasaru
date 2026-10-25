#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "mediapipe==0.10.21",
#   "numpy==1.26.4",
#   "opencv-contrib-python==4.11.0.86",
# ]
# [tool.uv]
# exclude-newer = "2026-10-25T00:00:00Z"
# ///
"""Tell whether a reference is a person talking to camera, a voice-only narration, or has no voice.

usage: people_voice.py <video> <work_dir> [--audio-events audio.json] [--max-fps 30] [--json]

Speech comes from audio_events.py: --audio-events, else <work_dir>/audio.json, else this script runs
audio_events.py next to it with `uv run` and writes <work_dir>/audio.json. When audio_events left a
vocals stem in <work_dir>/stems/vocals.wav, the voice envelope is taken from it.

Per frame, MediaPipe FaceLandmarker gives the inner-lip gap (landmarks 13-14) over face height
(10-152) for the largest face. The voice envelope is the 300-3400 Hz RMS, zeroed outside speech so
a BGM bed does not count as voice. The sync score is the best Pearson r within +-200 ms. It is
compared with the same score after shifting the envelope by 1 s or more (a permutation null), so the
call does not rest on one fixed r that depends on how wide a mouth opens.

  speech none       no speech in audio.json
  speech on-camera  a face is on screen for at least 30% of the speech, r >= 0.2, and r beats the
                    shifted scores at p < 0.05 (one-sided, empirical)
  speech voiceover  speech, but not the above

onCamera is face, hands or body-no-face from FaceLandmarker, HandLandmarker and PoseLandmarker
(the last two sampled every 0.5 s on frames without a face), else none.

Output: <work_dir>/people.json. --json prints the same to stdout. Logs go to stderr.
playbook.source.reference carries onCamera and speech; hardCuts is left to the cut detector.
Exit codes: 0 ok, 2 bad input.

Models are fetched on first use into $SASARU_CACHE (default $XDG_CACHE_HOME/sasaru), Apache-2.0:
  face_landmarker.task (about 4 MB), hand_landmarker.task (about 8 MB),
  pose_landmarker_lite.task (about 6 MB).
mediapipe is pinned to 0.10.21: later releases need libEGL. Needs ffmpeg on PATH.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np

MODELS = {
    "face": ("face_landmarker.task",
             "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"),
    "hand": ("hand_landmarker.task",
             "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"),
    "pose": ("pose_landmarker_lite.task",
             "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"),
}

AUDIO_SR = 16000
LAG_SEC = 0.2
NULL_MIN_SHIFT_SEC = 1.0
SPEECH_MIN_COVERAGE = 0.05
SPEECH_MIN_SEC = 0.5
FACE_IN_SPEECH_MIN = 0.3
R_MIN = 0.2
P_MAX = 0.05
PRESENCE_MIN = 0.2
SIDE_SAMPLE_SEC = 0.5
MIN_SYNC_FRAMES_SEC = 2.0


def log(*a):
    print(*a, file=sys.stderr, flush=True)


class InputError(Exception):
    pass


def cache_dir(arg: str | None) -> Path:
    if arg:
        d = Path(arg)
    elif os.environ.get("SASARU_CACHE"):
        d = Path(os.environ["SASARU_CACHE"])
    else:
        d = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "sasaru"
    d.mkdir(parents=True, exist_ok=True)
    return d


def model_path(cache: Path, key: str) -> Path:
    name, url = MODELS[key]
    dest = cache / "mediapipe" / name
    if not dest.exists():
        log(f"fetching {url} -> {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(f"{dest.suffix}.{os.getpid()}.part")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(dest)
    return dest


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_audio(path: Path, sr: int = AUDIO_SR) -> np.ndarray:
    if not shutil.which("ffmpeg"):
        raise InputError("ffmpeg not found on PATH")
    p = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                        "-f", "f32le", "-"], capture_output=True)
    if p.returncode != 0:
        raise InputError(f"ffmpeg could not decode {path.name}: {p.stderr.decode(errors='replace').strip()}")
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def band_envelope(y: np.ndarray, times: np.ndarray, win_sec: float, sr: int = AUDIO_SR,
                  lo: float = 300.0, hi: float = 3400.0) -> np.ndarray:
    """Speech-band RMS centred on each frame time, from FFT bins of a Hann window."""
    win = max(64, int(win_sec * sr))
    freqs = np.fft.rfftfreq(win, 1 / sr)
    band = (freqs >= lo) & (freqs <= hi)
    hann = np.hanning(win)
    out = np.zeros(len(times))
    pad = np.pad(y, (win, win))
    for i, t in enumerate(times):
        c = int(t * sr) + win
        seg = pad[c - win // 2 : c - win // 2 + win] * hann
        out[i] = np.sqrt(np.mean(np.abs(np.fft.rfft(seg)[band]) ** 2) + 1e-20)
    return out


def speech_mask(times: np.ndarray, segments: list[dict]) -> np.ndarray:
    m = np.zeros(len(times), bool)
    for s in segments:
        m |= (times >= s["tStart"]) & (times < s["tEnd"])
    return m


def corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or a.std() < 1e-12 or b.std() < 1e-12:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def best_lag_r(open_: np.ndarray, env: np.ndarray, valid: np.ndarray, max_lag: int) -> tuple[float, int]:
    """Best r over lags; a positive lag means the mouth moves after the sound."""
    best, best_lag = float("nan"), 0
    n = len(open_)
    for lag in range(-max_lag, max_lag + 1):
        idx = np.arange(n)
        j = idx + lag
        ok = (j >= 0) & (j < n)
        ok[ok] &= valid[j[ok]] & valid[idx[ok]]
        r = corr(open_[j[ok]], env[idx[ok]])
        if np.isfinite(r) and (not np.isfinite(best) or r > best):
            best, best_lag = r, lag
    return best, best_lag


def sync_score(open_: np.ndarray, env: np.ndarray, valid: np.ndarray, fps: float) -> dict:
    """Observed best-lag r against the same statistic with the envelope circularly shifted."""
    max_lag = int(round(LAG_SEC * fps))
    r_obs, lag = best_lag_r(open_, env, valid, max_lag)
    n = len(env)
    min_shift = int(np.ceil(NULL_MIN_SHIFT_SEC * fps))
    shifts = list(range(min_shift, n - min_shift + 1, max(1, int(round(fps / 10)))))
    null = []
    for k in shifts:
        r, _ = best_lag_r(open_, np.roll(env, k), valid, max_lag)
        if np.isfinite(r):
            null.append(r)
    null = np.array(null)
    out = {"r": None if not np.isfinite(r_obs) else round(r_obs, 3), "bestLagMs": round(lag * 1000 / fps),
           "nullShifts": int(len(null)), "nullMean": None, "nullStd": None, "nullP95": None, "z": None, "p": None}
    if len(null) >= 10 and np.isfinite(r_obs):
        sd = float(null.std()) or 1e-6
        out.update(nullMean=round(float(null.mean()), 3), nullStd=round(sd, 3),
                   nullP95=round(float(np.percentile(null, 95)), 3), z=round((r_obs - float(null.mean())) / sd, 2),
                   p=round((1 + int((null >= r_obs).sum())) / (1 + len(null)), 3))
    return out


def decide(speech_sec: float, coverage: float, face_in_speech: float | None, sync: dict | None,
           face_ratio: float, hands_ratio: float | None, body_ratio: float | None) -> tuple[str, str, list[str]]:
    reasons = []
    if speech_sec < SPEECH_MIN_SEC or coverage < SPEECH_MIN_COVERAGE:
        speech = "none"
        reasons.append(f"speech {speech_sec:.2f} s ({coverage:.0%}) is below {SPEECH_MIN_SEC} s or {SPEECH_MIN_COVERAGE:.0%}")
    elif face_in_speech is None or face_in_speech < FACE_IN_SPEECH_MIN:
        speech = "voiceover"
        reasons.append(f"a face is on screen for {0 if face_in_speech is None else face_in_speech:.0%} of the speech "
                       f"(needs {FACE_IN_SPEECH_MIN:.0%})")
    elif not sync or sync.get("r") is None or sync.get("p") is None:
        speech = "voiceover"
        reasons.append("too few face frames inside speech to score mouth sync")
    elif sync["r"] >= R_MIN and sync["p"] < P_MAX:
        speech = "on-camera"
        reasons.append(f"mouth follows the voice: r {sync['r']} at {sync['bestLagMs']} ms, above "
                       f"{1 - sync['p']:.0%} of the scores with the audio shifted by {NULL_MIN_SHIFT_SEC} s or more")
    else:
        speech = "voiceover"
        reasons.append(f"face on screen but the mouth does not follow the voice: r {sync['r']}, p {sync['p']} "
                       f"against shifted audio (needs r >= {R_MIN} and p < {P_MAX})")
    if face_ratio >= PRESENCE_MIN:
        on_camera = "face"
    elif hands_ratio is not None and hands_ratio >= PRESENCE_MIN:
        on_camera = "hands"
    elif body_ratio is not None and body_ratio >= PRESENCE_MIN:
        on_camera = "body-no-face"
    else:
        on_camera = "none"
    reasons.append(f"face in {face_ratio:.0%} of frames, hands in "
                   f"{'n/a' if hands_ratio is None else f'{hands_ratio:.0%}'}, body without face in "
                   f"{'n/a' if body_ratio is None else f'{body_ratio:.0%}'} of sampled frames")
    return speech, on_camera, reasons


def load_audio_events(video: Path, work: Path, given: str | None, cache_arg: str | None) -> tuple[dict, Path]:
    path = Path(given) if given else work / "audio.json"
    if not path.exists():
        if given:
            raise InputError(f"not found: {path}")
        script = Path(__file__).with_name("audio_events.py")
        if not shutil.which("uv") or not script.exists():
            raise InputError("no audio.json; run audio_events.py first or pass --audio-events")
        log("no audio.json: running audio_events.py")
        cmd = ["uv", "run", "-q", "--script", str(script), str(video), str(work)]
        if cache_arg:
            cmd += ["--cache", cache_arg]
        p = subprocess.run(cmd, stdout=sys.stderr)
        if p.returncode != 0:
            raise InputError("audio_events.py failed")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("tool") != "audio_events" or "speech" not in data:
        raise InputError(f"{path.name} is not audio_events output")
    return data, path


def scan_video(video: Path, cache: Path, max_fps: float):
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise InputError(f"cannot open video {video.name}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    if fps <= 0:
        raise InputError(f"{video.name} has no frame rate")
    step = max(1, int(round(fps / max_fps)))
    face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path(cache, "face"))),
        running_mode=vision.RunningMode.VIDEO, num_faces=2))
    hand = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path(cache, "hand"))),
        running_mode=vision.RunningMode.IMAGE, num_hands=2))
    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path(cache, "pose"))),
        running_mode=vision.RunningMode.IMAGE))
    side_every = max(1, int(round(SIDE_SAMPLE_SEC * fps / step)))
    times, opening, faces, heights, centres = [], [], [], [], []
    side = {"sampled": 0, "hands": 0, "body": 0}
    i = k = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step:
            i += 1
            continue
        t = i / fps
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        res = face.detect_for_video(img, int(round(t * 1000)))
        faces.append(len(res.face_landmarks))
        if res.face_landmarks:
            p = max(res.face_landmarks, key=lambda q: abs(q[152].y - q[10].y))
            h = abs(p[152].y - p[10].y)
            opening.append(abs(p[14].y - p[13].y) / max(1e-6, h))
            heights.append(h)
            centres.append(((p[10].x + p[152].x) / 2, (p[10].y + p[152].y) / 2))
        else:
            opening.append(np.nan)
            if k % side_every == 0:
                side["sampled"] += 1
                if hand.detect(img).hand_landmarks:
                    side["hands"] += 1
                pr = pose.detect(img)
                if pr.pose_landmarks:
                    lm = pr.pose_landmarks[0]
                    if min(lm[11].visibility, lm[12].visibility) >= 0.5:
                        side["body"] += 1
        times.append(t)
        i += 1
        k += 1
    cap.release()
    if not times:
        raise InputError(f"{video.name} has no readable frames")
    return {"fps": fps, "step": step, "times": np.array(times), "opening": np.array(opening),
            "faces": np.array(faces), "heights": heights, "centres": centres, "side": side}


def analyse(video: Path, work: Path, audio_events: str | None, cache_arg: str | None, max_fps: float) -> dict:
    cache = cache_dir(cache_arg)
    ae, ae_path = load_audio_events(video, work, audio_events, cache_arg)
    segs = ae["speech"].get("segments", [])
    log(f"scanning {video.name}")
    v = scan_video(video, cache, max_fps)
    times, opening, faces = v["times"], v["opening"], v["faces"]
    eff_fps = v["fps"] / v["step"]
    dur = float(times[-1] + 1 / eff_fps)

    vocals = work / "stems" / "vocals.wav"
    sep = ae.get("separation") or {}
    use_vocals = vocals.exists() and ae.get("stage") == "separated-htdemucs"
    y = decode_audio(vocals if use_vocals else video)
    env = band_envelope(y, times, 2.0 / eff_fps)
    sp = speech_mask(times, segs)
    gated = np.where(sp, env, 0.0)

    has_face = faces > 0
    speech_sec = float(sum(s["tEnd"] - s["tStart"] for s in segs))
    coverage = speech_sec / dur if dur else 0.0
    face_in_speech = float(has_face[sp].mean()) if sp.any() else None
    valid = has_face & np.isfinite(opening)
    sync = None
    if valid.sum() >= MIN_SYNC_FRAMES_SEC * eff_fps and sp.any():
        sync = sync_score(np.nan_to_num(opening), gated, valid, eff_fps)
        os_, op_ = valid & sp, valid & ~sp
        sync["openSpeech"] = round(float(opening[os_].mean()), 4) if os_.any() else None
        sync["openPause"] = round(float(opening[op_].mean()), 4) if op_.any() else None
        sync["framesUsed"] = int(valid.sum())

    side = v["side"]
    hands_ratio = side["hands"] / side["sampled"] * (1 - has_face.mean()) if side["sampled"] else None
    body_ratio = side["body"] / side["sampled"] * (1 - has_face.mean()) if side["sampled"] else None
    face_ratio = float(has_face.mean())
    speech, on_camera, reasons = decide(speech_sec, coverage, face_in_speech, sync, face_ratio, hands_ratio, body_ratio)
    centre = np.mean(v["centres"], 0) if v["centres"] else None

    return {
        "tool": "people_voice",
        "version": 1,
        "measuredAt": datetime.date.today().isoformat(),
        "input": {"name": video.name, "sha256": sha256(video), "durationSec": round(dur, 3),
                  "fps": round(v["fps"], 3), "framesScored": int(len(times)), "frameStep": v["step"]},
        "speechSource": {"file": ae_path.name, "stage": ae.get("stage"), "envelope": "vocals stem" if use_vocals else "mix",
                         "separationTrusted": sep.get("trusted"), "speechSec": round(speech_sec, 2),
                         "coverage": round(coverage, 3)},
        "face": {"ratio": round(face_ratio, 3), "maxFaces": int(faces.max()),
                 "inSpeechRatio": None if face_in_speech is None else round(face_in_speech, 3),
                 "heightRatioMedian": round(float(np.median(v["heights"])), 3) if v["heights"] else None,
                 "centre": None if centre is None else {"cx": round(float(centre[0]), 3), "cy": round(float(centre[1]), 3)}},
        "hands": {"ratio": None if hands_ratio is None else round(hands_ratio, 3), "sampledFrames": side["sampled"]},
        "body": {"ratio": None if body_ratio is None else round(body_ratio, 3), "sampledFrames": side["sampled"]},
        "sync": sync,
        "decision": {"speech": speech, "onCamera": on_camera, "talkingHead": speech == "on-camera", "reasons": reasons},
        "thresholds": {"faceInSpeechMin": FACE_IN_SPEECH_MIN, "rMin": R_MIN, "pMax": P_MAX, "lagMs": int(LAG_SEC * 1000),
                       "nullMinShiftSec": NULL_MIN_SHIFT_SEC, "presenceMin": PRESENCE_MIN},
        "models": [{"name": f"MediaPipe {MODELS[k][0]}", "license": "Apache-2.0"} for k in MODELS],
        "playbook": {"source": {"reference": {"onCamera": on_camera, "speech": speech}}},
        "evidence": {"measured": ["source.reference.onCamera", "source.reference.speech"], "inferred": [], "unmeasured": []},
        "notes": [
            "playbook.source.reference is a fragment to merge; hardCuts comes from the cut detector.",
            "talkingHead true means the default recipe must not copy the on-camera speech: format.speech is none or voiceover.",
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("work_dir")
    ap.add_argument("--audio-events", help="audio_events.py output (default <work_dir>/audio.json)")
    ap.add_argument("--max-fps", type=float, default=30.0, help="frames per second to score (default 30)")
    ap.add_argument("--cache", help="model cache directory (default $SASARU_CACHE or $XDG_CACHE_HOME/sasaru)")
    ap.add_argument("--json", action="store_true", help="also print the result to stdout")
    a = ap.parse_args(argv)
    video = Path(a.video)
    if not video.is_file():
        log(f"not a file: {video}")
        return 2
    work = Path(a.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    try:
        out = analyse(video, work, a.audio_events, a.cache, a.max_fps)
    except InputError as exc:
        log(str(exc))
        return 2
    text = json.dumps(out, ensure_ascii=False, indent=2)
    (work / "people.json").write_text(text + "\n", encoding="utf-8")
    log(f"wrote {work / 'people.json'}")
    if a.json:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
