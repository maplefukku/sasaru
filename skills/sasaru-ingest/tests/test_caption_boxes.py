#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy>=1.26,<3",
#     "opencv-python-headless>=4.9,<5",
#     "pytest>=8,<9",
#     "jsonschema>=4.21,<5",
#     "pyyaml>=6,<7",
# ]
# ///
"""caption_boxes.py を合成動画で確かめる。 uv run --script skills/sasaru-ingest/tests/test_caption_boxes.py"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import jsonschema
import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/sasaru-ingest/scripts/caption_boxes.py"
SCHEMA = json.loads((ROOT / "schema/playbook.schema.json").read_text())

spec = importlib.util.spec_from_file_location("caption_boxes", SCRIPT)
cb = importlib.util.module_from_spec(spec)
sys.modules["caption_boxes"] = cb
spec.loader.exec_module(cb)

W, H, FPS, N = 540, 960, 30, 120
FONT = cv2.FONT_HERSHEY_DUPLEX
SCALE, THICK, STROKE = 1.5, 3, 3

CARD_A = dict(lines=["HELLO WORLD"], f_in=15, f_out=45, shadow=False)
CARD_B = dict(lines=["LINE ONE", "LINE TWO"], f_in=45, f_out=75, shadow=True)
CARD_C = dict(lines=["THE END"], f_in=81, f_out=N, shadow=True, fade=8)
CY = 0.25


def background(i: int, rng: np.random.Generator) -> np.ndarray:
    ramp = np.linspace(30, 60, H, dtype=np.float32)[:, None, None]
    img = np.repeat(np.repeat(ramp, W, axis=1), 3, axis=2)
    img += rng.normal(0, 2, img.shape).astype(np.float32)
    cv2.ellipse(img, (W // 2, int(0.62 * H)), (int(0.22 * W), int(0.16 * H)), 0, 0, 360, (120, 140, 180), -1)
    yy, xx = np.mgrid[0:H, 0:W]
    hx, hy = int(0.42 * W + 2 * i), int(0.58 * H)
    spot = np.exp(-((xx - hx) ** 2 + (yy - hy) ** 2) / (2 * 22.0**2)).astype(np.float32)
    img += (255 - img) * spot[..., None]
    pillow = np.zeros((H, W), np.float32)
    pillow[int(0.80 * H):, int(0.55 * W):] = 1
    pillow = cv2.GaussianBlur(pillow, (0, 0), 25)
    img = img * (1 - pillow[..., None]) + 240 * pillow[..., None]
    img[int(0.08 * H): int(0.08 * H) + 70, 20:80] = 250
    return img


def line_layout(lines: list[str]) -> list[tuple[str, int, int]]:
    sizes = [cv2.getTextSize(t, FONT, SCALE, THICK) for t in lines]
    lh = max(s[0][1] for s in sizes)
    gap = int(0.6 * lh)
    total = len(lines) * lh + (len(lines) - 1) * gap
    top = int(CY * H - total / 2)
    out = []
    for j, (t, ((tw, _), _)) in enumerate(zip(lines, sizes)):
        out.append((t, (W - tw) // 2, top + lh + j * (lh + gap)))
    return out


def draw_card(img: np.ndarray, card: dict, alpha: float, words: int | None = None) -> None:
    layer = np.zeros_like(img)
    cover = np.zeros(img.shape[:2], np.float32)
    shade = np.zeros(img.shape[:2], np.float32)
    for t, x, y in line_layout(card["lines"]):
        if words is not None:
            t = " ".join(t.split()[:words])
        if card["shadow"]:
            cv2.putText(shade, t, (x, y + 4), FONT, SCALE, 1.0, THICK + 2 * STROKE + 2, cv2.LINE_AA)
        cv2.putText(cover, t, (x, y), FONT, SCALE, 1.0, THICK + 2 * STROKE, cv2.LINE_AA)
        cv2.putText(layer, t, (x, y), FONT, SCALE, (255, 255, 255), THICK, cv2.LINE_AA)
    if card["shadow"]:
        shade = cv2.GaussianBlur(shade, (0, 0), 6) * 0.6
        img *= 1 - alpha * shade[..., None]
    img *= 1 - alpha * cover[..., None]
    img += alpha * layer


def card_alpha(card: dict, i: int) -> float:
    if not card["f_in"] <= i < card["f_out"]:
        return 0.0
    fade = card.get("fade", 0)
    return min(1.0, (i - card["f_in"] + 1) / fade) if fade else 1.0


def white_truth(card: dict) -> tuple[float, float, list[float]]:
    img = np.zeros((H, W, 3), np.float32)
    draw_card(img, dict(card, shadow=False), 1.0)
    m = img.min(axis=2) > 220
    ys = np.flatnonzero(m.any(1))
    heights = []
    for _, _, y in line_layout(card["lines"]):
        band = m[y - 45: y + 8]
        rows = np.flatnonzero(band.any(1))
        heights.append((rows[-1] - rows[0] + 1) / H)
    return (ys[0] + ys[-1] + 1) / 2 / H, float(np.median(heights)), heights


def write_video(path: Path, cards=(CARD_A, CARD_B, CARD_C)) -> None:
    rng = np.random.default_rng(7)
    frames = []
    for i in range(N):
        img = background(i, rng)
        for card in cards:
            a = card_alpha(card, i)
            if a:
                reveal = card.get("reveal")
                words = sum(1 for f in reveal if i >= f) if reveal else None
                draw_card(img, card, a, words)
        frames.append(np.clip(img, 0, 255).astype(np.uint8))
    if shutil.which("ffmpeg"):
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(path)]
        subprocess.run(cmd, input=b"".join(f.tobytes() for f in frames), check=True)
    else:
        vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
        for f in frames:
            vw.write(f)
        vw.release()


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cb")
    video = tmp / "synthetic.mp4"
    write_video(video)
    work = tmp / "work"
    work.mkdir()
    (work / "source-text.json").write_text(json.dumps({"transcript": [{"t": 0.5, "text": "keep me"}]}))
    beats = tmp / "beats.json"
    beats.write_text(json.dumps({"beats": [{"id": "b1", "tIn": 0.0, "tOut": 1.5},
                                           {"id": "b2", "tIn": 1.5, "tOut": 4.0}]}))
    assert cb.main([str(video), str(work), "--beats", str(beats)]) == 0
    data = json.loads((work / "captions.json").read_text())
    return {"video": video, "work": work, "data": data, "tmp": tmp}


def by_frame(data: dict, f_in: int) -> dict:
    return min(data["cards"], key=lambda c: abs(c["frameIn"] - f_in))


def test_three_cards_with_frame_exact_cuts(run):
    cards = run["data"]["cards"]
    assert len(cards) == 3
    a, b = by_frame(run["data"], 15), by_frame(run["data"], 45)
    assert (a["frameIn"], a["frameOut"]) == (15, 45)
    assert (b["frameIn"], b["frameOut"]) == (45, 75)
    assert a["motionIn"] == "cut" and a["motionOut"] == "cut"
    assert a["at"] == {"beat": "b1", "offsetSec": 0.5}
    assert b["at"] == {"beat": "b2", "offsetSec": 0.0}


def test_fade_in_and_last_card_holds(run):
    c = by_frame(run["data"], 81)
    assert abs(c["frameIn"] - 81) <= 1
    assert c["motionIn"] == "fade"
    assert c["frameOut"] == N and c["holdsToEnd"]
    assert run["data"]["lastCard"]["holdsToEnd"] is True
    assert run["data"]["lastCard"]["lastFrame"] == N - 1


def test_geometry_matches_rendered_white(run):
    for card in (CARD_A, CARD_B, CARD_C):
        got = by_frame(run["data"], card["f_in"])
        cy, cap, heights = white_truth(card)
        assert abs(got["cy"] - cy) < 0.004
        assert abs(got["cx"] - 0.5) < 0.01
        assert abs(got["bboxHeightRatio"] - cap) < 0.003
        assert abs(got["capHeightRatio"] - cap) < 0.003
        assert got["lines"] == len(card["lines"])
        assert len(got["lineHeights"]) == len(heights)


def test_stroke_and_shadow(run):
    a, b, c = (by_frame(run["data"], f) for f in (15, 45, 81))
    for card in (a, b, c):
        assert card["color"] == "#FFFFFF"
        assert card["stroke"] is not None and card["stroke"]["color"] == "#000000"
        assert 3 <= card["stroke"]["px1080"] <= 10
    assert a["shadow"] is False
    assert b["shadow"] is True and c["shadow"] is True


def test_non_caption_whites_are_ignored(run):
    for fr in run["data"]["frames"]:
        for box in fr["boxes"]:
            assert 0.15 < box["cy"] < 0.35, box
    gaps = run["data"]["noCaption"]
    assert gaps[0]["tIn"] == 0.0 and gaps[0]["frames"] == 15
    assert run["data"]["firstFrameHasText"] is False


def test_layer_fits_caption_layer_schema(run):
    layers = run["data"]["playbook"]["captions"]
    assert len(layers) == 1
    layer = layers[0]
    validator = jsonschema.Draft202012Validator({"$defs": SCHEMA["$defs"], "$ref": "#/$defs/captionLayer"})
    validator.validate(layer)
    assert layer["id"] == "c1"
    assert layer["linesMax"] == 2
    assert layer["lastCard"] == "hold-to-end"
    assert layer["hide"] == "beat-end"
    assert layer["beats"] == []
    assert layer["position"]["align"] == "center"
    ev = run["data"]["playbook"]["evidence"]
    assert "captions.c1.capHeightRatio" in ev["measured"]
    assert "captions.c1.beats" in ev["measured"]
    assert all(p.startswith("captions.c1.") for kind in ev.values() for p in kind)


def test_layer_drops_into_template_playbook(run):
    text = (ROOT / "templates/playbook.md").read_text()
    front = yaml.safe_load(text.split("---\n")[1])
    front["captions"] = run["data"]["playbook"]["captions"]
    ev = run["data"]["playbook"]["evidence"]
    for kind in ("measured", "inferred", "unmeasured"):
        kept = [p for p in front["evidence"][kind] if not p.startswith("captions.")]
        front["evidence"][kind] = kept + ev[kind]
    jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker()).validate(front)


def test_no_wording_in_captions_json_and_source_text_kept_apart(run):
    raw = (run["work"] / "captions.json").read_text()
    for word in ("HELLO", "WORLD", "LINE", "END"):
        assert word not in raw
    src = json.loads((run["work"] / "source-text.json").read_text())
    assert src["transcript"] == [{"t": 0.5, "text": "keep me"}]
    assert [c["card"] for c in src["captions"]] == [c["id"] for c in run["data"]["cards"]]
    assert all(c["text"] is None for c in src["captions"])


def test_native_step_agrees(run):
    work = run["tmp"] / "native"
    assert cb.main([str(run["video"]), str(work), "--step", "native"]) == 0
    data = json.loads((work / "captions.json").read_text())
    got = sorted((c["frameIn"], c["frameOut"]) for c in data["cards"])
    want = sorted((c["frameIn"], c["frameOut"]) for c in run["data"]["cards"])
    assert got == want


@pytest.mark.skipif(not shutil.which("tesseract"), reason="tesseract が無い")
def test_ocr_writes_text_only_to_source_text(run):
    work = run["tmp"] / "ocr"
    assert cb.main([str(run["video"]), str(work), "--ocr", "--ocr-lang", "eng"]) == 0
    src = json.loads((work / "source-text.json").read_text())
    texts = [c["text"] or "" for c in src["captions"]]
    assert any("HELLO" in t for t in texts)
    raw = (work / "captions.json").read_text()
    assert "HELLO" not in raw
    a = json.loads(raw)["cards"][0]
    assert a["chars"] == 10


def test_word_by_word_reveal_is_one_card(tmp_path):
    card = dict(lines=["ONE TWO SIX"], f_in=20, f_out=80, shadow=False, reveal=[20, 35, 50])
    video = tmp_path / "words.mp4"
    write_video(video, (card,))
    assert cb.main([str(video), str(tmp_path / "w")]) == 0
    data = json.loads((tmp_path / "w" / "captions.json").read_text())
    assert len(data["cards"]) == 1
    got = data["cards"][0]
    assert (got["frameIn"], got["frameOut"]) == (20, 80)
    assert got["motionIn"] == "word-by-word" and got["steps"] == 3
    assert data["playbook"]["captions"][0]["motionIn"] == "word-by-word"


def test_roi_limits_the_search(run):
    work = run["tmp"] / "roi"
    assert cb.main([str(run["video"]), str(work), "--roi", "0,0.5,1,0.5"]) == 0
    data = json.loads((work / "captions.json").read_text())
    assert data["cards"] == [] and data["playbook"]["captions"] == []
    assert data["roi"] == [0, H // 2, W, H]


def test_input_errors_exit_2(run, tmp_path):
    video = str(run["video"])
    assert cb.main([str(tmp_path / "missing.mp4"), str(tmp_path / "w")]) == 2
    assert cb.main([video, str(tmp_path / "w"), "--color", "red"]) == 2
    assert cb.main([video, str(tmp_path / "w"), "--roi", "0,0,2,1"]) == 2
    assert cb.main([video, str(tmp_path / "w"), "--step", "0"]) == 2


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-rs"]))
