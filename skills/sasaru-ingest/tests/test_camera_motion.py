#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "opencv-python-headless>=4.10,<6",
#   "numpy>=1.26,<3",
#   "pytest>=8,<10",
#   "jsonschema>=4.18,<5",
# ]
# ///
"""Tests for camera_motion.py on synthetic videos with known camera moves and transitions.

Run: uv run --script skills/sasaru-ingest/tests/test_camera_motion.py
Videos are generated into a temp directory and never written to the repository.
Set CAMERA_MOTION_KEEP=<dir> to keep the generated videos and camera.json files.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import camera_motion as cm  # noqa: E402

REPO = HERE.parents[2]
SCHEMA = REPO / "schema" / "playbook.schema.json"
FPS = 30
W, H = 540, 960
HAS_FFMPEG = shutil.which("ffmpeg") is not None


# ---------------------------------------------------------------- synthetic footage


def make_scene(seed: int, size=(2200, 1800)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    hh, ww = size
    base = cv2.resize(rng.random((hh // 150, ww // 150, 3)).astype(np.float32), (ww, hh), interpolation=cv2.INTER_CUBIC)
    img = (base * 160 + 40).astype(np.uint8)
    for _ in range(900):
        c = tuple(int(x) for x in rng.integers(0, 255, 3))
        x, y = int(rng.integers(0, ww)), int(rng.integers(0, hh))
        r = int(rng.integers(4, 40))
        if rng.random() < 0.5:
            cv2.circle(img, (x, y), r, c, -1, cv2.LINE_AA)
        else:
            cv2.rectangle(img, (x, y), (x + r, y + int(rng.integers(4, 40))), c, -1)
    noise = rng.normal(0, 10, img.shape).astype(np.float32)
    img = np.clip(img.astype(np.float32) + cv2.GaussianBlur(noise, (0, 0), 1.0), 0, 255).astype(np.uint8)
    return img


def view(scene: np.ndarray, cx: float, cy: float, zoom: float, rot: float = 0.0) -> np.ndarray:
    """Camera looking at scene point (cx, cy); zoom 1 shows W x H scene pixels."""
    M = cv2.getRotationMatrix2D((cx, cy), rot, zoom)
    M[0, 2] += W / 2 - cx
    M[1, 2] += H / 2 - cy
    return cv2.warpAffine(scene, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease_in(x):
    x = min(1.0, max(0.0, x))
    return x * x


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 2


CAPTIONS = ["THIS IS A HOOK", "ZOOM WORKS", "LOOK HERE", "BIG REVEAL", "WAIT FOR IT", "SECOND LINE", "THE END"]


def caption_scale(since: float, pop_frames: int) -> float:
    return 1.6 * min(1.0, 0.6 + 0.4 * since * FPS / pop_frames)


def draw_caption(img: np.ndarray, t: float, period: float = 0.7, pop_frames: int = 3) -> np.ndarray:
    """Screen-fixed white caption with a black outline; each card scales in over pop_frames."""
    k = int(t // period)
    text = CAPTIONS[k % len(CAPTIONS)]
    sc = caption_scale(t - k * period, pop_frames)
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, sc, 3)
    org = (int(W / 2 - tw / 2), int(0.45 * H + th / 2))
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_DUPLEX, sc, (0, 0, 0), 10, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_DUPLEX, sc, (255, 255, 255), 3, cv2.LINE_AA)
    return img


def write_video(path: Path, frames) -> None:
    if HAS_FFMPEG:
        p = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
             "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(path)],
            stdin=subprocess.PIPE,
        )
        for f in frames:
            p.stdin.write(np.ascontiguousarray(f).tobytes())
        p.stdin.close()
        assert p.wait() == 0
    else:
        vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
        for f in frames:
            vw.write(f)
        vw.release()


# Ground truth of the main synthetic reel. Times are in seconds.
TRUTH = {
    "zooms": [
        {"tStart": 1.0, "tEnd": 2.0, "scaleFrom": 1.0, "scaleTo": 1.3, "easing": "ease-in-out"},
        {"tStart": 5.0, "tEnd": 5.1, "scaleFrom": 1.0, "scaleTo": 1.2, "easing": "snap"},
        {"tStart": 6.5, "tEnd": 7.5, "scaleFrom": 1.25, "scaleTo": 1.0, "easing": "linear"},
    ],
    "pans": [{"kind": "pan", "tStart": 2.5, "tEnd": 3.5, "direction": "right"},
             {"kind": "tilt", "tStart": 8.4, "tEnd": 9.2, "direction": "down"}],
    "shake": [(4.0, 5.0)],
    "static": [(0.0, 1.0), (5.1, 6.0), (7.5, 8.0)],
    "transitions": [
        {"at": 4.0, "type": "hard-cut"},
        {"at": 6.25, "type": "fade"},
        {"at": 8.2, "type": "whip"},
        {"at": 9.75, "type": "zoom-cut"},
    ],
    "hardCuts": 2,
    "duration": 10.8,
}


def main_reel_frames(captions: bool = True):
    A, B, C = make_scene(1), make_scene(2), make_scene(3)
    rng = np.random.default_rng(7)
    jit = cv2.GaussianBlur(rng.normal(0, 1, (60, 3)).astype(np.float32), (1, 9), 2.0)
    jit -= jit.mean(0)
    jit *= np.array([4.0, 4.0, 0.3]) / (np.abs(jit).max(0) + 1e-6)
    ax, ay = 900.0, 1100.0
    n = int(TRUTH["duration"] * FPS)
    for i in range(n):
        t = i / FPS
        if t < 4.0:
            z = 1.0 + 0.3 * smoothstep(t - 1.0)
            x = ax + 0.3 * W * min(1.0, max(0.0, (t - 2.5) / 1.0))
            f = view(A, x, ay, z)
        elif t < 6.0:
            j = jit[min(59, i - 120)] if t < 5.0 else (0, 0, 0)
            z = 1.0 if t < 5.0 else 1.0 + 0.2 * min(1.0, (i - 150) / 3)
            f = view(B, 900 + j[0], 1000 + j[1], z, j[2])
        elif t < 6.5:
            a = (t - 6.0) / 0.5
            f = cv2.addWeighted(view(B, 900, 1000, 1.2), 1 - a, view(C, 900, 1000, 1.25), a, 0)
        elif t < 8.0:
            z = 1.25 - 0.25 * min(1.0, max(0.0, (t - 6.5) / 1.0))
            f = view(C, 900, 1000, z)
        elif t < 8.4:
            a = smoothstep((t - 8.0) / 0.4)
            off = int(round(a * W))
            c_img, a_img = view(C, 900, 1000, 1.0), view(A, ax, ay, 1.0)
            f = np.concatenate([c_img[:, off:], a_img[:, : off]], 1) if off else c_img
        elif t < 9.75:
            y = ay + 0.2 * H * min(1.0, max(0.0, (t - 8.4) / 0.8))
            z = 1.0 + 0.6 * ease_in((t - 9.5) / 0.25)
            f = view(A, ax, y, z)
        else:
            z = 1.6 - 0.6 * ease_out((t - 9.75) / 0.25)
            f = view(B, 700, 900, z)
        f = np.ascontiguousarray(f)
        yield draw_caption(f, t) if captions else f


SLOW_POP = 9


def caption_only_frames(seconds: float = 4.0, dark: bool = False):
    S = make_scene(11)
    base = view(S, 900, 1000, 1.0)
    if dark:
        base = (cv2.GaussianBlur(base, (0, 0), 12) * 0.3).astype(np.uint8)
    for i in range(int(seconds * FPS)):
        yield draw_caption(base.copy(), i / FPS, period=0.5, pop_frames=SLOW_POP if dark else 3)


def caption_track(seconds: float = 4.0, period: float = 0.5) -> dict:
    """captions.json in caption_boxes.py's shape, in pixels, drawn from the same layout as draw_caption."""
    frames = []
    for i in range(int(seconds * FPS)):
        t = i / FPS
        k = int(t // period)
        text = CAPTIONS[k % len(CAPTIONS)]
        sc = caption_scale(t - k * period, SLOW_POP)
        (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, sc, 3)
        cy = 0.45 * H + th / 2 - (th + base) / 2
        frames.append({"t": round(t, 4), "boxes": [{"cx": W / 2, "cy": cy, "w": tw + 10, "h": th + base + 10, "lines": 1}]})
    return {"frames": frames}


# ---------------------------------------------------------------- fixtures


@pytest.fixture(scope="session")
def workdir(tmp_path_factory):
    keep = os.environ.get("CAMERA_MOTION_KEEP")
    if keep:
        p = Path(keep)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return tmp_path_factory.mktemp("camera_motion")


def run_cm(video: Path, out: Path, *extra: str) -> dict:
    rc = cm.main([str(video), str(out), *extra])
    assert rc == 0
    return json.loads((out / "camera.json").read_text())


@pytest.fixture(scope="session")
def main_reel(workdir):
    video = workdir / "synthetic-main.mp4"
    if not video.exists():
        write_video(video, main_reel_frames())
    beats = workdir / "beats.json"
    beats.write_text(json.dumps([
        {"id": "b1", "tIn": 0.0, "tOut": 4.0}, {"id": "b2", "tIn": 4.0, "tOut": 6.25},
        {"id": "b3", "tIn": 6.25, "tOut": 8.2}, {"id": "b4", "tIn": 8.2, "tOut": 10.8},
    ]))
    return run_cm(video, workdir / "main", "--beats", str(beats)), beats


# ---------------------------------------------------------------- unit tests


def test_easing_shapes():
    t = np.linspace(0, 1, 31)
    assert cm.easing_of(t, t, 1.0) == "linear"
    assert cm.easing_of(t, t * t, 1.0) == "ease-in"
    assert cm.easing_of(t, 1 - (1 - t) ** 2, 1.0) == "ease-out"
    assert cm.easing_of(t, t * t * (3 - 2 * t), 1.0) == "ease-in-out"
    assert cm.easing_of(np.linspace(0, 0.1, 4), np.linspace(0, 1, 4), 0.1) == "snap"


def test_key_time_snaps_to_beat_start():
    beats = [{"id": "b1", "tIn": 0.0, "tOut": 2.0}, {"id": "b2", "tIn": 2.0, "tOut": 5.0}]
    assert cm.key_time(1.5, beats) == {"beat": "b1", "offsetSec": 1.5}
    assert cm.key_time(1.97, beats) == {"beat": "b2", "offsetSec": 0.0}
    assert cm.key_time(6.0, beats) == {"beat": "b2", "offsetSec": 4.0}


def test_auto_caption_boxes_find_the_caption_only():
    S = make_scene(5)
    f = draw_caption(view(S, 900, 1000, 1.0), 0.5)
    small = cv2.resize(f, (360, 640), interpolation=cv2.INTER_AREA)
    boxes = cm.detect_caption_boxes(small, 220)
    caption = [b for b in boxes if abs(b[1] + b[3] / 2 - 0.45) < 0.03 and b[2] > 0.4]
    assert caption, f"caption not found in {boxes}"
    assert sum(w * h for _, _, w, h in boxes) < 0.1, "masking more than a tenth of the frame"


def test_bad_input_exits_2(tmp_path):
    assert cm.main([str(tmp_path / "missing.mp4"), str(tmp_path)]) == 2
    assert cm.main(["--rekey", str(tmp_path / "camera.json")]) == 2


# ---------------------------------------------------------------- end to end


def near(a, b, tol):
    return abs(a - b) <= tol


def test_zoom_events_match_truth(main_reel):
    res, _ = main_reel
    got = [z for z in res["zoomEvents"] if not z["transition"]]
    assert len(got) == len(TRUTH["zooms"]), got
    for g, t in zip(got, TRUTH["zooms"]):
        tol = 0.07 if t["easing"] == "snap" else 0.15
        assert near(g["tStart"], t["tStart"], tol), (g, t)
        assert near(g["tEnd"], t["tEnd"], tol), (g, t)
        assert near(g["scaleTo"] / g["scaleFrom"], t["scaleTo"] / t["scaleFrom"], 0.03), (g, t)
        assert near(g["scaleFrom"], t["scaleFrom"], 0.04), (g, t)
        assert g["easing"] == t["easing"], (g, t)


def test_pan_tilt_shake_static_segments(main_reel):
    res, _ = main_reel
    segs = res["segments"]

    def kind_at(t):
        return next((s for s in segs if s["tStart"] <= t < s["tEnd"]), None)

    for p in TRUTH["pans"]:
        mid = kind_at(0.5 * (p["tStart"] + p["tEnd"]))
        assert mid and mid["kind"] == p["kind"] and mid["direction"] == p["direction"], (p, mid)
        assert near(mid["tStart"], p["tStart"], 0.2) and near(mid["tEnd"], p["tEnd"], 0.2), (p, mid)
    for a, b in TRUTH["shake"]:
        s = kind_at(0.5 * (a + b))
        assert s and s["kind"] == "shake", s
    for a, b in TRUTH["static"]:
        s = kind_at(0.5 * (a + b))
        assert s and s["kind"] == "static", (a, b, s)


def test_transitions_match_truth(main_reel):
    res, _ = main_reel
    got = [tr for tr in res["transitions"] if tr["confidence"] in ("high", "medium")]
    assert len(got) == len(TRUTH["transitions"]), got
    for g, t in zip(got, TRUTH["transitions"]):
        assert near(g["atSec"], t["at"], 0.12), (g, t)
        assert g["type"] == t["type"], (g, t)
    assert res["hardCuts"] == TRUTH["hardCuts"]


def test_playbook_block_validates_against_schema(main_reel):
    jsonschema = pytest.importorskip("jsonschema")
    if not SCHEMA.exists():
        pytest.skip("schema not found")
    res, _ = main_reel
    schema = json.loads(SCHEMA.read_text())
    sub = {"$schema": schema["$schema"], "$defs": schema.get("$defs", {}), **schema["properties"]["camera"]}
    jsonschema.Draft202012Validator(sub).validate(res["playbook"]["camera"])
    hc = schema["properties"]["source"]["properties"]["reference"]["properties"]["hardCuts"]
    jsonschema.Draft202012Validator(hc).validate(res["playbook"]["source.reference.hardCuts"])
    moves: dict[str, list[str]] = {}
    for m in res["playbook"]["camera"]["moves"]:
        moves.setdefault(m["beat"], []).append(m["move"])
    assert moves["b1"] == ["push-in", "pan"]
    assert moves["b2"] == ["handheld"]
    assert moves["b3"] == ["pull-out"]
    assert moves["b4"] == ["tilt"]
    assert res["playbook"]["camera"]["transitions"][0]["at"] == {"beat": "b2", "offsetSec": 0.0}


def test_rekey_rebuilds_block(main_reel, workdir):
    _, _ = main_reel
    beats = workdir / "beats2.json"
    beats.write_text(json.dumps({"beats": [{"id": "b1", "tIn": 0, "tOut": 5.5}, {"id": "b2", "tIn": 5.5, "tOut": 10.8}]}))
    cam = workdir / "main" / "camera.json"
    assert cm.main(["--rekey", str(cam), "--beats", str(beats)]) == 0
    res = json.loads(cam.read_text())
    assert [b["id"] for b in res["playbook"]["beats"]] == ["b1", "b2"]
    assert all(z["at"]["beat"] in ("b1", "b2") for z in res["playbook"]["camera"]["zooms"])


def test_caption_mask_removes_false_zooms(workdir):
    video = workdir / "synthetic-captions.mp4"
    if not video.exists():
        write_video(video, caption_only_frames())
    masked = run_cm(video, workdir / "cap-auto")
    assert [z for z in masked["zoomEvents"] if not z["transition"]] == []
    assert masked["transitions"] == []
    assert {s["kind"] for s in masked["segments"]} == {"static"}


def max_scale_jump(res: dict) -> float:
    return max(abs(f["scale"] - 1) for f in res["frames"] if f["method"] != "none")


def test_caption_mask_on_dark_footage(workdir):
    """On dark, flat footage the caption's own features drive the estimate unless they are masked."""
    video = workdir / "synthetic-captions-dark.mp4"
    if not video.exists():
        write_video(video, caption_only_frames(dark=True))
    track = workdir / "captions.json"
    track.write_text(json.dumps(caption_track()))
    bare = run_cm(video, workdir / "cap-dark-none", "--mask-captions", "none")
    auto = run_cm(video, workdir / "cap-dark-auto")
    filed = run_cm(video, workdir / "cap-dark-file", "--mask-captions", str(track))
    assert max_scale_jump(bare) > 0.02, max_scale_jump(bare)
    assert len([z for z in bare["zoomEvents"] if not z["transition"]]) >= 4, "unmasked run should be fooled by the scale-in"
    for res in (auto, filed):
        assert {s["kind"] for s in res["segments"]} == {"static"}
        assert [z for z in res["zoomEvents"] if not z["transition"]] == []
        assert res["transitions"] == []
        assert max_scale_jump(res) < 0.5 * max_scale_jump(bare), (max_scale_jump(res), max_scale_jump(bare))


def test_prep_shots_are_checked(main_reel, workdir):
    video = workdir / "synthetic-main.mp4"
    shots = workdir / "shots.json"
    shots.write_text(json.dumps([{"id": "s001", "tIn": 0.0, "tOut": 4.0}, {"id": "s002", "tIn": 4.0, "tOut": 7.0},
                                 {"id": "s003", "tIn": 7.0, "tOut": 10.8}]))
    res = run_cm(video, workdir / "with-shots", "--shots", str(shots))
    by_src = {round(tr["atSec"], 1): tr for tr in res["transitions"]}
    assert by_src[4.0]["source"] == "both"
    assert any(tr["source"] == "prep" and tr["confidence"] == "unconfirmed" and near(tr["atSec"], 7.0, 0.15)
               for tr in res["transitions"])


# ---------------------------------------------------------------- ffmpeg-built reel (independent generator)

XF = [("fade", "fade"), ("slideleft", "whip"), ("zoomin", "zoom-cut"), ("fadeblack", "fade")]


@pytest.fixture(scope="session")
def ffmpeg_reel(workdir):
    if not HAS_FFMPEG:
        pytest.skip("ffmpeg not installed")
    video = workdir / "synthetic-xfade.mp4"
    clip_len, xd = 2.0, 0.5
    if not video.exists():
        stills = []
        for k in range(5):
            p = workdir / f"still{k}.png"
            cv2.imwrite(str(p), view(make_scene(20 + k), 900, 1000, 1.0))
            stills.append(p)
        inputs = []
        for p in stills:
            inputs += ["-loop", "1", "-t", str(clip_len), "-r", str(FPS), "-i", str(p)]
        # clip 0 gets an ffmpeg zoompan push-in from 0.5 s to 1.5 s (1.0 -> 1.25), upscaled first to avoid jitter
        zp = (f"[0:v]scale={W * 4}:{H * 4},zoompan=z='if(lt(on,15),1,if(lt(on,45),1+0.25*(on-15)/30,1.25))'"
              f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[v0]")
        chain, prev, off = [zp], "v0", 0.0
        for k in range(1, 5):
            chain.append(f"[{k}:v]format=yuv420p,setsar=1[c{k}]")
        for k, (name, _) in enumerate(XF, start=1):
            off += clip_len - xd
            chain.append(f"[{prev}][c{k}]xfade=transition={name}:duration={xd}:offset={off:.3f}[x{k}]")
            prev = f"x{k}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", f"[{prev}]",
                        "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(video)], check=True)
    truth = [((clip_len - xd) * k + xd / 2, typ) for k, (_, typ) in enumerate(XF, start=1)]
    return run_cm(video, workdir / "xfade"), truth


def test_ffmpeg_transitions(ffmpeg_reel):
    res, truth = ffmpeg_reel
    got = [tr for tr in res["transitions"] if tr["confidence"] in ("high", "medium")]
    assert len(got) == len(truth), got
    for g, (at, typ) in zip(got, truth):
        assert near(g["atSec"], at, 0.2), (g, at)
        assert g["type"] == typ, (g, typ)


def test_ffmpeg_zoompan(ffmpeg_reel):
    res, _ = ffmpeg_reel
    z = [z for z in res["zoomEvents"] if not z["transition"]]
    assert len(z) == 1, z
    assert near(z[0]["tStart"], 0.5, 0.15) and near(z[0]["tEnd"], 1.5, 0.15), z
    assert near(z[0]["scaleTo"] / z[0]["scaleFrom"], 1.25, 0.03), z
    assert z[0]["easing"] == "linear", z


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", *sys.argv[1:]]))
