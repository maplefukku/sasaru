# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "numpy==2.2.6",
#   "scipy==1.15.3",
#   "soundfile==0.13.1",
#   "librosa==0.11.0",
#   "pyyaml==6.0.2",
#   "jsonschema==4.24.0",
#   "pytest==8.4.1",
# ]
# [tool.uv]
# exclude-newer = "2026-10-25T00:00:00Z"
# ///
"""Tests for audio_events.py. Run: uv run skills/sasaru-ingest/tests/test_audio_events.py

The end-to-end test downloads the models and runs the script on synthetic audio. It is skipped
unless SASARU_SLOW=1.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
REPO = HERE.parents[2]

import audio_events as ae  # noqa: E402

SR = ae.SR


def beats_at(bpm: float, dur: float) -> np.ndarray:
    return np.arange(0, dur, 60 / bpm)


def onset_env(bpm: float, dur: float, fps: int = ae.FPS) -> np.ndarray:
    env = np.zeros(int(dur * fps))
    for t in beats_at(bpm, dur):
        i = int(t * fps)
        if i < len(env):
            env[i] = 1.0
    return env


def test_tempo_halves_when_downbeats_say_eight_beats_per_bar():
    beats = beats_at(172, 12)
    downbeats = beats[::8]
    out = ae.choose_tempo(beats, downbeats, onset_env(86, 12), ae.FPS, "test")
    assert out["bpm"] == pytest.approx(86, abs=1)
    assert "halved" in out["octaveRule"]
    assert {c["ratio"] for c in out["candidates"]} == {0.5, 1.0, 2.0}


def test_tempo_halves_fast_beats_when_half_tempo_is_as_periodic():
    beats = beats_at(172, 12)
    out = ae.choose_tempo(beats, np.array([]), onset_env(86, 12), ae.FPS, "test")
    assert out["bpm"] == pytest.approx(86, abs=1)


def test_tempo_keeps_a_real_quarter_note_tempo():
    beats = beats_at(86, 12)
    out = ae.choose_tempo(beats, beats[::4], onset_env(86, 12), ae.FPS, "test")
    assert out["bpm"] == pytest.approx(86, abs=1)
    assert out["octaveRule"] == "kept the beat tracker's level"


def test_tempo_refuses_irregular_or_few_beats():
    rng = np.random.default_rng(0)
    irregular = np.cumsum(rng.uniform(0.2, 1.2, 20))
    assert ae.choose_tempo(irregular, np.array([]), None, ae.FPS, "test")["bpm"] is None
    assert ae.choose_tempo(beats_at(100, 2), np.array([]), None, ae.FPS, "test")["bpm"] is None


def test_pauses_are_found_under_a_bgm_bed():
    fps = ae.FPS
    db = np.full(8 * fps, -20.0)
    for s in (1.0, 3.0, 5.5):
        db[int(s * fps) : int((s + 0.3) * fps)] = -40.0
    assert not (db < -40.5).any()
    region = np.ones(len(db), bool)
    pauses, info = ae.find_pauses(db, region)
    found = ae.segs_from_mask(pauses)
    assert len(found) == 3
    assert [round(p["tStart"], 1) for p in found] == [1.0, 3.0, 5.5]
    assert info["thresholdDb"] is not None


def test_no_pauses_when_the_level_barely_moves():
    db = np.full(4 * ae.FPS, -20.0)
    db[100:140] = -25.0
    pauses, info = ae.find_pauses(db, np.ones(len(db), bool))
    assert not pauses.any()
    assert info["thresholdDb"] is None


def test_to_at_keys_seconds_to_beats():
    beats = [{"id": "b1", "tIn": 0.0, "tOut": 1.5}, {"id": "b2", "tIn": 1.5, "tOut": 4.0}]
    assert ae.to_at(0.0, beats) == {"beat": "b1", "offsetSec": 0.0}
    assert ae.to_at(1.2, beats) == {"beat": "b1", "offsetSec": 1.2}
    assert ae.to_at(2.0, beats) == {"beat": "b2", "offsetSec": 0.5}
    assert ae.to_at(9.0, beats) == {"beat": "b2", "offsetSec": 7.5}
    assert ae.to_at(1.0, None) is None


def test_load_beats_reads_the_playbook_template_and_json(tmp_path):
    beats = ae.load_beats(REPO / "templates" / "playbook.md")
    assert beats[0]["id"] == "b1" and beats[0]["tIn"] == 0.0
    j = tmp_path / "beats.json"
    j.write_text(json.dumps({"beats": [{"id": "b2", "tIn": 1, "tOut": 2}, {"id": "b1", "tIn": 0, "tOut": 1}]}))
    assert [b["id"] for b in ae.load_beats(j)] == ["b1", "b2"]
    bad = tmp_path / "bad.json"
    bad.write_text("[]")
    with pytest.raises(ae.InputError):
        ae.load_beats(bad)


def test_swells_find_a_slow_whoosh_but_not_steady_hats():
    fps = ae.FPS
    hb = np.full(10 * fps, -50.0) + np.random.default_rng(1).normal(0, 1, 10 * fps)
    a = int(4.0 * fps)
    hb[a : a + 40] += 20 * np.sin(np.linspace(0, np.pi, 40)) ** 2
    found = ae.swells(hb)
    assert len(found) == 1
    assert abs(found[0][0] / fps - 4.0) < 0.15


def test_stitch_and_masks():
    y = np.ones(SR, np.float32)
    mask = np.zeros(ae.FPS, bool)
    mask[10:30] = True
    mask[50:52] = True
    out = ae.stitch(y, mask)
    assert len(out) == 20 * ae.HOP
    assert ae.clean_mask(np.array([1, 1, 0, 1, 1, 0, 0, 0, 1], bool), 2, 1).tolist() == [
        True, True, True, True, True, False, False, False, False]


def test_sfx_type_names():
    assert ae.sfx_type("Whoosh, swoosh, swish") == "whoosh"
    assert ae.sfx_type("Zipper (clothing)") == "zipper"
    assert ae.sfx_type("Beep, bleep") == "beep"


def audio_subschema() -> dict:
    schema = json.loads((REPO / "schema" / "playbook.schema.json").read_text())
    sub = dict(schema["properties"]["audio"])
    sub["$defs"] = schema.get("$defs", {})
    return sub


def fragment(present: bool, speech: bool, beats=None, sfx=()) -> dict:
    tempo = {"bpm": None}
    segs = [{"tStart": 0.5, "tEnd": 2.0, "levelDb": -20.0}] if speech else []
    bed = {"level": -40.0, "musicLike": 0.1, "sec": 1.0}
    return ae.build_output(Path(__file__), 4.0, "none", beats, segs, [], {}, present, 0.3 if present else None,
                           "exact", 4.0, [], bed, -20.0 if present and speech else None, None, False, None,
                           None, None, tempo, np.zeros(0), list(sfx), np.zeros(SR, np.float32))


@pytest.mark.parametrize("present,speech", [(True, True), (True, False), (False, True), (False, False)])
def test_fragment_follows_the_bgm_and_voice_rules(present, speech):
    import jsonschema

    out = fragment(present, speech)
    bgm = out["playbook"]["audio"]["bgm"]
    jsonschema.Draft202012Validator(audio_subschema()).validate(
        dict(out["playbook"]["audio"], voice=out["playbook"]["audio"].get("voice", "own-voiceover")))
    if not present:
        assert bgm == {"present": False}
    else:
        assert bgm["entersAt"] == {"beat": "b1", "offsetSec": 0.3}
        assert isinstance(bgm["character"], str)
        assert ("levelDbUnderVoice" in bgm) is speech and ("duckUnderVoice" in bgm) is speech
    assert ("voice" in out["playbook"]["audio"]) is (not speech)
    paths = sum(out["evidence"].values(), [])
    assert len(paths) == len(set(paths))
    assert all("[]" not in p for p in paths)


def test_fragment_keys_effects_to_beats_with_indexed_evidence_paths():
    hit = {"t": 2.5, "kind": "transient", "riseDb": 20.0, "label": "Whoosh, swoosh, swish", "tagLift": 0.3,
           "beatAligned": False, "repeatsWithBeat": False, "nearSpeech": False, "confidence": 0.9}
    beats = [{"id": "b1", "tIn": 0.0, "tOut": 2.0}, {"id": "b2", "tIn": 2.0, "tOut": 4.0}]
    out = fragment(True, False, beats, [hit])
    assert out["playbook"]["audio"]["sfx"] == [{"cue": "other", "type": "whoosh", "at": {"beat": "b2", "offsetSec": 0.5}}]
    assert "audio.sfx[0].at" in out["evidence"]["measured"]
    assert "audio.sfx[0].cue" in out["evidence"]["inferred"]


def synth_music(bpm: float, dur: float, hits: list[float]) -> np.ndarray:
    from scipy.signal import butter, lfilter

    rng = np.random.default_rng(0)
    y = np.zeros(int(dur * SR))

    def place(x, t):
        i = int(t * SR)
        m = min(len(x), len(y) - i)
        if m > 0:
            y[i : i + m] += x[:m]

    def decay(n, tau):
        return np.exp(-np.arange(n) / (tau * SR))

    n = int(0.25 * SR)
    f = 50 + 100 * np.exp(-np.arange(n) / SR * 30)
    kick = 0.9 * np.sin(2 * np.pi * np.cumsum(f) / SR) * decay(n, 0.08)
    beat = 60 / bpm
    for k, t in enumerate(np.arange(0, dur, beat)):
        place(kick, t)
        if k % 2:
            place(0.4 * rng.standard_normal(int(0.2 * SR)) * decay(int(0.2 * SR), 0.05), t)
        for q in range(4):
            h = np.diff(np.r_[0, rng.standard_normal(int(0.05 * SR))])
            place(0.12 * h * decay(len(h), 0.01), t + q * beat / 4)
    wn = int(0.45 * SR)
    noise = rng.standard_normal(wn)
    whoosh = np.zeros(wn)
    for i in range(0, wn, 640):
        fc = 500 + 6000 * i / wn
        b, a = butter(2, [fc * 0.7 / (SR / 2), min(0.99, fc * 1.3 / (SR / 2))], "band")
        whoosh[i : i + 640] = lfilter(b, a, noise[i : i + 640])
    whoosh *= 0.8 * np.sin(np.pi * np.arange(wn) / wn) ** 2 / np.abs(whoosh).max()
    t = np.arange(int(0.8 * SR)) / SR
    ding = 0.5 * (np.sin(2 * np.pi * 1760 * t) + 0.4 * np.sin(2 * np.pi * 3520 * t)) * decay(len(t), 0.25)
    t = np.arange(int(0.06 * SR)) / SR
    pop = 0.9 * np.sin(2 * np.pi * (900 - 8000 * t) * t) * decay(len(t), 0.012)
    for x, at in zip((whoosh, ding, pop), hits):
        place(x, at)
    return (0.5 * y / np.abs(y).max()).astype(np.float32)


@pytest.mark.skipif(os.environ.get("SASARU_SLOW") != "1", reason="set SASARU_SLOW=1 to run the models")
def test_end_to_end_on_synthetic_drums_with_effects(tmp_path):
    import jsonschema
    import soundfile as sf

    hits = [2.37, 5.13, 8.61]
    wav = tmp_path / "drums86.wav"
    sf.write(wav, synth_music(86, 12, hits), SR)
    beats = tmp_path / "beats.json"
    beats.write_text(json.dumps([{"id": "b1", "tIn": 0, "tOut": 4}, {"id": "b2", "tIn": 4, "tOut": 12}]))
    work = tmp_path / "work"
    p = subprocess.run(["uv", "run", "-q", "--script", str(SCRIPTS / "audio_events.py"), str(wav), str(work),
                        "--beats", str(beats), "--json"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out == json.loads((work / "audio.json").read_text())
    assert out["speech"]["present"] is False
    assert out["music"]["present"] is True
    assert out["music"]["tempo"]["bpm"] == pytest.approx(86, rel=0.03)
    found = [s["t"] for s in out["sfx"]]
    for h in hits:
        assert any(abs(t - h) <= 0.1 for t in found), (h, found)
    assert len(found) == len(hits)
    audio = out["playbook"]["audio"]
    assert audio["voice"] == "none"
    assert audio["bgm"]["entersAt"] == {"beat": "b1", "offsetSec": 0.0}
    assert all(s["cue"] == "other" and "at" in s for s in audio["sfx"])
    jsonschema.Draft202012Validator(audio_subschema()).validate(audio)
    assert isinstance(out["measuredAt"], str)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", *sys.argv[1:]]))
