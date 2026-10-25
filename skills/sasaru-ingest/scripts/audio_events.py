#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "numpy==2.2.6",
#   "scipy==1.15.3",
#   "soundfile==0.13.1",
#   "librosa==0.11.0",
#   "torch==2.9.1",
#   "torchaudio==2.9.1",
#   "panns-inference==0.1.1",
#   "torchlibrosa==0.1.0",
#   "matplotlib==3.10.3",
#   "beat-this==1.1.0",
#   "demucs==4.1.0",
#   "pyyaml==6.0.2",
# ]
# [tool.uv]
# exclude-newer = "2026-10-25T00:00:00Z"
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
# [tool.uv.sources]
# torch = { index = "pytorch-cpu" }
# torchaudio = { index = "pytorch-cpu" }
# ///
"""Measure voice, BGM and sound effects in one reference clip, without sending it anywhere.

usage: audio_events.py <audio_or_video> <work_dir> [--beats FILE] [--separate none|music] [--json]

Stage 1 (default, --separate none) reads the mix as it is:
  - speech region from PANNs SED (AudioSet "Speech" family), then pauses inside it found as
    dips relative to the voice level. An absolute silence threshold finds nothing under a BGM bed.
  - BGM from what is left between and around the speech: its level, and whether PANNs hears music
    in it once the pauses are stitched together and normalised.
  - tempo from beat_this beats, reported only when the beats are regular. Octave errors are checked
    with beat_this downbeats (8 beats per bar means double tempo) and the onset autocorrelation.
  - sound-effect hits: onsets that PANNs tags with an effect class, sharp rises, and high-band
    swells (whooshes, risers). The last two only off the beat grid and away from speech, so a hit
    that lands on a word is found only when PANNs tags it.
Stage 2 (--separate music) splits the mix with Demucs htdemucs into vocals and the rest, then
measures the BGM level, ducking and tempo on the rest. Speech stays on the mix unless the mix shows
no pauses. The stage checks itself: in speech pauses the rest should be about the mix, so when it
is more than 3 dB quieter there, the stems are not trusted and the BGM numbers fall back to stage 1
(output "separation.trusted"). Sustained pads and drones are where that happens. Stems stay in
<work_dir>/stems/ and are never part of a playbook.

Only stage 2 with trusted stems puts audio.bgm.levelDbUnderVoice under evidence.measured. Stage 1
estimates the BGM under the voice from the pauses, which is off when the BGM swells or dips with
the voice, so it lands under evidence.inferred.

--beats takes a playbook .md or a JSON list (or {"beats": [...]}) of {id, tIn, tOut}. With it, the
playbook fragment carries times as {beat, offsetSec}. Without it, audio.bgm.entersAt is keyed to b1
as if b1 starts at 0 s (and listed as inferred), and sound effects carry no at. Seconds are always
in the detail sections.

The fragment follows the schema's BGM rules: with BGM, character and entersAt are always written;
without BGM, only present is. duckUnderVoice and levelDbUnderVoice are left out when the reference
has no speech, and are null only when unmeasured (then listed in evidence.unmeasured). Evidence
paths index list items, such as audio.sfx[0].cue.

Output: <work_dir>/audio.json. --json prints the same to stdout. Logs go to stderr.
Exit codes: 0 ok, 2 bad input.

Models are fetched on first use into $SASARU_CACHE (default $XDG_CACHE_HOME/sasaru):
  PANNs Cnn14_DecisionLevelMax (Zenodo 3987831, about 330 MB, weights CC-BY-4.0, code MIT)
  AudioSet class labels csv (about 15 KB)
  beat_this final0 (code and weights MIT)
  Demucs htdemucs, only with --separate music (MIT)
Needs ffmpeg on PATH.
"""

from __future__ import annotations

import argparse
import contextlib
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

SR = 32000
HOP = 320
FPS = SR // HOP

PANNS_URL = "https://zenodo.org/record/3987831/files/Cnn14_DecisionLevelMax_mAP%3D0.385.pth?download=1"
PANNS_FILE = "Cnn14_DecisionLevelMax_mAP=0.385.pth"
LABELS_URL = "http://storage.googleapis.com/us_audioset/youtube_corpus/v1/csv/class_labels_indices.csv"

SPEECH_CLASSES = [
    "Speech",
    "Male speech, man speaking",
    "Female speech, woman speaking",
    "Child speech, kid speaking",
    "Conversation",
    "Narration, monologue",
    "Speech synthesizer",
]
MUSIC_FIRST, MUSIC_LAST = 137, 282
SFX_CLASSES = [
    "Whoosh, swoosh, swish",
    "Ding",
    "Ding-dong",
    "Burst, pop",
    "Camera",
    "Scratching (performance technique)",
    "Boing",
    "Zing",
    "Cash register",
    "Clicking",
    "Beep, bleep",
    "Drum roll",
    "Sound effect",
    "Chime",
    "Bell",
    "Jingle bell",
    "Thump, thud",
    "Whip",
    "Slam",
    "Bang",
    "Explosion",
    "Glass",
    "Chink, clink",
    "Tick",
    "Typing",
    "Zipper (clothing)",
    "Laughter",
    "Applause",
    "Gasp",
]

