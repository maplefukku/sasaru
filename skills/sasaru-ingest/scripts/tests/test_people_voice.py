# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "numpy==1.26.4",
#   "jsonschema==4.24.0",
#   "pytest==8.4.1",
# ]
# [tool.uv]
# exclude-newer = "2026-10-25T00:00:00Z"
# ///
"""Tests for people_voice.py. Run: uv run skills/sasaru-ingest/scripts/tests/test_people_voice.py

The end-to-end test fetches the MediaPipe models and runs the script on a synthetic clip without a
face. It is skipped unless SASARU_SLOW=1.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
REPO = HERE.parents[3]

import people_voice as pv  # noqa: E402

FPS = 30.0


def speech_like(n: int, seed: int) -> np.ndarray:
    """A syllable-rate envelope with pauses, the shape a voice track has."""
    rng = np.random.default_rng(seed)
    env = np.zeros(n)
    i = 0
    while i < n:
        talk = int(rng.uniform(0.6, 1.5) * FPS)
        t = np.arange(talk) / FPS
        env[i : i + talk] = (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(3, 6) * t + rng.uniform(0, 6))) [: n - i]
        i += talk + int(rng.uniform(0.2, 0.5) * FPS)
    return env


def test_mouth_that_follows_the_voice_beats_the_shifted_null():
    env = speech_like(600, 0)
    rng = np.random.default_rng(1)
    opening = 0.03 + 0.03 * np.roll(env, 2) + rng.normal(0, 0.01, len(env))
    out = pv.sync_score(opening, env, np.ones(len(env), bool), FPS)
    assert out["r"] >= 0.5
    assert out["p"] < 0.05
    assert out["bestLagMs"] == pytest.approx(67, abs=34)


def test_mouth_moving_to_other_speech_does_not():
    env = speech_like(600, 0)
    rng = np.random.default_rng(2)
    opening = 0.03 + 0.03 * speech_like(600, 7) + rng.normal(0, 0.01, 600)
    out = pv.sync_score(opening, env, np.ones(600, bool), FPS)
    assert out["p"] >= 0.05


def test_decide_cases():
    good = {"r": 0.4, "p": 0.01, "bestLagMs": -33, "nullMean": 0.1}
    weak = {"r": 0.25, "p": 0.3, "bestLagMs": 200, "nullMean": 0.2}
    assert pv.decide(0.0, 0.0, None, None, 1.0, None, None)[:2] == ("none", "face")
    assert pv.decide(5.0, 0.6, 1.0, good, 1.0, None, None)[:2] == ("on-camera", "face")
    assert pv.decide(5.0, 0.6, 1.0, weak, 1.0, None, None)[:2] == ("voiceover", "face")
    assert pv.decide(5.0, 0.6, 0.1, good, 0.1, 0.0, 0.0)[:2] == ("voiceover", "none")
    assert pv.decide(5.0, 0.6, 0.0, None, 0.0, 0.5, 0.0)[:2] == ("voiceover", "hands")
    assert pv.decide(5.0, 0.6, 0.0, None, 0.0, 0.0, 0.6)[:2] == ("voiceover", "body-no-face")


def test_speech_mask_and_band_envelope():
    times = np.arange(0, 2, 0.1)
    m = pv.speech_mask(times, [{"tStart": 0.5, "tEnd": 1.0}])
    assert m.sum() == 5 and m[5] and not m[10]
    sr = pv.AUDIO_SR
    t = np.arange(2 * sr) / sr
    y = np.where(t < 1, np.sin(2 * np.pi * 1000 * t), np.sin(2 * np.pi * 60 * t)).astype(np.float32)
    env = pv.band_envelope(y, np.array([0.5, 1.5]), 0.066)
    assert env[0] > 100 * env[1]


def reference_subschema() -> dict:
    schema = json.loads((REPO / "schema" / "playbook.schema.json").read_text())
    sub = dict(schema["properties"]["source"]["properties"]["reference"])
    sub["$defs"] = schema.get("$defs", {})
    return sub


@pytest.mark.skipif(os.environ.get("SASARU_SLOW") != "1", reason="set SASARU_SLOW=1 to run the models")
def test_end_to_end_without_a_face(tmp_path):
    import jsonschema

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    clip = tmp_path / "noface.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=360x640:r=30:d=6",
                    "-f", "lavfi", "-i", "sine=f=220:d=6", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", str(clip)], check=True)
    events = tmp_path / "audio.json"
    events.write_text(json.dumps({"tool": "audio_events", "stage": "mix",
                                  "speech": {"segments": [{"tStart": 0.5, "tEnd": 5.5}]}}))
    work = tmp_path / "work"
    p = subprocess.run(["uv", "run", "-q", "--script", str(HERE.parent / "people_voice.py"), str(clip), str(work),
                        "--audio-events", str(events), "--json"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["face"]["ratio"] == 0.0
    assert out["decision"]["speech"] == "voiceover"
    assert out["decision"]["onCamera"] == "none"
    ref = dict(out["playbook"]["source"]["reference"], hardCuts=None)
    jsonschema.Draft202012Validator(reference_subschema()).validate(ref)
    assert isinstance(out["measuredAt"], str)


def test_bad_input_exits_2(tmp_path):
    assert pv.main([str(tmp_path / "missing.mp4"), str(tmp_path / "w")]) == 2


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", *sys.argv[1:]]))
