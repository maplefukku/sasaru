# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "faster-whisper>=1.0,<2",
#   "numpy>=1.26,<3",
# ]
# ///
"""Word-timestamped transcript with faster-whisper, run locally on CPU.

Usage:
  uv run --script transcribe.py <audio_or_video> <out.json> [--model large-v3-turbo]
      [--language auto|ja|en|...] [--vad] [--vocals <stem.wav>] [--speech <audio.json>] [--threads 1] [--json]

The input is decoded with ffmpeg to 16 kHz mono, so mp4 works. --vocals transcribes that stem instead.
--speech keeps only segments that overlap the speech intervals in audio_events.py's audio.json;
under BGM-only stretches whisper invents words.

With --language auto, a decode whose mean avg_logprob is below -1.0 is redone with the detected language
pinned, and the better one is kept. "reliable" is true only when the kept decode's mean avg_logprob is at
least -1.0 and its median word probability at least 0.8 (a sine tone decodes to "Thank you." at -0.97 and 0.55).

Decoding is deterministic with the defaults: temperature 0 (no sampling fallback) and one CPU thread.
With --threads above 1, CTranslate2 changes word probabilities from run to run.

The model is fetched once from Hugging Face into $SASARU_CACHE/whisper
(default $XDG_CACHE_HOME/sasaru/whisper; large-v3-turbo is about 1.6 GB). The audio never leaves the machine.
The transcript is the reference's wording: keep it under work/, never in a playbook.
Exit codes: 0 ok, 2 bad input.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

LOW_LOGPROB = -1.0
MIN_WORD_PROB = 0.8


def log(*a):
    print(*a, file=sys.stderr)


def cache_dir():
    base = os.environ.get("SASARU_CACHE") or os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "sasaru")
    return os.path.join(base, "whisper")


def decode(path):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def speech_intervals(path):
    j = json.loads(Path(path).read_text())
    out = []
    for s in j.get("speech") or []:
        if isinstance(s, dict):
            out.append((float(s["tIn"]), float(s["tOut"])))
        else:
            out.append((float(s[0]), float(s[1])))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--language", default="auto")
    ap.add_argument("--vad", action="store_true", help="use faster-whisper's built-in VAD filter")
    ap.add_argument("--vocals", help="transcribe this separated vocal stem instead of src")
    ap.add_argument("--speech", help="audio.json from audio_events.py; drop segments outside its speech intervals")
    ap.add_argument("--beam-size", type=int, default=5)
    ap.add_argument("--threads", type=int, default=1, help="CPU threads; more than 1 is faster but word probabilities vary run to run")
    ap.add_argument("--json", action="store_true", help="also print the result to stdout")
    a = ap.parse_args()

    src = Path(a.vocals or a.src)
    if not src.is_file():
        log(f"no such file: {src}")
        return 2
    if shutil.which("ffmpeg") is None:
        log("ffmpeg not on PATH")
        return 2
    try:
        audio = decode(src)
    except subprocess.CalledProcessError:
        log(f"ffmpeg could not decode audio from {src}")
        return 2
    if audio.size == 0:
        log("no audio samples")
        return 2

    from faster_whisper import WhisperModel

    m = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=a.threads, download_root=cache_dir())

    def once(lang):
        segs, info = m.transcribe(audio, language=lang, word_timestamps=True, vad_filter=a.vad,
                                  beam_size=a.beam_size, temperature=0.0)
        segs = list(segs)
        lp = float(np.mean([s.avg_logprob for s in segs])) if segs else None
        return segs, info, lp

    segs, info, lp = once(None if a.language == "auto" else a.language)
    retried = False
    # On short clips auto-detection can pick the right language and still decode garbage; pinning it fixes that.
    if a.language == "auto" and lp is not None and lp < LOW_LOGPROB:
        segs2, info2, lp2 = once(info.language)
        retried = True
        if lp2 is not None and lp2 > lp:
            segs, info, lp = segs2, info2, lp2
    keep = speech_intervals(a.speech) if a.speech else None
    probs = [w.probability for s in segs for w in (s.words or [])]
    wp = float(np.median(probs)) if probs else None

    out = {
        "model": a.model,
        "language": info.language,
        "languageProb": round(float(info.language_probability), 3),
        "languageArg": a.language,
        "retriedWithDetectedLanguage": retried,
        "meanAvgLogprob": None if lp is None else round(lp, 3),
        "medianWordProb": None if wp is None else round(wp, 3),
        "reliable": lp is not None and lp >= LOW_LOGPROB and wp is not None and wp >= MIN_WORD_PROB,
        "input": str(src),
        "vad": a.vad,
        "speechFilter": a.speech,
        "segments": [],
        "dropped": 0,
    }
    for s in segs:
        if keep is not None and not any(s.start < b and s.end > t for t, b in keep):
            out["dropped"] += 1
            continue
        out["segments"].append({
            "start": round(s.start, 2),
            "end": round(s.end, 2),
            "text": s.text.strip(),
            "noSpeechProb": round(float(s.no_speech_prob), 3),
            "avgLogprob": round(float(s.avg_logprob), 3),
            "words": [{"w": w.word, "s": round(w.start, 2), "e": round(w.end, 2), "p": round(float(w.probability), 3)}
                      for w in (s.words or [])],
        })
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    words = sum(len(s["words"]) for s in out["segments"])
    log(f"{src}: lang={out['language']} segments={len(out['segments'])} words={words} dropped={out['dropped']}")
    if a.json:
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