SPEECH_ON, SPEECH_OFF = 0.30, 0.20
PAUSE_MIN_SEC = 0.12
PAUSE_SPLIT = 0.45
PAUSE_MIN_SPREAD_DB = 12.0
BED_FLOOR_DBFS = -70.0
MUSIC_LIKE_MIN = 0.03
BEAT_ALIGN_SEC = 0.06
SPEECH_GUARD_SEC = 0.15
REPEAT_EXCESS_DB = 6.0
SFX_TAG_LIFT = 0.08
SED_RESOLUTION_SEC = 0.5
SWELL_DB = 8.0
SWELL_MIN_SEC, SWELL_MAX_SEC = 0.1, 1.2
DUCK_DB = 4.0
NO_DUCK_DB = 2.0
MIN_RETENTION_DB = -3.0


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


def fetch(url: str, dest: Path) -> Path:
    if not dest.exists():
        log(f"fetching {url} -> {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(dest)
    return dest


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode(path: Path, sr: int, channels: int = 1) -> np.ndarray:
    if not shutil.which("ffmpeg"):
        raise InputError("ffmpeg not found on PATH")
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-vn", "-ac", str(channels),
           "-ar", str(sr), "-f", "f32le", "-"]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise InputError(f"ffmpeg could not decode {path.name}: {p.stderr.decode(errors='replace').strip()}")
    y = np.frombuffer(p.stdout, dtype=np.float32)
    if y.size == 0:
        raise InputError(f"{path.name} has no audio stream")
    return y.reshape(-1, channels).T.copy() if channels > 1 else y.copy()


