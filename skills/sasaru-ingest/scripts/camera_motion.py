#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless>=4.10,<6", "numpy>=1.26,<3"]
# ///
"""Measure the camera and the edit of one reference short: cuts, transitions,
zoom in/out, pan and tilt, handheld shake and static spans, all with seconds.

Usage:
  camera_motion.py <video> <work_dir> [--fps 10] [--width 360]
                   [--mask-captions auto|none|<captions.json>] [--caption-threshold 220]
                   [--shots <shots.json>] [--beats <beats.json>] [--json]
  camera_motion.py --rekey <work_dir>/camera.json --beats <beats.json> [--json]

Writes <work_dir>/camera.json. Logs go to stderr; --json also prints the result to stdout.
Exit codes: 0 ok, 2 bad input.

Motion is a similarity transform (scale, rotation, shift) between frames sampled at --fps,
from ORB matches with RANSAC, falling back to Farneback flow when ORB finds too little.
Caption pixels are excluded before estimating: burnt-in text is fixed to the screen and
otherwise votes for "no motion" or, when a card pops in, for a zoom that is not there.
With --mask-captions auto the script finds bright, line-shaped text itself; a captions.json
from caption_boxes.py (frames[].boxes[] or cards[] with cx, cy, w, h) replaces that.

Cuts are found at the native frame rate. --shots takes prep.py's shots.json
([{id, tIn, tOut}] or {"shots": [...]}) and every boundary in it is checked and reported.
Transitions are typed as cut, jump-cut, dissolve, fade-black, fade-white, slide, whip,
zoom or glitch, and mapped to the playbook schema's camera.transitions[].type.

Scales in zoom events are relative to the widest framing measured in the same shot.
Pan directions are camera directions (content moving left means the camera pans right).

The playbook schema keys times to beats. --beats takes [{id, tIn, tOut}] or a playbook-like
{"beats": [...]}; then camera.json carries a "playbook" block with camera.moves, zooms and
transitions keyed as {beat, offsetSec}, plus source.reference.hardCuts. Beats are usually
decided after this runs, so --rekey rebuilds that block from an existing camera.json
without decoding the video again.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

VERSION = 1
THUMB_W = 96

CUT_ABS = 0.55
CUT_REL = 3.0
GRADUAL_RESID = 0.14
REGISTER_RESID = 0.32
ZOOM_STEP_LN = 0.003
ZOOM_MIN_LN = math.log(1.04)
ZOOM_CONSISTENCY = 0.75
PAN_SPEED = 0.06
SHAKE_STEP = 0.0012
ROT_TO_SHIFT = 0.005
SNAP_MAX_SEC = 0.2
MIN_SEGMENT_SEC = 0.3
FAST_ZOOM_LN_PER_SEC = 0.8
WHIP_SPEED = 1.2

SCHEMA_TYPE = {
    "cut": "hard-cut",
    "jump-cut": "hard-cut",
    "dissolve": "fade",
    "fade-black": "fade",
    "fade-white": "fade",
    "gradual": "fade",
    "slide": "whip",
    "whip": "whip",
    "zoom": "zoom-cut",
    "glitch": "glitch",
}
SCHEMA_MOVE = {
    "static": "static",
    "shake": "handheld",
    "zoom-in": "push-in",
    "zoom-out": "pull-out",
    "pan": "pan",
    "tilt": "tilt",
}


class InputError(Exception):
    pass


def log(*a):
    print(*a, file=sys.stderr)


def r3(x):
    return None if x is None else round(float(x), 3)


def r4(x):
    return None if x is None else round(float(x), 4)


# ---------------------------------------------------------------- captions


def detect_caption_boxes(bgr: np.ndarray, threshold: int) -> list[tuple[float, float, float, float]]:
    """Bright, low-saturation, line-shaped blobs. Returns normalized (x, y, w, h)."""
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    bright = ((hsv[..., 2] >= threshold) & (hsv[..., 1] <= 70)).astype(np.uint8)
    if bright.sum() < 8:
        return []
    kx = max(3, int(round(0.03 * w))) | 1
    ky = max(3, int(round(0.012 * h))) | 1
    closed = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (kx, ky)))
    _, _, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    boxes = []
    for x, y, bw, bh, _area in stats[1:]:
        if bw < 0.04 * w or bh < 0.006 * h or bh > 0.10 * h or bw < 0.8 * bh:
            continue
        fill = float(bright[y : y + bh, x : x + bw].mean())
        if not 0.05 <= fill <= 0.75:
            continue
        boxes.append((x / w, y / h, bw / w, bh / h))
    return boxes


def _norm_box(b: dict, vw: int, vh: int):
    if "x" in b and "y" in b:
        x, y, bw, bh = b["x"], b["y"], b.get("w"), b.get("h")
        cx = cy = None
    else:
        cx, cy, bw, bh = b.get("cx"), b.get("cy"), b.get("w"), b.get("h")
        x = y = None
    if bw is None:
        return None
    if bh is None:
        bh = (b.get("capHeightRatio") or 0.03) * 2.2 * (b.get("lines") or 1)
    vals = [v for v in (x, y, cx, cy, bw, bh) if v is not None]
    if any(v > 1.5 for v in vals):
        sx, sy = 1.0 / vw, 1.0 / vh
        bw, bh = bw * sx, bh * sy
        x, y = (None if x is None else x * sx), (None if y is None else y * sy)
        cx, cy = (None if cx is None else cx * sx), (None if cy is None else cy * sy)
    if x is None:
        x, y = cx - bw / 2, cy - bh / 2
    return (float(x), float(y), float(bw), float(bh))


def load_caption_track(path: Path, vw: int, vh: int):
    try:
        d = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise InputError(f"cannot read captions file {path}: {e}") from e
    frames = []
    for f in d.get("frames", []) or []:
        boxes = [nb for nb in (_norm_box(b, vw, vh) for b in f.get("boxes", []) or []) if nb]
        frames.append((float(f["t"]), boxes))
    cards = []
    for c in d.get("cards", []) or []:
        nb = _norm_box(c, vw, vh)
        if nb and "tIn" in c and "tOut" in c:
            cards.append((float(c["tIn"]), float(c["tOut"]), nb))
    if not frames and not cards:
        raise InputError(f"captions file {path} has neither frames[] nor cards[] with boxes")
    frames.sort(key=lambda x: x[0])
    return frames, cards


def boxes_to_mask(boxes, w: int, h: int, mx: float = 0.02, my: float = 0.012) -> np.ndarray:
    m = np.full((h, w), 255, np.uint8)
    for x, y, bw, bh in boxes:
        x0, y0 = int(max(0, (x - mx) * w)), int(max(0, (y - my) * h))
        x1, y1 = int(min(w, math.ceil((x + bw + mx) * w))), int(min(h, math.ceil((y + bh + my) * h)))
        if x1 > x0 and y1 > y0:
            m[y0:y1, x0:x1] = 0
    return m


# ---------------------------------------------------------------- motion


@dataclass
class Frame:
    gray: np.ndarray
    eq: np.ndarray
    mask: np.ndarray
    pts: np.ndarray | None = None
    des: np.ndarray | None = None


@dataclass
class Motion:
    scale: float = 1.0
    tx: float = 0.0
    ty: float = 0.0
    rot: float = 0.0
    method: str = "none"
    inliers: int = 0
    resid: float = 1.0

    @property
    def ok(self) -> bool:
        return self.method != "none" and self.resid <= REGISTER_RESID

    @property
    def ls(self) -> float:
        return math.log(self.scale)


class Estimator:
    def __init__(self):
        self.orb = cv2.ORB_create(nfeatures=1500, fastThreshold=7)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def frame(self, gray: np.ndarray, mask: np.ndarray) -> Frame:
        eq = self.clahe.apply(gray)
        kp, des = self.orb.detectAndCompute(eq, mask)
        pts = np.float32([k.pt for k in kp]) if kp else None
        return Frame(gray=cv2.GaussianBlur(gray, (3, 3), 0), eq=eq, mask=mask, pts=pts, des=des)

    def estimate(self, a: Frame, b: Frame) -> Motion:
        h, w = a.gray.shape
        M, inl, method = None, 0, "none"
        if a.des is not None and b.des is not None and len(a.des) >= 8 and len(b.des) >= 8:
            matches = self.bf.match(a.des, b.des)
            if len(matches) >= 10:
                p = a.pts[[m.queryIdx for m in matches]]
                q = b.pts[[m.trainIdx for m in matches]]
                M, keep = cv2.estimateAffinePartial2D(
                    p, q, method=cv2.RANSAC, ransacReprojThreshold=2.0, maxIters=3000, confidence=0.995
                )
                inl = int(keep.sum()) if keep is not None else 0
                if M is not None and inl >= max(10, 0.25 * len(matches)):
                    method = "orb"
                else:
                    M = None
        if M is None:
            M, inl = self._flow(a, b)
            if M is not None:
                method = "flow"
        if M is None:
            return Motion(resid=self.residual(a, b, np.float32([[1, 0, 0], [0, 1, 0]])))
        s = math.hypot(M[0, 0], M[1, 0])
        rot = math.degrees(math.atan2(M[1, 0], M[0, 0]))
        cx, cy = w / 2.0, h / 2.0
        ncx = M[0, 0] * cx + M[0, 1] * cy + M[0, 2]
        ncy = M[1, 0] * cx + M[1, 1] * cy + M[1, 2]
        return Motion(
            scale=s, tx=(ncx - cx) / w, ty=(ncy - cy) / h, rot=rot, method=method, inliers=inl,
            resid=self.residual(a, b, M),
        )

    def _flow(self, a: Frame, b: Frame):
        flow = cv2.calcOpticalFlowFarneback(a.eq, b.eq, None, 0.5, 4, 21, 3, 5, 1.1, 0)
        h, w = a.gray.shape
        st = 8
        ys, xs = np.mgrid[st // 2 : h : st, st // 2 : w : st]
        gx = cv2.Sobel(a.eq, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(a.eq, cv2.CV_32F, 0, 1, ksize=3)
        mag = cv2.magnitude(gx, gy)
        tex = mag[ys, xs]
        valid = (a.mask[ys, xs] > 0) & (b.mask[ys, xs] > 0) & (tex > max(20.0, float(np.percentile(mag, 60))))
        if valid.sum() < 40:
            return None, 0
        p = np.stack([xs[valid], ys[valid]], 1).astype(np.float32)
        q = p + flow[ys[valid], xs[valid]]
        M, keep = cv2.estimateAffinePartial2D(p, q, method=cv2.RANSAC, ransacReprojThreshold=1.0, maxIters=2000)
        inl = int(keep.sum()) if keep is not None else 0
        if M is None or inl < max(30, 0.3 * len(p)):
            return None, 0
        return M, inl

    @staticmethod
    def residual(a: Frame, b: Frame, M: np.ndarray) -> float:
        h, w = a.gray.shape
        warped = cv2.warpAffine(a.gray, M, (w, h), flags=cv2.INTER_LINEAR)
        inside = cv2.warpAffine(a.mask, M, (w, h), flags=cv2.INTER_NEAREST)
        valid = (inside > 0) & (b.mask > 0)
        if valid.sum() < 0.05 * w * h:
            return 1.0
        bv = b.gray[valid].astype(np.float32)
        diff = np.abs(warped[valid].astype(np.float32) - bv)
        return float(diff.mean() / (bv.std() + 4.0))


# ---------------------------------------------------------------- video access


@dataclass
class Video:
    path: Path
    fps: float
    n: int
    width: int
    height: int
    aw: int
    ah: int


def open_video(path: Path, width: int):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise InputError(f"cannot open video {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps <= 0 or fps > 480 or w <= 0 or h <= 0:
        raise InputError(f"no usable frame rate or size in {path}")
    aw = min(width, w)
    ah = max(2, int(round(h * aw / w / 2)) * 2)
    return cap, Video(path, fps, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), w, h, aw, ah)


class WindowReader:
    """Re-decodes native frames for short windows (zoom refinement, transition typing)."""

    def __init__(self, video: Video, masks, est: Estimator, thumbs):
        self.video, self.masks, self.est, self.thumbs = video, masks, est, thumbs
        self.cap = cv2.VideoCapture(str(video.path))
        self.cache: dict[int, Frame] = {}

    def _decode(self, i0: int, i1: int):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, i0)
        out = {}
        for i in range(i0, i1 + 1):
            ok, fr = self.cap.read()
            if not ok:
                break
            out[i] = cv2.cvtColor(cv2.resize(fr, (self.video.aw, self.video.ah), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        if i0 in out:
            th = cv2.resize(out[i0], self.thumbs[i0].shape[::-1], interpolation=cv2.INTER_AREA).astype(np.float32)
            if np.abs(th - self.thumbs[i0]).mean() > 6.0:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                out = {}
                for i in range(0, i1 + 1):
                    ok, fr = self.cap.read()
                    if not ok:
                        break
                    if i >= i0:
                        out[i] = cv2.cvtColor(
                            cv2.resize(fr, (self.video.aw, self.video.ah), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY
                        )
        return out

    def frames(self, i0: int, i1: int) -> dict[int, Frame]:
        i0, i1 = max(0, i0), min(self.video.n - 1, i1)
        missing = [i for i in range(i0, i1 + 1) if i not in self.cache]
        if missing:
            for i, g in self._decode(missing[0], missing[-1]).items():
                if i not in self.cache:
                    self.cache[i] = self.est.frame(g, self.masks(i))
        return {i: self.cache[i] for i in range(i0, i1 + 1) if i in self.cache}

    def pair_motion(self, i0: int, i1: int) -> list[tuple[int, Motion]]:
        fr = self.frames(i0, i1)
        return [(i, self.est.estimate(fr[i - 1], fr[i])) for i in range(i0 + 1, i1 + 1) if i in fr and i - 1 in fr]


# ---------------------------------------------------------------- analysis helpers


def thumb_dist(a: np.ndarray, b: np.ndarray, ma: np.ndarray, mb: np.ndarray, win: np.ndarray) -> float:
    """Contrast-normalized difference after the best whole-pixel-ish shift."""
    h, w = a.shape
    (dx, dy), _ = cv2.phaseCorrelate(a, b, win)
    best = None
    for sx, sy in ((dx, dy), (-dx, -dy), (0.0, 0.0)):
        M = np.float32([[1, 0, sx], [0, 1, sy]])
        wa = cv2.warpAffine(a, M, (w, h))
        wm = cv2.warpAffine(ma, M, (w, h), flags=cv2.INTER_NEAREST)
        v = (wm > 0) & (mb > 0)
        if v.sum() < 0.2 * w * h:
            continue
        d = float(np.abs(wa[v] - b[v]).mean() / (0.5 * (a[ma > 0].std() + b[v].std()) + 2.0))
        best = d if best is None else min(best, d)
    return 1.0 if best is None else best


def blend_fit(a: np.ndarray, b: np.ndarray, mids: list[np.ndarray]):
    """How well each middle frame is a mix of a and b. Returns (alphas, relative residuals)."""
    ab = (a - b).ravel()
    den = float(ab @ ab) + 1e-6
    alphas, res = [], []
    for m in mids:
        mb = (m - b).ravel()
        al = float(np.clip((mb @ ab) / den, 0, 1))
        r = mb - al * ab
        alphas.append(al)
        res.append(float(math.sqrt(r @ r / den)))
    return alphas, res


def easing_of(times: np.ndarray, progress: np.ndarray, dur: float) -> str:
    if dur <= SNAP_MAX_SEC + 1e-6:
        return "snap"
    x = (times - times[0]) / max(dur, 1e-6)
    p = np.clip(progress, 0, 1)

    def at(v):
        return float(np.interp(v, x, p))

    early, late = at(0.25), 1.0 - at(0.75)
    steep = (at(0.6) - at(0.4)) * 5.0
    if late - early > 0.12:
        return "ease-in"
    if early - late > 0.12:
        return "ease-out"
    if steep >= 1.25 or early + late <= 0.38:
        return "ease-in-out"
    return "linear"


def moving_avg(x: np.ndarray, valid: np.ndarray, k: int) -> np.ndarray:
    xv = np.where(valid, x, 0.0)
    ker = np.ones(k)
    num = np.convolve(xv, ker, mode="same")
    den = np.convolve(valid.astype(float), ker, mode="same")
    return np.where(den > 0, num / np.maximum(den, 1e-9), 0.0)


# ---------------------------------------------------------------- main analysis


def analyze(video_path: Path, args) -> dict:
    cap, v = open_video(video_path, args.width)
    step = max(1, int(round(v.fps / args.fps)))
    th_h = max(8, int(round(v.height * THUMB_W / v.width)))
    est = Estimator()
    notes: list[str] = []

    caption_track = None
    if args.mask_captions not in ("auto", "none"):
        caption_track = load_caption_track(Path(args.mask_captions), v.width, v.height)

    thumbs, hists, lumas, auto_boxes, sample_gray = [], [], [], [], {}
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        small = cv2.resize(fr, (v.aw, v.ah), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        boxes = detect_caption_boxes(small, args.caption_threshold) if args.mask_captions == "auto" else []
        auto_boxes.append(boxes)
        m = boxes_to_mask(boxes, v.aw, v.ah)
        thumbs.append(cv2.resize(gray, (THUMB_W, th_h), interpolation=cv2.INTER_AREA).astype(np.float32))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], m, [8, 4, 8], [0, 180, 0, 256, 0, 256])
        hists.append(cv2.normalize(hist, hist).flatten())
        lumas.append(float(gray[m > 0].mean()) if (m > 0).any() else float(gray.mean()))
        if i % step == 0:
            sample_gray[i] = gray
        last_gray = gray
        i += 1
    cap.release()
    n = i
    if n < 2:
        raise InputError(f"{video_path} has fewer than two decodable frames")
    v.n = n
    sample_gray[n - 1] = last_gray
    t_of = lambda k: k / v.fps  # noqa: E731
    duration = n / v.fps

    # caption mask per native frame: union over a short window so fades and pops stay covered
    span = max(1, int(round(0.3 * v.fps)))

    def frame_boxes(k: int):
        if args.mask_captions == "none":
            return []
        if caption_track is None:
            out = []
            for j in range(max(0, k - span), min(n, k + span + 1)):
                out.extend(auto_boxes[j])
            return out
        frames_, cards = caption_track
        t = t_of(k)
        out = [bx for (a, b, bx) in cards if a - 0.1 <= t <= b + 0.1]
        if frames_:
            ts = np.array([f[0] for f in frames_])
            gap = float(np.median(np.diff(ts))) if len(ts) > 1 else 0.1
            win = 0.6 * gap + 0.1
            lo, hi = np.searchsorted(ts, t - win), np.searchsorted(ts, t + win, side="right")
            for f in frames_[lo:hi]:
                out.extend(f[1])
        return out

    mask_cache: dict[int, np.ndarray] = {}

    def mask_of(k: int) -> np.ndarray:
        if k not in mask_cache:
            mask_cache[k] = boxes_to_mask(frame_boxes(k), v.aw, v.ah)
        return mask_cache[k]

    masked_frames = sum(1 for k in range(n) if frame_boxes(k))
    coverage = float(np.mean([1 - mask_of(k).mean() / 255 for k in sample_gray]))

    # native-rate appearance change
    win = cv2.createHanningWindow((THUMB_W, th_h), cv2.CV_32F)
    tmask = lambda k: cv2.resize(mask_of(k), (THUMB_W, th_h), interpolation=cv2.INTER_NEAREST)  # noqa: E731
    D = np.zeros(n)
    Hd = np.zeros(n)
    for k in range(1, n):
        D[k] = thumb_dist(thumbs[k - 1], thumbs[k], tmask(k - 1), tmask(k), win)
        Hd[k] = cv2.compareHist(hists[k - 1], hists[k], cv2.HISTCMP_BHATTACHARYYA)

    # hard cuts: single-frame spikes
    W = max(3, int(round(0.5 * v.fps)))
    spikes = []
    for k in range(1, n):
        local = np.concatenate([D[max(1, k - W) : k], D[k + 1 : k + W + 1]])
        base = float(np.median(local)) if len(local) else 0.0
        if D[k] >= CUT_ABS and D[k] >= CUT_REL * base + 0.05 and (Hd[k] >= 0.08 or D[k] >= 2 * CUT_ABS):
            spikes.append(k)
    spikes = [k for k in spikes if not any(abs(k - o) <= 1 and D[o] > D[k] for o in spikes)]

    # sampled motion
    samples = sorted(sample_gray)
    sframes = {k: est.frame(sample_gray[k], mask_of(k)) for k in samples}
    pairs = []  # (k0, k1, Motion)
    for a, b in zip(samples[:-1], samples[1:]):
        pairs.append((a, b, est.estimate(sframes[a], sframes[b])))
    reader = WindowReader(v, mask_of, est, thumbs)

    # group spikes into transitions; neighbouring spikes form one short multi-frame event
    transitions = []
    groups: list[list[int]] = []
    for k in spikes:
        if groups and k - groups[-1][-1] <= max(2, int(round(0.2 * v.fps))):
            groups[-1].append(k)
        else:
            groups.append([k])
    for g in groups:
        i0, i1 = g[0] - 1, g[-1]
        moved = motion_explained(i0, i1, reader, v)
        if moved is not None:
            if moved.get("kind"):
                transitions.append(moved)
            continue
        tr = {"tStart": t_of(g[0]), "tEnd": t_of(g[-1]), "atSec": t_of(g[0]), "i0": i0, "i1": i1,
              "kind": "cut", "source": "detected", "confidence": "high", "score": r3(max(D[x] for x in g))}
        if len(g) > 1:
            inner = lumas[g[0] : g[-1]]
            ends = (lumas[i0], lumas[i1])
            if inner and max(inner) > max(ends) + 40 and max(inner) > 170:
                tr["kind"] = "fade-white"
            elif inner and min(inner) < 0.5 * min(ends) and min(inner) < 40:
                tr["kind"] = "fade-black"
            else:
                gtr = classify_gradual(i0, i1, reader, thumbs, lumas, D, v, tighten=False)
                if gtr["kind"] == "gradual" and (i1 - i0) / v.fps <= 0.35:
                    tr["kind"] = "glitch"
                else:
                    gtr["confidence"] = "high" if gtr["kind"] != "gradual" else "low"
                    tr = gtr
            tr["atSec"] = 0.5 * (tr["tStart"] + tr["tEnd"])
        transitions.append(tr)

    def in_cut(a: int, b: int) -> bool:
        return any(a < x <= b for x in spikes)

    # gradual transitions: runs of sampled pairs that motion cannot explain
    rough = [(not in_cut(a, b)) and (m.method == "none" or m.resid > GRADUAL_RESID) for a, b, m in pairs]
    runs, cur = [], []
    for idx, r in enumerate(rough):
        if r:
            cur.append(idx)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    for run in runs:
        if len(run) < 2:
            continue
        i0, i1 = pairs[run[0]][0], pairs[run[-1]][1]
        a_f, b_f = sframes[i0], sframes[i1]
        whole = est.estimate(a_f, b_f)
        far = thumb_dist(thumbs[i0], thumbs[i1], tmask(i0), tmask(i1), win)
        if whole.ok and whole.resid <= GRADUAL_RESID:
            continue
        if far < 0.35:
            continue
        tr = classify_gradual(i0, i1, reader, thumbs, lumas, D, v)
        if tr is not None:
            transitions.append(tr)

    # a run of very fast travel that covers half a frame or more is a slide or a whip, not a pan
    covered = lambda a, b: any(tr["i0"] <= a and b <= tr["i1"] for tr in transitions)  # noqa: E731
    run = []
    for idx, (a, b, m) in enumerate(pairs + [(n, n, Motion())]):
        speed = math.hypot(m.tx, m.ty) * v.fps / max(b - a, 1)
        if m.ok and m.resid <= GRADUAL_RESID and speed >= WHIP_SPEED and not in_cut(a, b) and not covered(a, b):
            run.append(idx)
            continue
        if run:
            ms = [pairs[j][2] for j in run]
            sx, sy = sum(x.tx for x in ms), sum(x.ty for x in ms)
            if max(abs(sx), abs(sy)) >= 0.5:
                i0, i1 = pairs[run[0]][0], pairs[run[-1]][1]
                far = thumb_dist(thumbs[i0], thumbs[i1], tmask(i0), tmask(i1), win)
                transitions.append({
                    "tStart": i0 / v.fps, "tEnd": i1 / v.fps, "atSec": 0.5 * (i0 + i1) / v.fps, "i0": i0, "i1": i1,
                    "kind": "slide" if far >= 0.35 else "whip", "source": "detected", "confidence": "medium",
                    "direction": ("left" if sx < 0 else "right") if abs(sx) >= abs(sy) else ("up" if sy < 0 else "down"),
                    "score": r3(far),
                })
            run = []

    transitions = merge_transitions(transitions, v)

    # prep shot candidates
    prep_bounds = []
    if args.shots:
        prep_bounds = load_shot_bounds(Path(args.shots))
        for tb in prep_bounds:
            near = [tr for tr in transitions if tr["tStart"] - 0.25 <= tb <= tr["tEnd"] + 0.25]
            if near:
                for tr in near:
                    tr["source"] = "both"
                continue
            k = int(round(tb * v.fps))
            lo, hi = max(1, k - 3), min(n - 1, k + 3)
            kk = lo + int(np.argmax(D[lo : hi + 1])) if hi >= lo else k
            transitions.append({
                "tStart": t_of(kk), "tEnd": t_of(kk), "atSec": t_of(kk), "i0": kk - 1, "i1": kk,
                "kind": "cut", "source": "prep", "confidence": "unconfirmed", "score": r3(D[kk]),
            })
    transitions.sort(key=lambda tr: tr["tStart"])

    # shots between transitions
    bounds = [0]
    for tr in transitions:
        if tr["confidence"] == "unconfirmed":
            continue
        bounds.append(tr["i0"] + 1 if tr["i1"] - tr["i0"] <= 1 else int(round(0.5 * (tr["i0"] + tr["i1"]))))
    bounds.append(n)
    shots = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b > a:
            shots.append({"id": f"s{len(shots) + 1:03d}", "tIn": r3(t_of(a)), "tOut": r3(t_of(b)), "i0": a, "i1": b - 1})

    blocked = np.zeros(n, bool)
    for tr in transitions:
        if tr["confidence"] != "unconfirmed":
            blocked[tr["i0"] + 1 : tr["i1"] + 1] = True
            if tr["i1"] - tr["i0"] > 1:
                blocked[tr["i0"] : tr["i1"] + 1] = True

    pair_valid = []
    for a, b, m in pairs:
        pair_valid.append(m.ok and not blocked[a + 1 : b + 1].any())
    pair_valid = np.array(pair_valid, bool)
    dt = np.array([(b - a) / v.fps for a, b, _ in pairs])
    ls = np.array([m.ls for *_, m in pairs])
    tx = np.array([m.tx for *_, m in pairs])
    ty = np.array([m.ty for *_, m in pairs])
    rot = np.array([m.rot for *_, m in pairs])
    shot_of_pair = np.array([next((si for si, s in enumerate(shots) if s["i0"] <= a and b <= s["i1"]), -1) for a, b, _ in pairs])
    pair_valid &= shot_of_pair >= 0

    zooms = detect_zooms(pairs, pair_valid, shot_of_pair, ls, shots, reader, v)
    for z in zooms:
        fast = abs(math.log(z["factor"])) / max(z["durSec"], 1 / v.fps) >= FAST_ZOOM_LN_PER_SEC
        for tr in transitions:
            if tr["confidence"] == "unconfirmed" or tr["kind"] not in ("cut", "jump-cut", "zoom"):
                continue
            if fast and abs(z["factor"] - 1) >= 0.08 and z["tEnd"] >= tr["tStart"] - 0.12 and z["tStart"] <= tr["tEnd"] + 0.12:
                z["transition"] = True
                tr["kind"] = "zoom"

    # type the remaining hard cuts: whip if fast travel touches the cut, jump-cut if both sides register
    for tr in transitions:
        if tr["kind"] != "cut" or tr["confidence"] == "unconfirmed":
            continue
        near = [idx for idx, (a, b, _) in enumerate(pairs)
                if pair_valid[idx] and (abs(t_of(b) - tr["tStart"]) <= 0.25 or abs(t_of(a) - tr["tStart"]) <= 0.25)]
        speed = max((math.hypot(tx[i_], ty[i_]) / dt[i_] for i_ in near), default=0.0)
        if speed >= WHIP_SPEED:
            tr["kind"] = "whip"
            continue
        fr = reader.frames(tr["i0"], tr["i1"])
        if tr["i0"] in fr and tr["i1"] in fr:
            m = est.estimate(fr[tr["i0"]], fr[tr["i1"]])
            if m.ok and m.inliers >= 25:
                tr["kind"] = "jump-cut"

    for tr in transitions:
        tr["type"] = SCHEMA_TYPE[tr["kind"]]

    segments, shake = build_segments(pairs, pair_valid, shot_of_pair, ls, tx, ty, rot, dt, zooms, shots, v)

    frames_out = [
        {"t": r3(t_of(b)), "scale": r4(m.scale), "tx": r4(m.tx), "ty": r4(m.ty), "rot": r3(m.rot),
         "method": m.method, "inliers": m.inliers, "resid": r3(m.resid), "valid": bool(pair_valid[idx])}
        for idx, (a, b, m) in enumerate(pairs)
    ]
    invalid_share = 1 - float(pair_valid.mean()) if len(pair_valid) else 1.0
    if invalid_share > 0.4:
        notes.append(f"{invalid_share:.0%} of sampled steps had no reliable motion estimate (dark, flat or fast frames)")
    if prep_bounds and any(tr["source"] == "prep" for tr in transitions):
        notes.append("some prep shot boundaries showed no cut here; they are kept with confidence "
                     "'unconfirmed' and left out of the playbook block")

    hard_cuts = sum(1 for tr in transitions if tr["confidence"] == "high" and tr["tEnd"] - tr["tStart"] < 1.5 / v.fps)
    clean = []
    for tr in transitions:
        d = {k: tr[k] for k in ("atSec", "tStart", "tEnd", "kind", "type", "source", "confidence", "score") if k in tr}
        for k in ("direction",):
            if k in tr:
                d[k] = tr[k]
        d["atSec"], d["tStart"], d["tEnd"] = r3(d["atSec"]), r3(d["tStart"]), r3(d["tEnd"])
        clean.append(d)

    return {
        "tool": "camera_motion",
        "version": VERSION,
        "video": {"path": str(video_path), "fps": r3(v.fps), "frames": n, "durationSec": r3(duration),
                  "width": v.width, "height": v.height},
        "params": {"fps": args.fps, "sampleStepFrames": step, "analysisWidth": v.aw,
                   "maskCaptions": args.mask_captions if args.mask_captions in ("auto", "none") else "file",
                   "captionThreshold": args.caption_threshold},
        "mask": {"source": args.mask_captions,
                 "framesWithCaptionBoxes": masked_frames, "meanMaskedShare": r3(coverage)},
        "conventions": {
            "scale": "per-step scale > 1 means the picture grows (zoom in)",
            "tx_ty": "per-step shift of the picture centre, as a fraction of frame width/height; positive is right/down",
            "pan": "segment direction is the camera direction, the opposite of the picture's travel",
            "slide": "transition direction is the picture's travel, as editors name a slide",
            "hardCuts": "instantaneous cuts with high confidence, whatever motion surrounds them",
            "zoomScale": "scaleFrom/scaleTo are relative to the widest framing in the same shot",
        },
        "shots": [{k: s[k] for k in ("id", "tIn", "tOut")} for s in shots],
        "transitions": clean,
        "hardCuts": hard_cuts,
        "zoomEvents": [{k: (r3(val) if isinstance(val, float) else val) for k, val in z.items()} for z in zooms],
        "segments": segments,
        "shake": shake,
        "frames": frames_out,
        "notes": notes,
        **({"debug": {"D": [r3(x) for x in D], "Hd": [r3(x) for x in Hd], "luma": [r3(x) for x in lumas]}} if args.debug else {}),
    }


def motion_explained(i0, i1, reader: WindowReader, v: Video):
    """A change spike that frame-to-frame motion explains is a slide, a whip or a fast zoom, not a cut.

    Returns None when motion does not explain it (a real cut), {} when it is ordinary camera
    motion, or a transition dict for a slide or a zoom.
    """
    nat = reader.pair_motion(i0, i1)
    if not nat or sum(1 for _, m in nat if m.ok and m.resid <= GRADUAL_RESID) < 0.7 * len(nat):
        return None
    fast = lambda m: m.ok and (math.hypot(m.tx, m.ty) * v.fps >= 0.5 * WHIP_SPEED or abs(m.ls) * v.fps >= 0.5 * FAST_ZOOM_LN_PER_SEC)  # noqa: E731
    lim = int(round(1.0 * v.fps))
    a, b = i0, i1
    while a > max(0, i0 - lim):
        m = reader.pair_motion(a - 1, a)
        if not m or not fast(m[0][1]):
            break
        a -= 1
    while b < min(v.n - 1, i1 + lim):
        m = reader.pair_motion(b, b + 1)
        if not m or not fast(m[0][1]):
            break
        b += 1
    ms = [m for _, m in reader.pair_motion(a, b) if m.ok]
    sx, sy, sl = sum(m.tx for m in ms), sum(m.ty for m in ms), sum(m.ls for m in ms)
    tr = {"tStart": a / v.fps, "tEnd": b / v.fps, "atSec": 0.5 * (a + b) / v.fps, "i0": a, "i1": b,
          "source": "detected", "confidence": "medium"}
    if max(abs(sx), abs(sy)) >= 0.3:
        tr["kind"] = "slide"
        tr["direction"] = ("left" if sx < 0 else "right") if abs(sx) >= abs(sy) else ("up" if sy < 0 else "down")
        return tr
    if abs(sl) >= math.log(1.15):
        tr["kind"] = "zoom"
        tr["direction"] = "in" if sl > 0 else "out"
        return tr
    return {}


def classify_gradual(i0, i1, reader: WindowReader, thumbs, lumas, D, v: Video, tighten: bool = True):
    seg = D[i0 + 1 : i1 + 1]
    if tighten and len(seg):
        noise = float(np.median(seg)) * 0.35
        idx = np.where(seg > max(noise, 0.02))[0]
        if len(idx):
            i0, i1 = i0 + int(idx[0]), i0 + int(idx[-1]) + 1
    tr = {"tStart": i0 / v.fps, "tEnd": i1 / v.fps, "i0": i0, "i1": i1, "source": "detected", "confidence": "medium"}
    tr["atSec"] = 0.5 * (tr["tStart"] + tr["tEnd"])
    inner = lumas[i0 + 1 : i1]
    ends = (lumas[i0], lumas[i1])
    motions = [m for _, m in reader.pair_motion(i0, i1)]
    good = [m for m in motions if m.method != "none" and m.resid < 0.6]
    sum_ls = sum(m.ls for m in good)
    sum_tx = sum(m.tx for m in good)
    sum_ty = sum(m.ty for m in good)
    fast = [m for m in good if math.hypot(m.tx, m.ty) * v.fps >= WHIP_SPEED]
    if inner and min(inner) < 0.45 * min(ends) and min(inner) < 45:
        tr["kind"] = "fade-black"
    elif inner and max(inner) > max(ends) + 40 and max(inner) > 170:
        tr["kind"] = "fade-white"
    elif abs(sum_ls) >= math.log(1.15):
        tr["kind"] = "zoom"
        tr["direction"] = "in" if sum_ls > 0 else "out"
    elif max(abs(sum_tx), abs(sum_ty)) >= 0.3 and len(fast) >= max(1, 0.3 * len(motions)):
        tr["kind"] = "slide"
        if abs(sum_tx) >= abs(sum_ty):
            tr["direction"] = "left" if sum_tx < 0 else "right"
        else:
            tr["direction"] = "up" if sum_ty < 0 else "down"
    else:
        mids = [thumbs[k] for k in range(i0 + 1, i1)]
        if mids:
            alphas, res = blend_fit(thumbs[i0], thumbs[i1], mids)
            mono = np.mean(np.diff(alphas) <= 0.02) if len(alphas) > 1 else 1.0
            if float(np.median(res)) <= 0.45 and mono >= 0.7:
                tr["kind"] = "dissolve"
            else:
                tr["kind"] = "gradual"
                tr["confidence"] = "low"
        else:
            tr["kind"] = "gradual"
            tr["confidence"] = "low"
    tr["score"] = r3(float(D[i0 + 1 : i1 + 1].sum()))
    return tr


MERGE_PRIORITY = ["fade-black", "fade-white", "zoom", "slide", "whip", "dissolve", "glitch", "gradual", "jump-cut", "cut"]
CONF_RANK = {"high": 2, "medium": 1, "low": 0}


def merge_transitions(transitions: list[dict], v: Video) -> list[dict]:
    """One edit can trip several detectors (a fade through black is a spike plus a gradual run)."""
    out: list[dict] = []
    for tr in sorted(transitions, key=lambda x: x["tStart"]):
        prev = out[-1] if out else None
        if prev is not None and tr["tStart"] <= prev["tEnd"] + 0.15:
            keep = min((prev, tr), key=lambda x: MERGE_PRIORITY.index(x["kind"]))
            merged = dict(keep)
            merged["i0"], merged["i1"] = min(prev["i0"], tr["i0"]), max(prev["i1"], tr["i1"])
            if merged["i1"] - merged["i0"] > 1:
                merged["tStart"], merged["tEnd"] = merged["i0"] / v.fps, merged["i1"] / v.fps
                merged["atSec"] = 0.5 * (merged["tStart"] + merged["tEnd"])
            merged["confidence"] = max(prev["confidence"], tr["confidence"], key=lambda c: CONF_RANK.get(c, -1))
            out[-1] = merged
        else:
            out.append(tr)
    return out


def load_shot_bounds(path: Path) -> list[float]:
    try:
        d = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise InputError(f"cannot read shots file {path}: {e}") from e
    shots = d.get("shots", []) if isinstance(d, dict) else d
    try:
        tins = sorted(float(s["tIn"]) for s in shots)
    except (KeyError, TypeError, ValueError) as e:
        raise InputError(f"shots file {path} needs [{{tIn, tOut}}]") from e
    return [t for t in tins if t > 0]


def detect_zooms(pairs, valid, shot_of_pair, ls, shots, reader: WindowReader, v: Video):
    events = []
    for si, shot in enumerate(shots):
        idxs = [i for i in range(len(pairs)) if shot_of_pair[i] == si]
        if not idxs:
            continue
        vals = np.array([ls[i] if valid[i] else 0.0 for i in idxs])
        cum = np.concatenate([[0.0], np.cumsum(vals)])
        lmin = float(cum.min())
        runs, cur, sign, gap = [], [], 0, 0
        for j, x in enumerate(vals):
            s = 1 if x > 0 else -1
            if abs(x) >= ZOOM_STEP_LN and (not cur or s == sign):
                cur.append(j)
                sign, gap = s, 0
            elif cur and gap == 0 and abs(x) < ZOOM_STEP_LN and (x == 0 or (1 if x > 0 else -1) == sign):
                gap = 1
            else:
                if cur:
                    runs.append(cur)
                cur, gap = ([j], 0) if abs(x) >= ZOOM_STEP_LN else ([], 0)
                sign = s
        if cur:
            runs.append(cur)
        for run in runs:
            seg = vals[run[0] : run[-1] + 1]
            total = float(seg.sum())
            if abs(total) < ZOOM_MIN_LN or abs(total) / (np.abs(seg).sum() + 1e-9) < ZOOM_CONSISTENCY:
                continue
            a_idx, b_idx = idxs[run[0]], idxs[run[-1]]
            f0 = max(shot["i0"], pairs[a_idx][0] - (pairs[a_idx][1] - pairs[a_idx][0]))
            f1 = min(shot["i1"], pairs[b_idx][1] + (pairs[b_idx][1] - pairs[b_idx][0]))
            nat = reader.pair_motion(f0, f1)
            nls = np.array([m.ls if m.ok else 0.0 for _, m in nat])
            if len(nls) == 0 or abs(nls.sum()) < 0.5 * abs(total):
                nls = None
            if nls is not None:
                c = np.concatenate([[0.0], np.cumsum(nls)])
                delta = float(c[-1])
                # progress in linear scale, the way editors key a zoom
                p = (np.exp(c) - 1.0) / (math.exp(delta) - 1.0)
                frames_idx = np.arange(f0, f0 + len(c))
                half = int(np.argmax(p >= 0.5))
                low = np.where(p[: half + 1] <= 0.015)[0]
                start_j = int(low.max()) if len(low) else 0
                high = np.where(p[half:] >= 0.985)[0]
                end_j = half + int(high.min()) if len(high) else len(c) - 1
                t_start, t_end = frames_idx[start_j] / v.fps, frames_idx[end_j] / v.fps
                tt = frames_idx[start_j : end_j + 1] / v.fps
                pp = (p[start_j : end_j + 1] - p[start_j]) / max(p[end_j] - p[start_j], 1e-9)
                method = "native"
            else:
                t_start, t_end = pairs[a_idx][0] / v.fps, pairs[b_idx][1] / v.fps
                cc = np.concatenate([[0.0], np.cumsum(seg)])
                tt = np.array([pairs[a_idx][0]] + [pairs[i][1] for i in idxs[run[0] : run[-1] + 1]]) / v.fps
                pp = (np.exp(cc) - 1.0) / (math.exp(total) - 1.0)
                delta = total
                method = "sampled"
            dur = max(t_end - t_start, 1 / v.fps)
            base = float(cum[run[0]]) - lmin
            s_from = math.exp(base)
            s_to = s_from * math.exp(delta)
            events.append({
                "tStart": t_start, "tEnd": t_end, "durSec": dur,
                "direction": "in" if delta > 0 else "out",
                "factor": math.exp(delta), "scaleFrom": s_from, "scaleTo": s_to,
                "easing": easing_of(tt, pp, dur), "shot": shot["id"], "refined": method, "transition": False,
            })
    events.sort(key=lambda e: e["tStart"])
    return events


def build_segments(pairs, valid, shot_of_pair, ls, tx, ty, rot, dt, zooms, shots, v: Video):
    labels: list[str | None] = [None] * len(pairs)
    jitter_all, rot_all = [], []
    speed_x = np.zeros(len(pairs))
    speed_y = np.zeros(len(pairs))
    for si, _ in enumerate(shots):
        idxs = np.array([i for i in range(len(pairs)) if shot_of_pair[i] == si])
        if len(idxs) == 0:
            continue
        val = valid[idxs]
        sdt = float(np.median(dt[idxs]))
        k = max(3, int(round(0.5 / sdt)) | 1)
        vx = np.where(val, tx[idxs] / dt[idxs], 0.0)
        vy = np.where(val, ty[idxs] / dt[idxs], 0.0)
        svx, svy = moving_avg(vx, val, k), moving_avg(vy, val, k)
        speed_x[idxs], speed_y[idxs] = vx, vy
        # shake: how much the per-step shift and roll change from one step to the next.
        # A pan that starts or stops changes it once; a hand changes it every step.
        stx, sty, srt = tx[idxs], ty[idxs], rot[idxs]
        both = val[1:] & val[:-1]
        dj = np.zeros(len(idxs))
        dj[1:] = np.where(both, np.hypot(np.diff(stx), np.diff(sty)) + ROT_TO_SHIFT * np.abs(np.diff(srt)), 0.0)
        dval = np.zeros(len(idxs), bool)
        dval[1:] = both
        jit = np.array([
            float(np.median(dj[max(0, j - k // 2) : j + k // 2 + 1][dval[max(0, j - k // 2) : j + k // 2 + 1]]))
            if dval[max(0, j - k // 2) : j + k // 2 + 1].any() else 0.0
            for j in range(len(idxs))
        ])
        jitter_all.extend(dj[dval].tolist())
        rot_all.extend(np.diff(srt)[both].tolist())
        consistency_x = np.abs(svx) / (moving_avg(np.abs(vx), val, k) + 1e-9)
        consistency_y = np.abs(svy) / (moving_avg(np.abs(vy), val, k) + 1e-9)
        for j, i in enumerate(idxs):
            if not val[j]:
                continue
            a, b = pairs[i][0] / v.fps, pairs[i][1] / v.fps
            z = next((z for z in zooms if not z["transition"] and z["tStart"] - 1e-6 <= 0.5 * (a + b) <= z["tEnd"] + 1e-6), None)
            if z is not None:
                labels[i] = "zoom-in" if z["direction"] == "in" else "zoom-out"
            elif abs(vx[j]) >= PAN_SPEED and abs(vx[j]) >= abs(vy[j]) and abs(svx[j]) >= 0.5 * PAN_SPEED and consistency_x[j] >= 0.6:
                labels[i] = "pan"
            elif abs(vy[j]) >= PAN_SPEED and abs(svy[j]) >= 0.5 * PAN_SPEED and consistency_y[j] >= 0.6:
                labels[i] = "tilt"
            elif jit[j] >= SHAKE_STEP:
                labels[i] = "shake"
            else:
                labels[i] = "static"

    segs = []
    for i, (a, b, _) in enumerate(pairs):
        lab = labels[i]
        if lab is None:
            continue
        si = int(shot_of_pair[i])
        if segs and segs[-1]["kind"] == lab and segs[-1]["shot"] == si and abs(segs[-1]["i1"] - a) <= 1:
            segs[-1]["i1"] = b
            segs[-1]["pairs"].append(i)
        else:
            segs.append({"kind": lab, "shot": si, "i0": a, "i1": b, "pairs": [i]})
    changed = True
    while changed:
        changed = False
        for j, s in enumerate(segs):
            if (s["i1"] - s["i0"]) / v.fps >= MIN_SEGMENT_SEC or s["kind"].startswith("zoom"):
                continue
            nb = [o for o in (segs[j - 1] if j > 0 else None, segs[j + 1] if j + 1 < len(segs) else None)
                  if o is not None and o["shot"] == s["shot"] and not o["kind"].startswith("zoom")]
            if not nb:
                continue
            tgt = max(nb, key=lambda o: o["i1"] - o["i0"])
            tgt["i0"], tgt["i1"] = min(tgt["i0"], s["i0"]), max(tgt["i1"], s["i1"])
            tgt["pairs"] = sorted(tgt["pairs"] + s["pairs"])
            segs.pop(j)
            changed = True
            break
        for j in range(len(segs) - 1, 0, -1):
            a_, b_ = segs[j - 1], segs[j]
            if a_["kind"] == b_["kind"] and a_["shot"] == b_["shot"] and abs(a_["i1"] - b_["i0"]) <= 1:
                a_["i1"] = b_["i1"]
                a_["pairs"] += b_["pairs"]
                segs.pop(j)
                changed = True

    out = []
    for s in segs:
        ps = s["pairs"]
        d = {"tStart": r3(s["i0"] / v.fps), "tEnd": r3(s["i1"] / v.fps), "kind": s["kind"], "move": SCHEMA_MOVE[s["kind"]],
             "shot": shots[s["shot"]]["id"]}
        if s["kind"] in ("pan", "tilt"):
            vx = float(np.mean(speed_x[ps]))
            vy = float(np.mean(speed_y[ps]))
            if s["kind"] == "pan":
                d["direction"] = "right" if vx < 0 else "left"
                d["speed"] = r3(abs(vx))
            else:
                d["direction"] = "down" if vy < 0 else "up"
                d["speed"] = r3(abs(vy))
            d["travel"] = r3(abs(float(np.sum(tx[ps] if s["kind"] == "pan" else ty[ps]))))
        if s["kind"].startswith("zoom"):
            d["factor"] = r3(math.exp(float(np.sum(ls[ps]))))
        out.append(d)

    jit = np.array(jitter_all) if jitter_all else np.zeros(1)
    rj = np.array(rot_all) if rot_all else np.zeros(1)
    med = float(np.median(jit))
    level = "none" if med < SHAKE_STEP else ("low" if med < SHAKE_STEP * 3 else "high")
    shake = {
        "stepJitter": r4(med),
        "stepJitterP90": r4(float(np.percentile(jit, 90))),
        "px1080": r3(med * 1080),
        "rotationStepDeg": r3(float(np.median(np.abs(rj)))),
        "level": level,
        "note": "median change of the per-step picture shift between consecutive sampled steps "
                "(fraction of the frame, roll folded in), over valid steps of all shots",
    }
    return out, shake


# ---------------------------------------------------------------- beats and the playbook block


def load_beats(path: Path) -> list[dict]:
    try:
        d = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise InputError(f"cannot read beats file {path}: {e}") from e
    beats = d.get("beats", []) if isinstance(d, dict) else d
    out = []
    for b in beats:
        try:
            out.append({"id": str(b["id"]), "tIn": float(b["tIn"]), "tOut": float(b["tOut"])})
        except (KeyError, TypeError, ValueError) as e:
            raise InputError(f"beats file {path} needs [{{id, tIn, tOut}}]") from e
    if not out:
        raise InputError(f"beats file {path} has no beats")
    for b in out:
        if not b["id"].startswith("b") or not b["id"][1:].isdigit():
            raise InputError(f"beat id {b['id']!r} does not match ^b[0-9]+$")
    return sorted(out, key=lambda b: b["tIn"])


def key_time(t: float, beats: list[dict], snap: float = 0.05) -> dict:
    for b in beats:
        if abs(t - b["tIn"]) <= snap:
            return {"beat": b["id"], "offsetSec": 0.0}
    for b in beats:
        if b["tIn"] <= t < b["tOut"]:
            return {"beat": b["id"], "offsetSec": round(t - b["tIn"], 3)}
    if t < beats[0]["tIn"]:
        return {"beat": beats[0]["id"], "offsetSec": 0.0}
    last = beats[-1]
    return {"beat": last["id"], "offsetSec": round(max(0.0, t - last["tIn"]), 3)}


def playbook_block(result: dict, beats: list[dict]) -> dict:
    segs = result["segments"]
    overall: dict[str, float] = {}
    for s in segs:
        overall[s["move"]] = overall.get(s["move"], 0.0) + s["tEnd"] - s["tStart"]
    fallback = max(overall, key=overall.get) if overall else "static"
    snaps = [(z["tStart"], z["tEnd"]) for z in result["zoomEvents"] if z.get("easing") == "snap"]
    moves = []
    for b in beats:
        share: dict[str, float] = {}
        order: list[str] = []
        for s in segs:
            if s["kind"].startswith("zoom") and any(abs(s["tStart"] - a) < 0.05 and abs(s["tEnd"] - e) < 0.05 for a, e in snaps):
                continue
            ov = min(b["tOut"], s["tEnd"]) - max(b["tIn"], s["tStart"])
            if ov > 0:
                share[s["move"]] = share.get(s["move"], 0.0) + ov
                if s["move"] not in order:
                    order.append(s["move"])
        span = max(b["tOut"] - b["tIn"], 1e-9)
        picked = [m for m in order if m in ("push-in", "pull-out", "pan", "tilt") and share[m] >= MIN_SEGMENT_SEC]
        if share.get("handheld", 0.0) >= 0.4 * span:
            picked.append("handheld")
        if not picked:
            picked = [max(share, key=share.get) if share else fallback]
        moves.extend({"beat": b["id"], "move": m} for m in picked)
    zooms = [
        {"at": key_time(z["tStart"], beats), "scaleFrom": round(z["scaleFrom"], 3), "scaleTo": round(z["scaleTo"], 3),
         "durSec": round(z["durSec"], 3), "easing": z["easing"]}
        for z in result["zoomEvents"] if not z.get("transition")
    ]
    transitions = [
        {"at": key_time(tr["atSec"], beats), "type": tr["type"]}
        for tr in result["transitions"] if tr["confidence"] in ("high", "medium")
    ]
    return {
        "beats": [{"id": b["id"], "tIn": b["tIn"], "tOut": b["tOut"]} for b in beats],
        "camera": {"moves": moves, "zooms": zooms, "transitions": transitions},
        "source.reference.hardCuts": result["hardCuts"],
    }


# ---------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Measure cuts, transitions, zooms, pans, shake and static spans of one short video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("video", nargs="?", help="reference video")
    ap.add_argument("work_dir", nargs="?", help="output directory; camera.json is written here")
    ap.add_argument("--fps", type=float, default=10.0, help="motion sampling rate (default 10)")
    ap.add_argument("--width", type=int, default=360, help="analysis width in px (default 360)")
    ap.add_argument("--mask-captions", default="auto",
                    help="auto (find bright text), none, or a captions.json from caption_boxes.py")
    ap.add_argument("--caption-threshold", type=int, default=220, help="brightness for auto caption masking")
    ap.add_argument("--shots", help="prep.py shots.json; every boundary in it is checked")
    ap.add_argument("--beats", help="beats [{id, tIn, tOut}] to key the playbook block to")
    ap.add_argument("--rekey", help="existing camera.json to re-key with --beats, without decoding again")
    ap.add_argument("--json", action="store_true", help="also print the result to stdout")
    ap.add_argument("--debug", action="store_true", help="add per-frame change scores to camera.json")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        if args.rekey:
            if not args.beats:
                raise InputError("--rekey needs --beats")
            path = Path(args.rekey)
            try:
                result = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError) as e:
                raise InputError(f"cannot read {path}: {e}") from e
            result["playbook"] = playbook_block(result, load_beats(Path(args.beats)))
            path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            log(f"re-keyed {path} to {len(result['playbook']['beats'])} beats")
        else:
            if not args.video or not args.work_dir:
                raise InputError("need <video> <work_dir> (or --rekey camera.json --beats beats.json)")
            if args.fps <= 0 or args.width < 64:
                raise InputError("--fps must be > 0 and --width >= 64")
            video = Path(args.video)
            if not video.is_file():
                raise InputError(f"no such file: {video}")
            beats = load_beats(Path(args.beats)) if args.beats else None
            result = analyze(video, args)
            result["playbook"] = playbook_block(result, beats) if beats else None
            if beats is None:
                result["notes"].append("no --beats given; run again with --rekey camera.json --beats beats.json "
                                       "to build the playbook block")
            out = Path(args.work_dir)
            out.mkdir(parents=True, exist_ok=True)
            path = out / "camera.json"
            path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            z = [e for e in result["zoomEvents"] if not e["transition"]]
            log(f"{result['video']['durationSec']}s, {len(result['shots'])} shots, {len(result['transitions'])} transitions, "
                f"{len(z)} zooms, shake {result['shake']['level']} -> {path}")
    except InputError as e:
        log(f"error: {e}")
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