def frame_db(y: np.ndarray, win: int = 3 * HOP) -> np.ndarray:
    n = int(np.ceil(len(y) / HOP))
    pad = np.pad(y.astype(np.float64), (win // 2, win))
    c = np.concatenate([[0.0], np.cumsum(pad**2)])
    starts = np.arange(n) * HOP
    p = (c[starts + win] - c[starts]) / win
    return 10 * np.log10(p + 1e-12)


def power(db: np.ndarray) -> np.ndarray:
    return 10 ** (np.asarray(db) / 10)


def mean_db(db: np.ndarray) -> float | None:
    db = np.asarray(db)
    return None if db.size == 0 else float(10 * np.log10(power(db).mean() + 1e-12))


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    m = np.concatenate([[False], np.asarray(mask, bool), [False]])
    d = np.diff(m.astype(np.int8))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def hysteresis(x: np.ndarray, on: float, off: float) -> np.ndarray:
    out = np.zeros(len(x), bool)
    active = False
    for i, v in enumerate(x):
        active = v >= on if not active else v >= off
        out[i] = active
    return out


def clean_mask(mask: np.ndarray, min_len: int, max_gap: int) -> np.ndarray:
    m = np.asarray(mask, bool).copy()
    for s, e in runs(~m):
        if s > 0 and e < len(m) and e - s <= max_gap:
            m[s:e] = True
    for s, e in runs(m):
        if e - s < min_len:
            m[s:e] = False
    return m


def segs_from_mask(mask: np.ndarray, fps: int = FPS) -> list[dict]:
    return [{"tStart": round(s / fps, 2), "tEnd": round(e / fps, 2)} for s, e in runs(mask)]


def median_smooth(x: np.ndarray, k: int | tuple[int, ...]) -> np.ndarray:
    from scipy.ndimage import median_filter

    size = tuple(max(1, v) for v in k) if isinstance(k, tuple) else max(1, k)
    return median_filter(x, size=size, mode="nearest")


def detect_speech(fw: np.ndarray, db: np.ndarray, panns: "Panns", gate_db: float | None = None
                  ) -> tuple[np.ndarray, dict]:
    """Speech region from PANNs (its frames are 0.32 s blocks, so it spans short pauses), then the
    pauses cut out of it as level dips."""
    sp = median_smooth(fw[:, panns.speech_idx].max(1), int(0.2 * FPS))
    region = clean_mask(hysteresis(sp, SPEECH_ON, SPEECH_OFF), int(0.15 * FPS), int(0.3 * FPS))
    if gate_db is not None:
        region &= db > max(-60.0, float(np.percentile(db, 95)) - gate_db)
    pauses, info = find_pauses(db, region)
    return clean_mask(region & ~pauses, int(0.1 * FPS), 0), info


def find_pauses(db: np.ndarray, region: np.ndarray, fps: int = FPS) -> tuple[np.ndarray, dict]:
    """Frames inside the speech region that sit well below the voice. Thresholds are relative to the
    region's own level spread, so a BGM bed under the voice does not hide the pauses."""
    vals = db[region]
    info = {"method": "relative-dip", "thresholdDb": None, "spreadDb": None}
    pauses = np.zeros(len(db), bool)
    if vals.size < fps // 2:
        return pauses, info
    lo, hi = np.percentile(vals, 10), np.percentile(vals, 90)
    info["spreadDb"] = round(float(hi - lo), 1)
    if hi - lo < PAUSE_MIN_SPREAD_DB:
        return pauses, info
    thr = lo + PAUSE_SPLIT * (hi - lo)
    info["thresholdDb"] = round(float(thr), 1)
    low = region & (db < thr)
    min_len = int(round(PAUSE_MIN_SEC * fps))
    for s, e in runs(low):
        if e - s >= min_len:
            pauses[s:e] = True
    return pauses, info


def stitch(y: np.ndarray, mask: np.ndarray, min_frames: int = 6, fade: int = 160) -> np.ndarray:
    parts = []
    for s, e in runs(mask):
        if e - s < min_frames:
            continue
        seg = y[s * HOP : e * HOP].astype(np.float32).copy()
        f = min(fade, len(seg) // 4)
        if f > 0:
            ramp = np.linspace(0, 1, f, dtype=np.float32)
            seg[:f] *= ramp
            seg[-f:] *= ramp[::-1]
        parts.append(seg)
    return np.concatenate(parts) if parts else np.zeros(0, np.float32)


def normalise(y: np.ndarray, target_dbfs: float = -20.0) -> np.ndarray:
    rms = np.sqrt(np.mean(y.astype(np.float64) ** 2)) + 1e-12
    return (y * (10 ** (target_dbfs / 20) / rms)).astype(np.float32)


def autocorr_support(env: np.ndarray, fps: float, bpm: float) -> float:
    e = env - env.mean()
    if e.std() < 1e-9 or bpm <= 0:
        return 0.0
    ac = np.correlate(e, e, mode="full")[len(e) - 1 :]
    ac = ac / (ac[0] + 1e-12)
    lag = 60.0 * fps / bpm
    lo, hi = int(np.floor(lag * 0.97)), int(np.ceil(lag * 1.03))
    if hi >= len(ac) or lo < 1:
        return 0.0
    return float(max(0.0, ac[lo : hi + 1].max()))


def choose_tempo(beats: np.ndarray, downbeats: np.ndarray, env: np.ndarray | None, env_fps: float,
                 source: str) -> dict:
    """Tempo from beat times with an explicit octave check. Returns bpm None when the beats are too
    few or too irregular to be a tempo."""
    out = {"bpm": None, "confidence": 0.0, "candidates": [], "beatsPerBar": None, "octaveRule": None,
           "source": source, "beatCount": int(len(beats)), "ibiCv": None}
    if len(beats) < 8:
        out["octaveRule"] = "fewer than 8 beats: no tempo"
        return out
    ibi = np.diff(beats)
    med = float(np.median(ibi))
    cv = float(np.std(ibi) / (np.mean(ibi) + 1e-9))
    out["ibiCv"] = round(cv, 3)
    if cv > 0.25:
        out["octaveRule"] = "beat intervals irregular (cv > 0.25): no tempo"
        return out
    bpm0 = 60.0 / med
    bpb = None
    if len(downbeats) >= 3:
        idx = np.searchsorted(beats, downbeats - 1e-3)
        counts = np.diff(idx)
        counts = counts[counts > 0]
        if counts.size:
            bpb = int(np.median(counts))
    out["beatsPerBar"] = bpb
    sup = {r: (autocorr_support(env, env_fps, bpm0 * r) if env is not None else None) for r in (0.5, 1.0, 2.0)}
    out["candidates"] = [{"ratio": r, "bpm": round(bpm0 * r, 1), "support": None if s is None else round(s, 3)}
                         for r, s in sup.items()]
    s_half, s_one, s_two = sup[0.5], sup[1.0], sup[2.0]
    ratio, rule = 1.0, "kept the beat tracker's level"
    if bpb is not None and bpb >= 6 and bpb % 2 == 0:
        ratio, rule = 0.5, f"{bpb} beats per bar: halved"
    elif bpm0 > 150 and s_half and s_half >= 0.5 * (s_one or 0.0):
        ratio, rule = 0.5, "above 150 BPM and the half tempo is as periodic: halved"
    elif bpm0 < 60 and s_two and s_two >= 0.5 * (s_one or 0.0):
        ratio, rule = 2.0, "below 60 BPM and the double tempo is as periodic: doubled"
    out["bpm"] = round(bpm0 * ratio, 1)
    out["octaveRule"] = rule
    out["confidence"] = round(float(np.clip(1.0 - cv / 0.25, 0, 1)), 2)
    return out


def load_beats(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".md", ".yaml", ".yml"):
        import yaml

        if path.suffix.lower() == ".md":
            parts = text.split("---\n")
            if len(parts) < 3:
                raise InputError(f"{path.name} has no YAML frontmatter")
            text = parts[1]
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    beats = data.get("beats") if isinstance(data, dict) else data
    if not isinstance(beats, list) or not beats:
        raise InputError(f"{path.name} has no beats list")
    out = []
    for b in beats:
        try:
            out.append({"id": str(b["id"]), "tIn": float(b["tIn"]), "tOut": float(b["tOut"])})
        except (KeyError, TypeError, ValueError) as exc:
            raise InputError(f"bad beat in {path.name}: {b!r}") from exc
    return sorted(out, key=lambda b: b["tIn"])


def to_at(t: float | None, beats: list[dict] | None) -> dict | None:
    """Seconds on the reference timeline to {beat, offsetSec}: the last beat whose tIn <= t."""
    if t is None or not beats:
        return None
    chosen = beats[0]
    for b in beats:
        if b["tIn"] <= t + 1e-9:
            chosen = b
    return {"beat": chosen["id"], "offsetSec": round(max(0.0, t - chosen["tIn"]), 2)}


def sfx_type(label: str) -> str:
    return label.split(",")[0].split("(")[0].strip().lower().replace(" ", "-")


class Panns:
    def __init__(self, cache: Path):
        labels_csv = Path.home() / "panns_data" / "class_labels_indices.csv"
        fetch(LABELS_URL, labels_csv)
        ckpt = fetch(PANNS_URL, cache / PANNS_FILE)
        with contextlib.redirect_stdout(sys.stderr):
            from panns_inference import SoundEventDetection, labels

            self.sed = SoundEventDetection(checkpoint_path=str(ckpt), device="cpu")
        self.labels = list(labels)
        index = {name: i for i, name in enumerate(self.labels)}
        self.speech_idx = [index[c] for c in SPEECH_CLASSES if c in index]
        self.sfx_idx = [index[c] for c in SFX_CLASSES if c in index]
        self.music_idx = list(range(MUSIC_FIRST, MUSIC_LAST + 1))

    def framewise(self, y: np.ndarray, chunk_sec: float = 20.0) -> np.ndarray:
        import torch

        n_frames = int(np.ceil(len(y) / HOP))
        out = []
        step = int(chunk_sec * SR)
        for s in range(0, len(y), step):
            seg = y[s : s + step]
            if len(seg) < SR // 2:
                seg = np.pad(seg, (0, SR // 2 - len(seg)))
            with torch.no_grad(), contextlib.redirect_stdout(sys.stderr):
                fw = self.sed.inference(seg[None, :].astype(np.float32))[0]
            out.append(fw[: int(np.ceil(min(step, len(y) - s) / HOP))])
        fw = np.concatenate(out, 0)
        if len(fw) < n_frames:
            fw = np.pad(fw, ((0, n_frames - len(fw)), (0, 0)), mode="edge")
        return fw[:n_frames]


def run_beat_this(y: np.ndarray, sr: int, cache: Path) -> tuple[np.ndarray, np.ndarray]:
    os.environ.setdefault("TORCH_HOME", str(cache / "torch"))
    with contextlib.redirect_stdout(sys.stderr):
        from beat_this.inference import Audio2Beats

        a2b = Audio2Beats(checkpoint_path="final0", device="cpu", dbn=False)
        beats, downbeats = a2b(y.astype(np.float32), sr)
    return np.asarray(beats, float), np.asarray(downbeats, float)


def separate(path: Path, work: Path, cache: Path) -> tuple[np.ndarray, np.ndarray]:
    os.environ.setdefault("TORCH_HOME", str(cache / "torch"))
    os.environ.setdefault("HF_HOME", str(cache / "huggingface"))
    import soundfile as sf
    import torch

    with contextlib.redirect_stdout(sys.stderr):
        from demucs.apply import apply_model
        from demucs.pretrained import get_model

        model = get_model("htdemucs")
        model.eval()
    msr = model.samplerate
    wav = torch.from_numpy(decode(path, msr, channels=2))
    ref = wav.mean(0)
    mu, sd = ref.mean(), ref.std() + 1e-8
    with torch.no_grad(), contextlib.redirect_stdout(sys.stderr):
        src = apply_model(model, ((wav - mu) / sd)[None], device="cpu", split=True, overlap=0.25, progress=False)[0]
    src = src * sd + mu
    names = list(model.sources)
    vocals = src[names.index("vocals")]
    rest = src.sum(0) - vocals
    stems = work / "stems"
    stems.mkdir(parents=True, exist_ok=True)
    sf.write(stems / "vocals.wav", vocals.T.numpy(), msr)
    sf.write(stems / "accompaniment.wav", rest.T.numpy(), msr)
    import librosa

    v = librosa.resample(vocals.mean(0).numpy(), orig_sr=msr, target_sr=SR)
    r = librosa.resample(rest.mean(0).numpy(), orig_sr=msr, target_sr=SR)
    return v.astype(np.float32), r.astype(np.float32)


def high_band_db(y: np.ndarray, cutoff: float = 2000.0) -> np.ndarray:
    import librosa

    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=HOP, center=True)) ** 2
    freqs = librosa.fft_frequencies(sr=SR, n_fft=1024)
    return 10 * np.log10(S[freqs >= cutoff].mean(0) + 1e-12)


def swells(hb: np.ndarray) -> list[tuple[int, int, float]]:
    """High-band bumps over a 1.5 s running median: whooshes and risers rise too slowly for an
    onset detector."""
    excess = hb - median_smooth(hb, int(1.5 * FPS))
    out = []
    for s, e in runs(excess >= SWELL_DB):
        if SWELL_MIN_SEC * FPS <= e - s <= SWELL_MAX_SEC * FPS:
            a = s
            while a > 0 and excess[a - 1] >= 3.0 and s - a < FPS // 2:
                a -= 1
            out.append((a, e, float(excess[s:e].max())))
    return out


def mel_db(y: np.ndarray) -> np.ndarray:
    import librosa

    m = librosa.feature.melspectrogram(y=y, sr=SR, n_fft=1024, hop_length=HOP, n_mels=64)
    return librosa.power_to_db(m, ref=np.max, top_db=80.0)


def repeats(mel: np.ndarray, q: int, period: float | None, span: int = 4) -> bool:
    """True when the sound at q is already there 1-4 beats before or after: part of the groove,
    not a one-off hit. Compared per mel band, so an effect stacked on a kick still stands out."""
    if not period:
        return False
    n = mel.shape[1]
    v = mel[:, q : q + span].mean(1)
    close = 0
    for k in (-4, -3, -2, -1, 1, 2, 3, 4):
        c0 = int(round(q + k * period))
        best = None
        for c in range(max(0, c0 - 3), min(n - span, c0 + 4)):
            excess = float(np.maximum(0.0, v - mel[:, c : c + span].mean(1)).mean())
            best = excess if best is None else min(best, excess)
        if best is not None and best < REPEAT_EXCESS_DB:
            close += 1
    return close >= 2


def detect_sfx(y: np.ndarray, fw: np.ndarray, panns: Panns, db: np.ndarray, speech: np.ndarray,
               beats: np.ndarray, bpm: float | None) -> list[dict]:
    """Three detectors, merged within 0.15 s: an onset where PANNs tags an effect class above its
    local baseline; a sharp rise; a high-band swell. The last two must not repeat with the beat
    and are not counted within SPEECH_GUARD_SEC of speech, because word onsets after a pause and
    fricatives look the same."""
    import librosa

    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    n = min(len(env), len(db), len(fw), len(speech))
    env = env[:n]
    if n < 10 or env.max() <= 0:
        return []
    med = np.median(env)
    mad = np.median(np.abs(env - med)) + 1e-9
    peaks = librosa.util.peak_pick(env, pre_max=3, post_max=3, pre_avg=10, post_avg=10,
                                   delta=float(4 * mad), wait=8)
    sfx_probs = fw[:n, panns.sfx_idx] if panns.sfx_idx else np.zeros((n, 0))
    sfx_base = median_smooth(sfx_probs, (int(4 * FPS), 1)) if sfx_probs.shape[1] else sfx_probs
    guard = int(SPEECH_GUARD_SEC * FPS)
    near_speech = np.convolve(speech[:n].astype(float), np.ones(2 * guard + 1), "same") > 0
    ddb = np.diff(db[:n], prepend=db[0])

    def tag(p: int) -> tuple[float, str | None, int]:
        if not sfx_probs.shape[1]:
            return 0.0, None, p
        wa, wb = max(0, p - 10), min(n, p + 40)
        lifts = sfx_probs[wa:wb] - sfx_base[wa:wb]
        inner = lifts.argmax(0)
        lifts_max = np.where((inner > 0) & (inner < len(lifts) - 1), lifts.max(0), 0.0)
        j = int(np.argmax(lifts_max))
        return float(lifts_max[j]), panns.labels[panns.sfx_idx[j]], wa + int(inner[j])

    def aligned(t: float) -> bool:
        return bool(bpm and len(beats) and np.min(np.abs(beats - t)) <= BEAT_ALIGN_SEC)

    period = 60.0 * FPS / bpm if bpm else None
    hb = high_band_db(y)[:n]
    mel = mel_db(y)[:, :n] if period else None

    cands = []
    for p in peaks:
        a, b = max(0, p - 3), min(n, p + 7)
        q = a + int(np.argmax(ddb[a:b]))
        t = q / FPS
        rise = float(db[q : min(n, q + 5)].max() - db[max(0, q - 10) : q + 1].min())
        lift, label, peak = tag(q)
        al, sp, rep = aligned(t), bool(near_speech[q]), repeats(mel, q, period)
        by_tag = lift >= SFX_TAG_LIFT and rise >= 6
        by_rise = rise >= 12 and not sp and not rep
        if not (by_tag or by_rise):
            continue
        score = max(min(1.0, 0.5 + lift) if by_tag else 0.0, min(1.0, 0.4 + rise / 40) if by_rise else 0.0)
        cands.append({"t": round(t, 2), "kind": "transient", "riseDb": round(rise, 1),
                      "label": label if lift >= 0.05 else None, "tagLift": round(lift, 3),
                      "beatAligned": al, "repeatsWithBeat": rep, "nearSpeech": sp, "confidence": round(score, 2),
                      "_tagOnly": not by_rise, "_peak": (label, peak)})
    claimed: dict = {}
    for c in cands:
        if c["_tagOnly"]:
            label, peak = c["_peak"]
            key = next((k for k in claimed if k[0] == label and abs(k[1] - peak) <= int(SED_RESOLUTION_SEC * FPS)), (label, peak))
            if key not in claimed or c["riseDb"] > claimed[key]["riseDb"]:
                claimed[key] = c
    cands = [c for c in cands if not c["_tagOnly"] or c in claimed.values()]
    for c in cands:
        c.pop("_tagOnly")
        c.pop("_peak")
    for a, e, ex in swells(hb):
        t = a / FPS
        if near_speech[a:e].any() or repeats(mel, a, period, span=max(4, e - a)):
            continue
        lift, label, _ = tag(a)
        cands.append({"t": round(t, 2), "kind": "swell", "riseDb": round(ex, 1), "durSec": round((e - a) / FPS, 2),
                      "label": label if lift >= 0.05 else None, "tagLift": round(lift, 3),
                      "beatAligned": aligned(t), "repeatsWithBeat": False, "nearSpeech": False,
                      "confidence": round(min(1.0, 0.6 + (ex - SWELL_DB) / 20), 2)})
    cands.sort(key=lambda c: c["t"])
    out: list[dict] = []
    for c in cands:
        if out and c["t"] - out[-1]["t"] <= 0.15:
            if c["confidence"] > out[-1]["confidence"]:
                out[-1] = c
            continue
        out.append(c)
    return out


def analyse(path: Path, work: Path, beats_file: Path | None, mode: str, cache: Path) -> dict:
    import librosa

    y = decode(path, SR)
    dur = len(y) / SR
    beats_tl = load_beats(beats_file) if beats_file else None
    log(f"decoded {path.name}: {dur:.2f} s")
    panns = Panns(cache)

    voice_y, bed_y = y, y
    if mode == "music":
        log("separating with htdemucs")
        voice_y, bed_y = separate(path, work, cache)
        n = min(len(y), len(voice_y), len(bed_y))
        y, voice_y, bed_y = y[:n], voice_y[:n], bed_y[:n]

    fw_mix = panns.framewise(y)
    n = len(fw_mix)
    db_mix = frame_db(y)[:n]
    db_voice = frame_db(voice_y)[:n] if mode == "music" else db_mix
    db_bed = frame_db(bed_y)[:n] if mode == "music" else None

    speech, pause_info = detect_speech(fw_mix, db_mix, panns)
    if mode == "music" and pause_info["thresholdDb"] is None:
        speech, pause_info = detect_speech(panns.framewise(voice_y), db_voice, panns, gate_db=35.0)
        pause_info["source"] = "vocals stem"
    else:
        pause_info["source"] = "mix"
    speech_segs = segs_from_mask(speech)
    for s in speech_segs:
        a, b = int(s["tStart"] * FPS), int(s["tEnd"] * FPS)
        s["levelDb"] = round(mean_db(db_voice[a:b]), 1)
    pause_segs = []
    if speech.any():
        first, last = np.where(speech)[0][[0, -1]]
        inner = ~speech
        inner[:first] = False
        inner[last + 1 :] = False
        pause_segs = [p for p in segs_from_mask(clean_mask(inner, int(PAUSE_MIN_SEC * FPS), 0))]

    edge = int(0.05 * FPS)
    nonspeech = ~speech
    nonspeech[:edge] = False
    nonspeech[max(0, n - edge) :] = False

    mix_bed = bed_evidence(y, db_mix, nonspeech, panns)
    direct_music = (median_smooth(fw_mix[:, panns.music_idx].max(1), int(1.0 * FPS)) >= 0.3) & nonspeech
    present = mix_bed["present"] or bool(direct_music.sum() >= FPS)

    separation = None
    use_stems = False
    if mode == "music":
        all_frames = np.ones(n, bool)
        all_frames[:edge] = False
        all_frames[max(0, n - edge) :] = False
        stem_bed = bed_evidence(bed_y, db_bed, all_frames, panns)
        retention = None
        if nonspeech.sum() >= int(0.2 * FPS):
            retention = mean_db(db_bed[nonspeech]) - mean_db(db_mix[nonspeech])
        use_stems = retention is not None and retention >= MIN_RETENTION_DB
        separation = {"model": "htdemucs", "bedRetentionDb": r(retention),
                      "trusted": use_stems, "stemMusicLikeProb": r(stem_bed["musicLike"], 3)}
        if not use_stems:
            separation["note"] = ("the accompaniment stem lost the bed in speech pauses; "
                                  "BGM level, ducking and tempo fall back to the mix")
        present = present or (use_stems and stem_bed["present"])

    bed_db_frames = db_bed if use_stems else db_mix
    bed_mask = all_frames if use_stems else nonspeech
    bed = stem_bed if use_stems else mix_bed
    bed_level = bed["level"]

    bed_frames = bed_mask & (bed_db_frames > max(BED_FLOOR_DBFS, (bed_level or 0) - 12)) if present else np.zeros(n, bool)
    enters, enters_bound, exits = None, None, None
    music_segs = []
    if present and bed_frames.any():
        idx = np.where(bed_frames)[0]
        first_bed, last_bed = idx[0], idx[-1]
        first_speech = np.where(speech)[0][0] if speech.any() else n
        if first_bed <= edge + 1:
            enters, enters_bound = 0.0, "exact"
        elif use_stems or first_bed < first_speech:
            enters, enters_bound = round(first_bed / FPS, 2), "exact"
        else:
            enters, enters_bound = round(first_bed / FPS, 2), "upper"
        exits = round(min(dur, (last_bed + 1) / FPS) if last_bed < n - edge - 1 else dur, 2)
        span = np.zeros(n, bool)
        span[first_bed : last_bed + 1] = True
        for s, e in runs(bed_mask & ~bed_frames & span):
            if e - s >= FPS:
                span[s:e] = False
        if first_bed <= edge + 1:
            span[:first_bed] = True
        if last_bed >= n - edge - 1:
            span[last_bed:] = True
        music_segs = segs_from_mask(span)
        for s in music_segs:
            a, b = int(s["tStart"] * FPS), int(s["tEnd"] * FPS)
            sel = bed_mask[a:b]
            s["levelDb"] = round(mean_db(bed_db_frames[a:b][sel]), 1) if sel.any() else None

    level_rel, level_basis, duck, duck_db = None, None, None, None
    if present and speech.any():
        if use_stems:
            b = mean_db(db_bed[speech])
            level_rel = b - mean_db(db_voice[speech])
            level_basis = "htdemucs stems, RMS over speech frames"
            far = np.convolve(speech.astype(float), np.ones(int(0.5 * FPS)), "same") == 0
            gaps = bed_mask & far
            if gaps.sum() >= int(0.5 * FPS):
                duck_db = mean_db(db_bed[gaps]) - b
        elif bed_level is not None:
            ps = power(mean_db(db_mix[speech]))
            pb = power(bed_level)
            if ps > 1.5 * pb:
                level_rel = float(10 * np.log10(pb / (ps - pb)))
                level_basis = ("mix: BGM from the speech pauses, voice = speech frames minus that power. "
                               "Biased when the BGM swells or dips with the voice")
            long_gap = np.zeros(n, bool)
            short_gap = np.zeros(n, bool)
            for s, e in runs(nonspeech):
                (long_gap if e - s >= FPS else short_gap)[s:e] = True
            if long_gap.sum() >= FPS and short_gap.sum() >= int(0.3 * FPS):
                duck_db = mean_db(db_mix[long_gap]) - mean_db(db_mix[short_gap])
        if duck_db is not None:
            duck = True if duck_db >= DUCK_DB else (False if abs(duck_db) <= NO_DUCK_DB else None)

    tempo = {"bpm": None, "confidence": 0.0, "candidates": [], "beatsPerBar": None,
             "octaveRule": "no BGM", "source": None, "beatCount": 0, "ibiCv": None}
    beat_times = np.zeros(0)
    if present:
        tempo_src = bed_y if use_stems else y
        beat_times, downbeats = run_beat_this(tempo_src, SR, cache)
        env = librosa.onset.onset_strength(y=tempo_src, sr=SR, hop_length=HOP)[:n]
        if not use_stems and speech.any() and nonspeech[: len(env)].sum() > 4 * FPS:
            env = env[nonspeech[: len(env)]]
        tempo = choose_tempo(beat_times, downbeats, env, FPS, "beat_this final0")
        if not use_stems and tempo["bpm"] is not None and speech.mean() > 0.3:
            on_beat_speech = np.mean([speech[min(int(t * FPS), n - 1)] for t in beat_times])
            if on_beat_speech > 0.8:
                tempo.update(bpm=None, confidence=0.0,
                             octaveRule="beats fall inside speech: likely syllables, no tempo")

    sfx = detect_sfx(y, fw_mix, panns, db_mix, speech, beat_times, tempo["bpm"])

    return build_output(path, dur, mode, beats_tl, speech_segs, pause_segs, pause_info, present, enters,
                        enters_bound, exits, music_segs, bed, level_rel, level_basis, use_stems,
                        separation, duck, duck_db, tempo, beat_times, sfx, y)


def bed_evidence(audio: np.ndarray, db: np.ndarray, mask: np.ndarray, panns: "Panns") -> dict:
    """Level of what sounds under the masked frames, and whether PANNs hears music in it once those
    frames are stitched together and normalised (short pauses alone are too short to tag)."""
    vals = db[mask]
    level = None
    if vals.size >= int(0.2 * FPS):
        lo, hi = np.percentile(vals, [20, 80])
        core = vals[(vals >= lo) & (vals <= hi)]
        level = mean_db(core if core.size else vals)
    stitched = stitch(audio, mask & (db > BED_FLOOR_DBFS))
    sec = len(stitched) / SR
    music_like = None
    if sec >= 0.8:
        fw = panns.framewise(normalise(stitched))
        music_like = float(np.mean(fw[:, panns.music_idx].max(1)))
    present = bool(level is not None and level > BED_FLOOR_DBFS and music_like is not None
                   and music_like >= MUSIC_LIKE_MIN)
    return {"level": level, "musicLike": music_like, "sec": sec, "present": present}


def r(v, k=1):
    return None if v is None else round(float(v), k)


def build_output(path, dur, mode, beats_tl, speech_segs, pause_segs, pause_info, present, enters,
                 enters_bound, exits, music_segs, bed, level_rel, level_basis, use_stems, separation,
                 duck, duck_db, tempo, beat_times, sfx, y) -> dict:
    speech_present = bool(speech_segs)
    measured, inferred, unmeasured = [], [], []

    bgm = {"present": present}
    measured.append("audio.bgm.present")
    if present:
        if tempo["bpm"] is not None:
            bgm["character"] = f"約 {tempo['bpm']:.0f} BPM。気分は聞いて書く"
        else:
            bgm["character"] = "拍が取れない持続音の床。気分は聞いて書く"
        inferred.append("audio.bgm.character")
        if enters is None:
            enters, enters_bound = 0.0, "unknown"
        at = to_at(enters, beats_tl)
        if at is None:
            at = {"beat": "b1", "offsetSec": round(enters, 2)}
            inferred.append("audio.bgm.entersAt")
        else:
            (measured if enters_bound == "exact" else inferred).append("audio.bgm.entersAt")
        bgm["entersAt"] = at
        if speech_present:
            bgm["duckUnderVoice"] = duck
            (measured if duck is not None else unmeasured).append("audio.bgm.duckUnderVoice")
            bgm["levelDbUnderVoice"] = r(level_rel)
            if level_rel is None:
                unmeasured.append("audio.bgm.levelDbUnderVoice")
            else:
                (measured if use_stems else inferred).append("audio.bgm.levelDbUnderVoice")

    kept = [s for s in sfx if s["confidence"] >= 0.6]
    pb_sfx = []
    for i, s in enumerate(kept):
        item = {"cue": "other", "type": sfx_type(s["label"]) if s["label"] else "transient"}
        at = to_at(s["t"], beats_tl)
        if at is not None:
            item["at"] = at
            measured.append(f"audio.sfx[{i}].at")
        inferred += [f"audio.sfx[{i}].cue", f"audio.sfx[{i}].type"]
        pb_sfx.append(item)
    if not pb_sfx:
        measured.append("audio.sfx")

    audio = {"bgm": bgm, "sfx": pb_sfx, "referenceAudioUsed": False}
    if not speech_present:
        audio["voice"] = "none"
        inferred.append("audio.voice")

    peak = float(np.max(np.abs(y))) if y.size else 0.0
    return {
        "tool": "audio_events",
        "version": 1,
        "measuredAt": datetime.date.today().isoformat(),
        "input": {"name": path.name, "sha256": sha256(path), "durationSec": round(dur, 3), "sampleRate": SR},
        "stage": "mix" if mode == "none" else "separated-htdemucs",
        "separation": separation,
        "speech": {
            "present": speech_present,
            "coverage": round(sum(s["tEnd"] - s["tStart"] for s in speech_segs) / dur, 3) if dur else 0.0,
            "segments": speech_segs,
            "pauses": pause_segs,
            "pauseDetection": pause_info,
        },
        "music": {
            "present": present,
            "entersAtSec": enters,
            "entersAtBound": enters_bound,
            "exitsAtSec": exits,
            "segments": music_segs,
            "bedLevelDbfs": r(bed["level"]),
            "musicLikeProb": r(bed["musicLike"], 3),
            "bedAudioSec": round(bed["sec"], 2),
            "levelDbUnderVoice": r(level_rel),
            "levelBasis": level_basis,
            "duckUnderVoice": duck,
            "duckDb": r(duck_db),
            "tempo": tempo,
            "beatTimes": [round(float(t), 2) for t in beat_times] if tempo["bpm"] is not None else [],
        },
        "sfx": sfx,
        "loudness": {"peakDbfs": r(20 * np.log10(peak + 1e-12)),
                     "rmsDbfs": r(10 * np.log10(np.mean(y.astype(np.float64) ** 2) + 1e-12))},
        "beatsFile": bool(beats_tl),
        "models": [
            {"name": "PANNs Cnn14_DecisionLevelMax", "weightsLicense": "CC-BY-4.0", "codeLicense": "MIT"},
            {"name": "beat_this final0", "weightsLicense": "MIT", "codeLicense": "MIT"},
        ] + ([{"name": "Demucs htdemucs", "weightsLicense": "MIT", "codeLicense": "MIT"}] if mode == "music" else []),
        "playbook": {"audio": audio},
        "evidence": {"measured": measured, "inferred": inferred, "unmeasured": unmeasured},
        "notes": [
            "playbook.audio is a fragment to merge. audio.voice is the recipe's voice and is set here only when the reference has no speech.",
            "Without --beats, audio.bgm.entersAt is keyed to b1 as if b1 starts at 0 s, and sfx carry no at.",
            "duckUnderVoice and levelDbUnderVoice are left out when the reference has no speech; every BGM field but present is left out when there is no BGM.",
            "audio.sfx[].cue is 'other' until the hit times are matched against cuts, cards and zooms.",
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("input", help="audio or video file")
    ap.add_argument("work_dir")
    ap.add_argument("--beats", help="playbook .md or beats JSON with {id, tIn, tOut}")
    ap.add_argument("--separate", choices=["none", "music"], default="none")
    ap.add_argument("--cache", help="model cache directory (default $SASARU_CACHE or $XDG_CACHE_HOME/sasaru)")
    ap.add_argument("--json", action="store_true", help="also print the result to stdout")
    a = ap.parse_args(argv)
    src = Path(a.input)
    if not src.is_file():
        log(f"not a file: {src}")
        return 2
    work = Path(a.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    try:
        out = analyse(src, work, Path(a.beats) if a.beats else None, a.separate, cache_dir(a.cache))
    except InputError as exc:
        log(str(exc))
        return 2
    text = json.dumps(out, ensure_ascii=False, indent=2)
    (work / "audio.json").write_text(text + "\n", encoding="utf-8")
    log(f"wrote {work / 'audio.json'}")
    if a.json:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
