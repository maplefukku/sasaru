#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy>=1.26,<3",
#     "opencv-python-headless>=4.9,<5",
# ]
# ///
"""テロップの箱を測り、playbook の captions[] の層を下書きする。

    uv run --script caption_boxes.py <video> <work_dir>
        [--threshold 220] [--color white|auto|#RRGGBB] [--step native|0.1]
        [--roi x,y,w,h] [--min-hold 0.15] [--min-contrast 90]
        [--beats beats.json] [--onsets onsets.json]
        [--ocr] [--ocr-lang jpn] [--no-face-filter] [--json]

書くもの
  work_dir/captions.json     フレームごとの箱、カード（出る秒と消える秒、中心、一行の高さ、段数、色、縁、影）、
                             字の無い区間、最後のカード、層の下書き（playbook.captions と evidence の断片）。文言は持たない。
  work_dir/source-text.json  読んだテロップの文言。--ocr のときだけ text が入る。ほかの鍵（文字起こしなど）は残し、
                             captions の鍵だけを置き換える。playbook には入れない。

手順
  1. --step の間隔で全体を見る。箱の組が変わった間だけ、元の fps で読み直す。出る秒と消える秒はフレーム単位。
     tIn は字が見え始めたフレーム（立ち上がりの途中を含む）、tOut は字が見えなくなった最初のフレーム。
     立ち上がりと消えの長さは fadeInSec、fadeOutSec に出し、0.2 秒以上なら motionIn、motionOut を fade にする。
  2. 箱が --min-hold 未満だけ消えても、カードは切れていないと見なす。--min-hold 未満のカードは捨てる。
  3. テロップでない白を外す。近くに暗い縁か地が無い白（顔のハイライト、枕、窓の中）、縁がなだらかな白（光のにじみ）、
     中まで塗りつぶした塊、縦の筋の無い塊を落とす。顔の矩形（OpenCV 同梱の Haar）の中の候補には、より強い縁の対比を求める。
  4. 一行の高さは行プロファイルで測る。白画素が行の最大の 10% に満たない端の行が、行の高さの 15% を超えて続くときだけ
     切る（ラテン文字のアセンダーとディセンダー）。和文はほぼ外接箱と同じになる。外接箱の値も bboxHeightRatio に出す。
  5. 層は、位置と色が揃い、時間が重ならないカードの組。層の中で 8% を超えて大きさが跳ぶ組を sizeGroups に分け、
     カード数の最も多い組を capHeightRatio、それより大きい組を emphasis.scale にする。

--beats は [{id, tIn, tOut}] か {"beats": [...]}。渡すと、カードの秒に {beat, offsetSec} を付け、層の beats を埋める。
--onsets は秒の配列か、start / t / tIn / time を持つ要素の配列（文字起こしの words など）。渡すと show と leadSec を測る。
--ocr はローカルの tesseract（Apache-2.0、tessdata も Apache-2.0）を呼ぶ。無ければ警告して字数は幅からの推定にする。

終了コード 0 成功、2 入力の誤り。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

CAPTIONS_SCHEMA = "sasaru-captions/1"
SOURCE_TEXT_SCHEMA = "sasaru-source-text/1"
CAP_PROFILE_FRACTION = 0.10
TAIL_FRACTION = 0.15
FADE_MIN_SEC = 0.2
RAMP_VISIBLE = 0.03
SHADOW_BELOW = 0.08
SHADOW_AROUND = 0.12
MIN_EDGE = 35
SIG_SIZE = (128, 24)


class InputError(Exception):
    pass


@dataclass
class Line:
    x0: int
    y0: int
    x1: int
    y1: int
    core_h: int

    @property
    def h(self) -> int:
        return self.y1 - self.y0


@dataclass
class Block:
    x0: int
    y0: int
    x1: int
    y1: int
    lines: list[Line]
    sig: np.ndarray
    mask: np.ndarray | None = None

    @property
    def w(self) -> int:
        return self.x1 - self.x0

    @property
    def h(self) -> int:
        return self.y1 - self.y0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Card:
    obs: list[tuple[int, Block]] = field(default_factory=list)
    first_miss: int | None = None
    f_in: int = 0
    f_out: int = 0
    style: dict | None = None
    ref: dict | None = None
    first_mask: Block | None = None
    last_mask: Block | None = None
    motion_in: str = "cut"
    motion_out: str = "cut"
    f_in_detected: int = 0
    f_out_detected: int = 0
    steps: int = 1
    fade_in: int = 0
    fade_out: int = 0
    text: str | None = None
    id: str = ""
    layer: str = ""

    @property
    def last_block(self) -> Block:
        return self.obs[-1][1]


def hexcolor(bgr) -> str:
    b, g, r = (int(round(float(v))) for v in bgr)
    if min(r, g, b) >= 240:
        return "#FFFFFF"
    if max(r, g, b) <= 15:
        return "#000000"
    return f"#{r:02X}{g:02X}{b:02X}"


def color_dist(a, b) -> float:
    return float(np.linalg.norm(np.asarray(a, float) - np.asarray(b, float)))


def hex_to_bgr(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], float)


def split_rows(sub: np.ndarray) -> list[tuple[int, int]]:
    prof = sub.sum(1)
    if prof.max() == 0:
        return []
    empty = prof <= max(1, 0.02 * prof.max())
    segs, start = [], None
    for i, e in enumerate(empty):
        if not e and start is None:
            start = i
        elif e and start is not None:
            segs.append([start, i])
            start = None
    if start is not None:
        segs.append([start, len(prof)])
    merged: list[list[int]] = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < 2:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    total = sub.shape[0]
    if len(merged) > 1 and any((b - a) < 0.3 * max(bb - aa for aa, bb in merged) for a, b in merged):
        return [(merged[0][0], merged[-1][1])] if total else []
    return [(a, b) for a, b in merged]


def core_height(crop: np.ndarray) -> int:
    prof = crop.sum(1)
    if prof.max() == 0:
        return 0
    any_rows = np.flatnonzero(prof >= max(1, 0.02 * prof.max()))
    top, bot = int(any_rows[0]), int(any_rows[-1])
    dense = np.flatnonzero(prof >= CAP_PROFILE_FRACTION * prof.max())
    full = bot - top + 1
    if dense[0] - top > TAIL_FRACTION * full:
        top = int(dense[0])
    if bot - dense[-1] > TAIL_FRACTION * full:
        bot = int(dense[-1])
    return bot - top + 1


def sig_of(crop: np.ndarray) -> np.ndarray:
    return cv2.resize(crop.astype(np.uint8) * 255, SIG_SIZE, interpolation=cv2.INTER_AREA) > 127


def sig_iou(a: np.ndarray, b: np.ndarray) -> float:
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 0.0


def box_iou(a: Block, b: Block) -> float:
    ix = max(0, min(a.x1, b.x1) - max(a.x0, b.x0))
    iy = max(0, min(a.y1, b.y1) - max(a.y0, b.y0))
    inter = ix * iy
    u = a.w * a.h + b.w * b.h - inter
    return inter / u if u else 0.0


class Analyzer:
    def __init__(self, W: int, H: int, args: argparse.Namespace):
        self.W, self.H = W, H
        self.thr = args.threshold
        self.min_contrast = args.min_contrast
        self.color = args.color
        self.target = hex_to_bgr(args.color) if args.color.startswith("#") else None
        self.kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (max(3, round(25 * W / 1080)), max(3, round(9 * H / 1920)))
        )
        r = max(3, round(0.016 * H))
        self.local_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2 * r + 1, 2 * r + 1))
        self.min_h = max(4, round(0.006 * H))
        self.max_h = round(0.2 * H)
        self.min_w = max(6, round(0.02 * W))
        self.roi_mask = None
        if args.roi_px:
            x0, y0, x1, y1 = args.roi_px
            self.roi_mask = np.zeros((H, W), bool)
            self.roi_mask[y0:y1, x0:x1] = True
        self.face = None
        if not args.no_face_filter:
            path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            if path.exists():
                c = cv2.CascadeClassifier(str(path))
                if not c.empty():
                    self.face = c

    def text_map(self, bgr: np.ndarray) -> np.ndarray:
        if self.color in ("white", "auto"):
            b, g, r = cv2.split(bgr)
            op = cv2.min if self.color == "white" else cv2.max
            return op(op(b, g), r)
        d = np.sqrt(((bgr.astype(np.float32) - self.target.astype(np.float32)) ** 2).sum(axis=2))
        return (255 - np.clip(d, 0, 255)).astype(np.uint8)

    def faces(self, bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
        scale = 360 / self.W
        small = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (360, max(1, round(self.H * scale))))
        small = cv2.equalizeHist(small)
        found = self.face.detectMultiScale(small, 1.1, 5, minSize=(40, 40))
        out = []
        for x, y, w, h in found:
            x0, y0 = int(x / scale), int(y / scale)
            x1, y1 = int((x + w) / scale), int((y + h) / scale)
            pw, ph = int(0.15 * (x1 - x0)), int(0.15 * (y1 - y0))
            out.append((x0 - pw, y0 - ph, x1 + pw, y1 + ph))
        return out

    def text_like(self, seg: np.ndarray, white: np.ndarray, edge: np.ndarray) -> bool:
        fill = seg.mean()
        if fill < 0.06 or fill > 0.85:
            return False
        if seg.sum() / max(1, white.sum()) < 0.75:
            return False
        rim = seg & ~(cv2.erode(seg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        if not rim.any() or np.median(edge[rim]) < MIN_EDGE:
            return False
        h = seg.shape[0]
        mid = seg[int(0.2 * h): max(int(0.2 * h) + 1, int(0.8 * h))].astype(np.int8)
        runs = (np.diff(mid, axis=1) == 1).sum(1) + mid[:, 0]
        return runs.mean() >= 1.2

    def ring_contrast(self, tmap: np.ndarray, x0, y0, seg) -> float:
        pad = 6
        H, W = tmap.shape
        X0, Y0 = max(0, x0 - pad), max(0, y0 - pad)
        X1, Y1 = min(W, x0 + seg.shape[1] + pad), min(H, y0 + seg.shape[0] + pad)
        m = np.zeros((Y1 - Y0, X1 - X0), np.uint8)
        m[y0 - Y0: y0 - Y0 + seg.shape[0], x0 - X0: x0 - X0 + seg.shape[1]] = seg
        outer = cv2.dilate(m, np.ones((9, 9), np.uint8)) > 0
        inner = cv2.dilate(m, np.ones((3, 3), np.uint8)) > 0
        ring = outer & ~inner
        crop = tmap[Y0:Y1, X0:X1]
        if not ring.any():
            return 0.0
        return float(np.median(crop[m > 0]) - np.median(crop[ring]))

    def analyze(self, bgr: np.ndarray, keep_mask: bool = False) -> list[Block]:
        tmap = self.text_map(bgr)
        white = tmap > self.thr
        if self.roi_mask is not None:
            white &= self.roi_mask
        if not white.any():
            return []
        low = cv2.erode(tmap, self.local_kernel)
        keep = white & ((tmap.astype(np.int16) - low) >= self.min_contrast)
        closed = cv2.morphologyEx(keep.astype(np.uint8), cv2.MORPH_CLOSE, self.kernel)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
        pieces = np.zeros(tmap.shape, bool)
        boxes = []
        for i in range(1, n):
            x, y, w, h, _ = stats[i]
            if h < self.min_h or h > 2 * self.max_h:
                continue
            sub = (labels[y: y + h, x: x + w] == i) & keep[y: y + h, x: x + w]
            for r0, r1 in split_rows(sub):
                seg = sub[r0:r1]
                cols = np.flatnonzero(seg.any(0))
                rows = np.flatnonzero(seg.any(1))
                if cols.size == 0:
                    continue
                seg = seg[rows[0]: rows[-1] + 1, cols[0]: cols[-1] + 1]
                X0, Y0 = x + int(cols[0]), y + r0 + int(rows[0])
                hh, ww = seg.shape
                if hh < self.min_h or hh > self.max_h:
                    continue
                pieces[Y0: Y0 + hh, X0: X0 + ww] |= seg
                boxes.append([X0, Y0, X0 + ww, Y0 + hh])
        if not boxes:
            return []
        faces = None
        edge = tmap - cv2.erode(tmap, np.ones((3, 3), np.uint8))
        acc = np.zeros(tmap.shape, bool)
        lines = []
        for x0, y0, x1, y1 in merge_rows(boxes):
            seg = pieces[y0:y1, x0:x1]
            if x1 - x0 < self.min_w or y1 - y0 > self.max_h:
                continue
            if not self.text_like(seg, white[y0:y1, x0:x1], edge[y0:y1, x0:x1]):
                continue
            if self.face is not None:
                if faces is None:
                    faces = self.faces(bgr)
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                if any(a <= cx <= c and b <= cy <= d for a, b, c, d in faces):
                    if self.ring_contrast(tmap, x0, y0, seg) < 120:
                        continue
            acc[y0:y1, x0:x1] |= seg
            lines.append([x0, y0, x1, y1])
        if not lines:
            return []
        boxes = lines
        blocks = []
        for group in group_blocks(boxes, self.W):
            bx0 = min(b[0] for b in group)
            by0 = min(b[1] for b in group)
            bx1 = max(b[2] for b in group)
            by1 = max(b[3] for b in group)
            crop = acc[by0:by1, bx0:bx1]
            lines = [
                Line(b[0], b[1], b[2], b[3], core_height(acc[b[1]: b[3], b[0]: b[2]]))
                for b in sorted(group, key=lambda b: b[1])
            ]
            blocks.append(Block(bx0, by0, bx1, by1, lines, sig_of(crop), crop.copy() if keep_mask else None))
        return blocks


def merge_rows(boxes: list[list[int]]) -> list[list[int]]:
    changed = True
    while changed:
        changed = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                ha, hb = a[3] - a[1], b[3] - b[1]
                vov = min(a[3], b[3]) - max(a[1], b[1])
                gap = max(a[0], b[0]) - min(a[2], b[2])
                big, small = (a, b) if ha >= hb else (b, a)
                tol = 0.1 * max(ha, hb)
                inside = small[1] >= big[1] - tol and small[3] <= big[3] + tol
                similar = max(ha, hb) <= 1.8 * min(ha, hb)
                if vov >= 0.5 * min(ha, hb) and gap <= 1.2 * max(ha, hb) and (similar or inside):
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    del boxes[j]
                    changed = True
                    break
            if changed:
                break
    return boxes


def group_blocks(boxes: list[list[int]], W: int) -> list[list[list[int]]]:
    parent = list(range(len(boxes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(boxes):
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            ha, hb = a[3] - a[1], b[3] - b[1]
            hov = min(a[2], b[2]) - max(a[0], b[0])
            dcx = abs((a[0] + a[2]) / 2 - (b[0] + b[2]) / 2)
            vgap = max(a[1], b[1]) - min(a[3], b[3])
            if (hov > 0 or dcx <= 0.1 * W) and vgap <= 0.9 * max(ha, hb) and max(ha, hb) <= 2.2 * min(ha, hb):
                parent[find(i)] = find(j)
    groups: dict[int, list] = {}
    for i, b in enumerate(boxes):
        groups.setdefault(find(i), []).append(b)
    return list(groups.values())


def same_card(a: Block, b: Block, W: int, H: int) -> bool:
    if len(a.lines) != len(b.lines):
        return False
    if abs(a.cx - b.cx) > 0.05 * W or abs(a.cy - b.cy) > 0.05 * H:
        return False
    rw, rh = b.w / a.w, b.h / a.h
    if not (0.6 < rw < 1.67 and 0.6 < rh < 1.67):
        return False
    return sig_iou(a.sig, b.sig) >= 0.65


def match(prev: list[Block], cur: list[Block], W: int, H: int) -> bool:
    if len(prev) != len(cur):
        return False
    used = set()
    for a in prev:
        hit = next((j for j, b in enumerate(cur) if j not in used and same_card(a, b, W, H)), None)
        if hit is None:
            return False
        used.add(hit)
    return True


class Video:
    def __init__(self, path: Path):
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise InputError(f"動画を開けない: {path}")
        self.path = path
        self.fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
        self.W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        self.n: int | None = None

    def frames(self, wanted=None):
        cap = cv2.VideoCapture(str(self.path))
        last = max(wanted) if wanted else None
        i = 0
        try:
            while True:
                if last is not None and i > last:
                    break
                if not cap.grab():
                    break
                if wanted is None or i in wanted:
                    ok, frame = cap.retrieve()
                    if ok:
                        yield i, frame
                i += 1
        finally:
            cap.release()
        if wanted is None:
            self.n = i


def stroke_shadow_plate(bgr: np.ndarray, block: Block, H: int, W: int) -> dict:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    crop = block.mask
    lh = float(np.median([ln.core_h for ln in block.lines])) or float(block.h)
    D = max(6, int(0.6 * lh))
    cols = np.flatnonzero(crop.any(0))
    tops = np.array([np.flatnonzero(crop[:, c])[0] for c in cols]) + block.y0
    bots = np.array([np.flatnonzero(crop[:, c])[-1] for c in cols]) + block.y0
    xs = cols + block.x0

    def profile(src, ys0, sign):
        out = []
        for d in range(1, D + 1):
            ys = ys0 + sign * d
            ok = (ys >= 0) & (ys < H)
            if not ok.any():
                out.append(None)
                continue
            out.append(np.median(src[ys[ok], xs[ok]], axis=0))
        return out

    top_c = profile(bgr.astype(np.float32), tops, -1)
    top_g = profile(gray, tops, -1)
    bot_g = profile(gray, bots, +1)
    core = cv2.erode(crop.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    if not core.any():
        core = crop
    region = bgr[block.y0: block.y1, block.x0: block.x1]
    core_bgr = np.median(region[core], axis=0)

    def mean_of(prof, lo, hi):
        vals = [prof[d - 1] for d in range(max(1, lo), min(D, hi) + 1) if prof[d - 1] is not None]
        return np.median(np.array(vals), axis=0) if vals else None

    far_lo, far_hi = int(0.45 * lh), int(0.6 * lh)
    far_c = mean_of(top_c, far_lo, far_hi)
    ring_c = mean_of(top_c, 2, 3)
    stroke = None
    sw = 0
    if far_c is not None and ring_c is not None:
        if color_dist(ring_c, far_c) > 35 and color_dist(ring_c, core_bgr) > 60:
            for d in range(2, D + 1):
                v = top_c[d - 1]
                if v is None or color_dist(v, ring_c) >= color_dist(v, far_c):
                    break
                sw = d
            stroke = {"color": hexcolor(ring_c), "px1080": round(sw * 1080 / W, 1)}

    near_lo, near_hi = sw + 1, sw + 1 + max(3, int(0.1 * lh))
    if near_hi >= far_lo:
        far_lo, far_hi = near_hi + 1, max(near_hi + 2, far_hi)
    tn, bn = mean_of(top_g, near_lo, near_hi), mean_of(bot_g, near_lo, near_hi)
    tf, bf = mean_of(top_g, far_lo, far_hi), mean_of(bot_g, far_lo, far_hi)
    below = around = 0.0
    shadow = False
    if None not in (tn, bn, tf, bf):
        d_n, d_f = (near_lo + near_hi) / 2, (far_lo + far_hi) / 2
        span = lh + 2 * d_f

        def expected(y):
            return float(tf + (bf - tf) * (y + d_f) / span)

        exp_b, exp_t = expected(lh + d_n), expected(-d_n)
        drop_b, drop_t = exp_b - float(bn), exp_t - float(tn)
        below = drop_b / max(exp_b, 20.0)
        around = min(drop_b, drop_t) / max((exp_b + exp_t) / 2, 20.0)
        shadow = (below >= SHADOW_BELOW and drop_b >= 3) or (around >= SHADOW_AROUND and min(drop_b, drop_t) >= 3)

    plate = "none"
    pz_lo, pz_hi = sw + max(2, int(0.1 * lh)), sw + max(3, int(0.3 * lh))
    tz = [top_c[d - 1] for d in range(pz_lo, min(D, pz_hi) + 1) if top_c[d - 1] is not None]
    if tz:
        zone = np.median(np.array(tz), axis=0)
        span = int(1.4 * lh)
        sides = []
        for x in (block.x0 - span, block.x1 + span):
            if 0 <= x < W:
                sides.append(np.median(bgr[block.y0: block.y1, x].astype(np.float32), axis=0))
        spread = float(np.array(tz).std(axis=0).max())
        if sides and spread < 12 and min(color_dist(zone, s) for s in sides) > 40 and color_dist(zone, core_bgr) > 60:
            plate = "box"

    dt = cv2.distanceTransform(crop.astype(np.uint8), cv2.DIST_L2, 3)
    ridge = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8))) & (dt >= 1.5)
    thickness = 2 * float(np.median(dt[ridge])) if ridge.any() else 0.0

    return {
        "color": hexcolor(core_bgr),
        "colorBgr": [round(float(v), 1) for v in core_bgr],
        "stroke": stroke,
        "shadow": bool(shadow),
        "shadowScore": {"below": round(below, 3), "around": round(around, 3)},
        "plate": plate,
        "thicknessRatio": round(thickness / lh, 3) if lh else None,
    }


def contrast_ref(block: Block, H: int, W: int) -> dict:
    pad = 6
    X0, Y0 = max(0, block.x0 - pad), max(0, block.y0 - pad)
    X1, Y1 = min(W, block.x1 + pad), min(H, block.y1 + pad)
    m = np.zeros((Y1 - Y0, X1 - X0), np.uint8)
    m[block.y0 - Y0: block.y1 - Y0, block.x0 - X0: block.x1 - X0] = block.mask
    core = cv2.erode(m, np.ones((3, 3), np.uint8)) > 0
    ring = (cv2.dilate(m, np.ones((9, 9), np.uint8)) > 0) & ~(cv2.dilate(m, np.ones((3, 3), np.uint8)) > 0)
    return {"box": (X0, Y0, X1, Y1), "core": core, "ring": ring}


def contrast(tmap: np.ndarray, ref: dict) -> float:
    X0, Y0, X1, Y1 = ref["box"]
    c = tmap[Y0:Y1, X0:X1].astype(np.float32)
    if not ref["core"].any() or not ref["ring"].any():
        return 0.0
    return float(c[ref["core"]].mean() - c[ref["ring"]].mean())


def run_ocr(block: Block, lang: str) -> str | None:
    img = np.where(block.mask, 0, 255).astype(np.uint8)
    lh = max(1, int(np.median([ln.core_h for ln in block.lines])))
    s = 64 / lh
    img = cv2.resize(img, (max(1, int(img.shape[1] * s)), max(1, int(img.shape[0] * s))), interpolation=cv2.INTER_AREA)
    img = cv2.copyMakeBorder(img, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255)
    ok, png = cv2.imencode(".png", img)
    if not ok:
        return None
    psm = "7" if len(block.lines) == 1 else "6"
    try:
        out = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", lang, "--psm", psm],
            input=png.tobytes(), capture_output=True, timeout=60, check=True,
        ).stdout.decode("utf-8", "replace")
    except (subprocess.SubprocessError, OSError):
        return None
    text = "\n".join(ln.strip() for ln in out.splitlines() if ln.strip())
    return re.sub(r"(?<=[^\x00-\x7f])[ \t]+(?=[^\x00-\x7f])", "", text)


def load_beats(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    beats = data.get("beats", data) if isinstance(data, dict) else data
    out = []
    for b in beats:
        out.append({"id": str(b["id"]), "tIn": float(b["tIn"]), "tOut": float(b["tOut"])})
    return sorted(out, key=lambda b: b["tIn"])


def load_onsets(path: Path) -> list[float]:
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        for key in ("onsets", "words", "segments"):
            if key in data:
                data = data[key]
                break
    out = []
    for item in data:
        if isinstance(item, (int, float)):
            out.append(float(item))
        elif isinstance(item, dict):
            for key in ("start", "t", "tIn", "time"):
                if key in item:
                    out.append(float(item[key]))
                    break
    return sorted(out)


def beat_at(beats: list[dict], t: float) -> dict | None:
    if not beats:
        return None
    for i, b in enumerate(beats):
        if b["tIn"] <= t < b["tOut"] or (i == len(beats) - 1 and t <= b["tOut"] + 1e-6):
            return {"beat": b["id"], "offsetSec": round(max(0.0, t - b["tIn"]), 3)}
    return None


def parse_roi(s: str, W: int, H: int) -> tuple[int, int, int, int]:
    try:
        x, y, w, h = (float(v) for v in s.split(","))
    except ValueError as e:
        raise InputError(f"--roi は x,y,w,h（画面比）: {s}") from e
    if not (0 <= x < 1 and 0 <= y < 1 and 0 < w <= 1 and 0 < h <= 1):
        raise InputError(f"--roi は 0 から 1 の画面比: {s}")
    return int(x * W), int(y * H), min(W, int((x + w) * W)), min(H, int((y + h) * H))


def measure(args: argparse.Namespace) -> dict:
    video = Video(args.video)
    W, H, fps = video.W, video.H, video.fps
    args.roi_px = parse_roi(args.roi, W, H) if args.roi else None
    an = Analyzer(W, H, args)
    warnings: list[str] = []
    if an.face is None and not args.no_face_filter:
        warnings.append("顔の検出器を読めなかった。顔の中の候補にも通常の基準だけを当てた")
    k = 1 if args.step == "native" else max(1, round(float(args.step) * fps))

    frames: dict[int, list[Block]] = {}
    last_frame = None
    for i, frame in video.frames():
        last_frame = (i, frame)
        if i % k == 0:
            frames[i] = an.analyze(frame)
    n = video.n or 0
    if n == 0:
        raise InputError("フレームを一枚も読めなかった")
    if last_frame and last_frame[0] not in frames:
        frames[last_frame[0]] = an.analyze(last_frame[1])

    coarse = sorted(frames)
    pre, post = round(0.7 * fps), round(0.5 * fps)
    dense: set[int] = set()
    for p, c in zip(coarse, coarse[1:]):
        if not match(frames[p], frames[c], W, H):
            dense.update(range(max(0, p - pre), min(n, c + post + 1)))
    dense -= set(frames)
    if dense:
        for i, frame in video.frames(dense):
            frames[i] = an.analyze(frame)

    min_hold_f = max(1, round(args.min_hold * fps))
    active: list[Card] = []
    done: list[Card] = []
    for f in sorted(frames):
        blocks = list(frames[f])
        for card in active:
            hit = next((b for b in blocks if same_card(card.last_block, b, W, H)), None)
            if hit is not None:
                card.obs.append((f, hit))
                card.first_miss = None
                blocks.remove(hit)
            elif card.first_miss is None:
                card.first_miss = f
        for card in [c for c in active if c.first_miss is not None and f - c.first_miss >= min_hold_f]:
            card.f_out = card.first_miss
            active.remove(card)
            done.append(card)
        for b in blocks:
            active.append(Card(obs=[(f, b)]))
    for card in active:
        card.f_out = card.first_miss if card.first_miss is not None else n
        done.append(card)
    cards = []
    for c in done:
        c.f_in = c.obs[0][0]
        c.f_in_detected, c.f_out_detected = c.f_in, c.f_out
        if c.f_out - c.f_in >= min_hold_f:
            cards.append(c)
    cards.sort(key=lambda c: (c.f_in, c.obs[0][1].cy))

    def geo(c: Card) -> dict:
        bs = [b for _, b in c.obs]
        return {
            "cx": float(np.median([b.cx for b in bs])) / W,
            "cy": float(np.median([b.cy for b in bs])) / H,
            "w": float(np.median([b.w for b in bs])) / W,
            "h": float(np.median([b.h for b in bs])) / H,
            "x0": float(np.median([b.x0 for b in bs])) / W,
            "x1": float(np.median([b.x1 for b in bs])) / W,
            "lines": int(np.bincount([len(b.lines) for b in bs]).argmax()),
        }

    geos = {id(c): geo(c) for c in cards}

    chain_pairs = []
    for a in cards:
        for b in cards:
            if b is a or not (0 <= b.f_in - a.f_out <= 1):
                continue
            ga, gb = geos[id(a)], geos[id(b)]
            if (
                ga["lines"] == gb["lines"]
                and abs(ga["cy"] - gb["cy"]) <= 0.015
                and 0.85 <= gb["h"] / ga["h"] <= 1.18
                and gb["w"] > 1.05 * ga["w"]
            ):
                chain_pairs.append((a, b))

    want: dict[int, list] = {}
    for c in cards:
        mid_f = c.obs[len(c.obs) // 2][0]
        want.setdefault(mid_f, []).append(("mid", c))
    for a, b in chain_pairs:
        want.setdefault(a.obs[-1][0], []).append(("last", a))
        want.setdefault(b.obs[0][0], []).append(("first", b))

    def pick(blocks: list[Block], target: Block) -> Block | None:
        best = max(blocks, key=lambda b: box_iou(b, target), default=None)
        return best if best is not None and box_iou(best, target) > 0.3 else None

    ocr_ok = False
    if args.ocr:
        if shutil.which("tesseract"):
            ocr_ok = True
        else:
            warnings.append("--ocr を指定したが tesseract が無い。字数は幅からの推定にした")
    for i, frame in video.frames(set(want)):
        blocks = an.analyze(frame, keep_mask=True)
        tmap = an.text_map(frame)
        for kind, c in want[i]:
            obs_block = next(b for f, b in c.obs if f == i)
            b = pick(blocks, obs_block)
            if b is None:
                continue
            if kind == "mid":
                c.style = stroke_shadow_plate(frame, b, H, W)
                c.ref = contrast_ref(b, H, W)
                c.ref["plateau"] = contrast(tmap, c.ref)
                if ocr_ok:
                    c.text = run_ocr(b, args.ocr_lang)
            elif kind == "last":
                c.last_mask = b
            else:
                c.first_mask = b

    links = {}
    for a, b in chain_pairs:
        if a.last_mask is None or b.first_mask is None:
            continue
        am, bm = a.last_mask, b.first_mask
        canvas_b = np.zeros((H, W), np.uint8)
        canvas_b[bm.y0: bm.y1, bm.x0: bm.x1] = bm.mask
        canvas_b = cv2.dilate(canvas_b, np.ones((5, 5), np.uint8)) > 0
        covered = canvas_b[am.y0: am.y1, am.x0: am.x1][am.mask].mean() if am.mask.any() else 0
        if covered >= 0.9 and id(a) not in links:
            links[id(a)] = b

    for c in cards:
        bs = c.obs
        g = geos[id(c)]
        early = [b for f, b in bs if f < c.f_in + round(0.4 * fps)]
        late = [b for f, b in bs if f > bs[-1][0] - round(0.4 * fps)]
        ph, pcy = g["h"] * H, g["cy"] * H
        if len(early) >= 2:
            r0 = early[0].h / ph
            peak = max(b.h for b in early) / ph
            if r0 < 0.92:
                c.motion_in = "pop" if peak > 1.04 else "scale-in"
            elif r0 > 1.08:
                c.motion_in = "pop"
            elif (early[0].cy - pcy) / H > 0.008:
                c.motion_in = "slide-up"
        if len(late) >= 2:
            if abs(late[-1].cy - pcy) / H > 0.008:
                c.motion_out = "slide"
            elif abs(late[-1].h / ph - 1) > 0.08:
                c.motion_out = "other"

    ramp_want: dict[int, list] = {}
    for c in cards:
        if c.ref is None or c.ref["plateau"] <= 0:
            continue
        for f in range(max(0, c.f_in - pre), min(n, c.f_in + post)):
            ramp_want.setdefault(f, []).append(c)
        for f in range(max(0, c.obs[-1][0] - post), min(n, c.f_out + pre)):
            ramp_want.setdefault(f, []).append(c)
    ramps: dict[int, dict[int, float]] = {}
    if ramp_want:
        for i, frame in video.frames(set(ramp_want)):
            tmap = an.text_map(frame)
            for c in ramp_want[i]:
                ramps.setdefault(id(c), {})[i] = contrast(tmap, c.ref) / c.ref["plateau"]

    def overlaps(a: Card, b: Card) -> bool:
        ga, gb = geos[id(a)], geos[id(b)]
        return min(ga["x1"], gb["x1"]) > max(ga["x0"], gb["x0"]) and abs(ga["cy"] - gb["cy"]) < (ga["h"] + gb["h"]) / 2

    fade_min = max(2, round(FADE_MIN_SEC * fps))
    for c in cards:
        r = ramps.get(id(c))
        if not r:
            continue
        if c.motion_in == "cut":
            guard = max([o.f_out for o in cards if o is not c and o.f_out <= c.f_in and overlaps(o, c)], default=0)
            start, f = c.f_in, c.f_in - 1
            while (f >= max(guard, c.f_in - pre) and r.get(f, 0) >= RAMP_VISIBLE
                   and r.get(f, 0) <= r.get(f + 1, 1) + 0.02):
                start, f = f, f - 1
            after = 0
            for f in range(c.f_in, c.f_in + post):
                if r.get(f, 1) >= 0.85:
                    break
                after += 1
            c.fade_in = (c.f_in - start) + after
            c.f_in = start
            if c.fade_in >= fade_min:
                c.motion_in = "fade"
        if c.motion_out == "cut" and c.f_out < n:
            guard = min([o.f_in for o in cards if o is not c and o.f_in >= c.f_out and overlaps(o, c)], default=n)
            last = c.obs[-1][0]
            end, f = last, last + 1
            while (f < min(guard, c.f_out + pre) and r.get(f, 0) >= RAMP_VISIBLE
                   and r.get(f, 0) <= r.get(f - 1, 1) + 0.02):
                end, f = f, f + 1
            before = 0
            for f in range(last, last - post, -1):
                if r.get(f, 1) >= 0.85:
                    break
                before += 1
            c.fade_out = (end - last) + before
            c.f_out = max(c.f_out, end + 1)
            if c.fade_out >= fade_min:
                c.motion_out = "fade"

    merged: list[Card] = []
    consumed = set()
    for c in cards:
        if id(c) in consumed:
            continue
        chain = [c]
        while id(chain[-1]) in links:
            chain.append(links[id(chain[-1])])
        if len(chain) >= 2:
            last = chain[-1]
            for x in chain:
                consumed.add(id(x))
            steps = [geos[id(chain[i + 1])]["w"] - geos[id(chain[i])]["w"] for i in range(len(chain) - 1)]
            step_px = float(np.median(steps)) * W
            last_h = geos[id(last)]["h"] * H
            last.motion_in = "typewriter" if step_px < 1.6 * last_h else "word-by-word"
            last.f_in, last.f_in_detected = chain[0].f_in, chain[0].f_in_detected
            last.steps = len(chain)
            last.obs = [o for x in chain for o in x.obs]
            merged.append(last)
        else:
            merged.append(c)
    cards = sorted(merged, key=lambda c: (c.f_in, geos[id(c)]["cy"]))

    beats = load_beats(args.beats) if args.beats else []
    onsets = load_onsets(args.onsets) if args.onsets else []
    duration = n / fps

    card_out = []
    for idx, c in enumerate(cards, 1):
        c.id = f"k{idx:03d}"
        g = geos[id(c)]
        tail = [b for f, b in c.obs if f >= c.obs[len(c.obs) // 2][0]] if c.steps > 1 else [b for _, b in c.obs]
        line_core = [float(np.median([ln.core_h for ln in b.lines])) for b in tail]
        line_bbox = [float(np.median([ln.h for ln in b.lines])) for b in tail]
        per_line = [round(float(np.median([b.lines[j].core_h for b in tail if len(b.lines) > j])) / H, 4)
                    for j in range(max(len(b.lines) for b in tail))]
        cap = float(np.median(line_core)) / H
        widths = [ln.x1 - ln.x0 for b in tail for ln in b.lines]
        heights = [ln.core_h for b in tail for ln in b.lines]
        est = sum(max(1, round(wd / (1.1 * ht))) for wd, ht in zip(widths, heights) if ht) // max(1, len(tail))
        chars = len(re.sub(r"\s", "", c.text)) if c.text else None
        t_in, t_out = round(c.f_in / fps, 3), round(c.f_out / fps, 3)
        st = c.style or {}
        card_out.append({
            "id": c.id,
            "tIn": t_in,
            "tOut": t_out,
            "frameIn": c.f_in,
            "frameOut": c.f_out,
            "detectedIn": round(c.f_in_detected / fps, 3),
            "detectedOut": round(c.f_out_detected / fps, 3),
            "at": beat_at(beats, t_in),
            "until": beat_at(beats, t_out),
            "cx": round(g["cx"], 4),
            "cy": round(g["cy"], 4),
            "w": round(g["w"], 4),
            "h": round(g["h"], 4),
            "left": round(g["x0"], 4),
            "right": round(g["x1"], 4),
            "lines": g["lines"],
            "capHeightRatio": round(cap, 4),
            "bboxHeightRatio": round(float(np.median(line_bbox)) / H, 4),
            "lineHeights": per_line,
            "color": st.get("color"),
            "stroke": st.get("stroke"),
            "shadow": st.get("shadow"),
            "shadowScore": st.get("shadowScore"),
            "plate": st.get("plate"),
            "thicknessRatio": st.get("thicknessRatio"),
            "motionIn": c.motion_in,
            "motionOut": c.motion_out,
            "fadeInSec": round(c.fade_in / fps, 3),
            "fadeOutSec": round(c.fade_out / fps, 3),
            "steps": c.steps,
            "chars": chars,
            "charsEstimate": int(est),
            "holdsToEnd": c.f_out >= n,
        })

    layers = build_layers(card_out, fps, duration, beats, onsets, bool(ocr_ok), args.color, warnings)
    for lay in layers:
        for cid in lay["_cards"]:
            next(x for x in card_out if x["id"] == cid)["layer"] = lay["id"]
    for co, c in zip(card_out, cards):
        c.layer = co.get("layer", "")

    frame_out = []
    owner = {}
    for c in cards:
        for f, b in c.obs:
            owner[(f, id(b))] = c.id
    for f in sorted(frames):
        boxes = []
        for b in frames[f]:
            boxes.append({
                "cx": round(b.cx / W, 4), "cy": round(b.cy / H, 4),
                "w": round(b.w / W, 4), "h": round(b.h / H, 4),
                "lines": len(b.lines), "card": owner.get((f, id(b))),
            })
        frame_out.append({"t": round(f / fps, 3), "frame": f, "boxes": boxes})

    cover = np.zeros(n, bool)
    lines_at = np.zeros(n, int)
    cards_at = np.zeros(n, int)
    for co in card_out:
        cover[co["frameIn"]: co["frameOut"]] = True
        lines_at[co["frameIn"]: co["frameOut"]] += co["lines"]
        cards_at[co["frameIn"]: co["frameOut"]] += 1
    gaps, start = [], None
    for i in range(n + 1):
        free = i < n and not cover[i]
        if free and start is None:
            start = i
        elif not free and start is not None:
            gaps.append({"tIn": round(start / fps, 3), "tOut": round(i / fps, 3), "frames": i - start})
            start = None

    last = max(card_out, key=lambda x: (x["frameOut"], x["frameIn"]), default=None)
    playbook_captions = [{k: v for k, v in lay.items() if not k.startswith("_")} for lay in layers]
    evidence = {"measured": [], "inferred": [], "unmeasured": []}
    for lay in layers:
        for kind in evidence:
            evidence[kind] += [f"captions.{lay['id']}.{p}" for p in lay["_evidence"][kind]]

    result = {
        "schema": CAPTIONS_SCHEMA,
        "video": {"file": args.video.name, "width": W, "height": H, "fps": round(fps, 3), "frames": n,
                  "durationSec": round(duration, 3)},
        "params": {
            "threshold": args.threshold, "color": args.color, "step": args.step, "minHoldSec": args.min_hold,
            "minContrast": args.min_contrast, "faceFilter": an.face is not None, "ocr": bool(ocr_ok),
            "ocrLang": args.ocr_lang if ocr_ok else None,
        },
        "threshold": args.threshold,
        "roi": list(args.roi_px) if args.roi_px else None,
        "capHeightMethod": f"row-profile: rows with white >= {CAP_PROFILE_FRACTION:.0%} of the line's peak row; "
                           "bboxHeightRatio is the bounding box",
        "firstFrameHasText": bool(cover[0]) if n else False,
        "maxSimultaneousCards": int(cards_at.max()) if n else 0,
        "maxSimultaneousLines": int(lines_at.max()) if n else 0,
        "cards": card_out,
        "noCaption": gaps,
        "lastCard": {
            "card": last["id"] if last else None,
            "holdsToEnd": bool(last and last["holdsToEnd"]),
            "lastFrame": n - 1,
        },
        "colorCandidates": color_candidates(card_out),
        "layers": [{"id": lay["id"], "cards": lay["_cards"], "sizeGroups": lay["_sizes"]} for lay in layers],
        "playbook": {"captions": playbook_captions, "evidence": evidence},
        "frames": frame_out,
        "warnings": warnings,
    }
    texts = [{"card": co["id"], "layer": co.get("layer"), "tIn": co["tIn"], "tOut": co["tOut"],
              "text": c.text, "method": "tesseract" if ocr_ok else None} for co, c in zip(card_out, cards)]
    return {"captions": result, "texts": texts}


def color_candidates(cards: list[dict]) -> list[dict]:
    groups: list[dict] = []
    for c in cards:
        if not c["color"]:
            continue
        bgr = hex_to_bgr(c["color"])
        home = next((g for g in groups if color_dist(g["bgr"], bgr) <= 40), None)
        if home is None:
            home = {"bgr": bgr, "colors": [], "cards": [], "seconds": 0.0}
            groups.append(home)
        home["colors"].append(c["color"])
        home["cards"].append(c["id"])
        home["seconds"] += c["tOut"] - c["tIn"]
    groups.sort(key=lambda g: -g["seconds"])
    return [{"color": max(set(g["colors"]), key=g["colors"].count), "cards": g["cards"],
             "seconds": round(g["seconds"], 3)} for g in groups]


def build_layers(cards: list[dict], fps: float, duration: float, beats: list[dict], onsets: list[float],
                 ocr: bool, color_mode: str, warnings: list[str]) -> list[dict]:
    groups: list[list[dict]] = []
    for c in sorted(cards, key=lambda x: x["tIn"]):
        home = None
        for g in groups:
            cy = float(np.median([x["cy"] for x in g]))
            cx = float(np.median([x["cx"] for x in g]))
            col = g[0]["color"]
            if abs(c["cy"] - cy) > 0.06 or abs(c["cx"] - cx) > 0.2:
                continue
            if col and c["color"] and color_dist(hex_to_bgr(col), hex_to_bgr(c["color"])) > 60:
                continue
            if any(x["tIn"] < c["tOut"] and c["tIn"] < x["tOut"] for x in g):
                continue
            home = g
            break
        if home is None:
            groups.append([c])
        else:
            home.append(c)
    groups.sort(key=lambda g: -sum(x["tOut"] - x["tIn"] for x in g))
    frame = 1 / fps
    layers = []
    for li, g in enumerate(groups, 1):
        g.sort(key=lambda x: x["tIn"])
        ev = {"measured": [], "inferred": [], "unmeasured": []}
        hs = sorted(x["capHeightRatio"] for x in g)
        sizes: list[list[float]] = []
        for h in hs:
            if sizes and h <= sizes[-1][-1] * 1.08:
                sizes[-1].append(h)
            else:
                sizes.append([h])
        base = max(sizes, key=lambda s: (len(s), -s[0]))
        base_h = float(np.median(base))
        bigger = [s for s in sizes if float(np.median(s)) > base_h * 1.12]
        emphasis = None
        if bigger:
            top = max(bigger, key=lambda s: (len(s), float(np.median(s))))
            emphasis = {"scale": round(float(np.median(top)) / base_h, 2), "color": None}
            ecolors = [x["color"] for x in g if x["capHeightRatio"] in top and x["color"]]
            bcolors = [x["color"] for x in g if x["capHeightRatio"] in base and x["color"]]
            if ecolors and bcolors and color_dist(hex_to_bgr(ecolors[0]), hex_to_bgr(bcolors[0])) > 60:
                emphasis["color"] = ecolors[0]
            ev["measured"].append("emphasis.scale")
            (ev["unmeasured"] if color_mode == "white" else ev["measured"]).append("emphasis.color")
        else:
            ev["measured"].append("emphasis")
        base_cards = [x for x in g if x["capHeightRatio"] in base]

        def mode(vals, default):
            vals = [v for v in vals if v is not None]
            return max(set(vals), key=vals.count) if vals else default

        color = mode([x["color"] for x in base_cards], "#FFFFFF")
        strokes = [x["stroke"] for x in base_cards]
        stroke = None
        if sum(s is not None for s in strokes) * 2 > len(strokes):
            ss = [s for s in strokes if s]
            stroke = {"color": mode([s["color"] for s in ss], "#000000"),
                      "px1080": round(float(np.median([s["px1080"] for s in ss])), 1)}
        shadow = sum(bool(x["shadow"]) for x in base_cards) * 2 > len(base_cards)
        plate = mode([x["plate"] for x in base_cards], "none")
        cx = float(np.median([x["cx"] for x in g]))
        cy = float(np.median([x["cy"] for x in g]))
        ws = [x["w"] for x in g]
        if len(g) >= 3 and max(ws) > 1.3 * min(ws):
            spread = {"left": np.std([x["left"] for x in g]), "center": np.std([x["cx"] for x in g]),
                      "right": np.std([x["right"] for x in g])}
            align = min(spread, key=spread.get)
        else:
            align = "center" if abs(cx - 0.5) < 0.06 else ("left" if cx < 0.5 else "right")
        lines_max = max(x["lines"] for x in g)
        counts = [x["chars"] if ocr and x["chars"] else x["charsEstimate"] for x in g]
        counts = [max(1, int(v)) for v in counts]
        thick = [x["thicknessRatio"] for x in base_cards if x["thicknessRatio"]]
        tr = float(np.median(thick)) if thick else 0.0
        if tr >= 0.135:
            font = {"class": "extra-bold-gothic", "weight": 900}
        elif tr >= 0.10:
            font = {"class": "bold-gothic", "weight": 700}
        elif tr >= 0.075:
            font = {"class": "other", "weight": 500}
        else:
            font = {"class": "thin-sans", "weight": 300}
        holds = [x["tOut"] - x["tIn"] for x in g]
        span = sum(holds)
        if len(g) == 1 and span >= 0.8 * duration:
            role = "label"
        elif base_h >= 0.035:
            role = "headline"
        else:
            role = "subtitle"
        if lines_max >= 2:
            unit = "card"
        elif max(counts) <= 3 and float(np.median(holds)) < 0.7:
            unit = "word"
        elif max(counts) > 14:
            unit = "line"
        else:
            unit = "phrase"

        motion_in = mode([x["motionIn"] for x in g], "cut")
        motion_out = mode([x["motionOut"] for x in g[:-1]] or [g[-1]["motionOut"]], "cut")
        show, lead = "onset", None
        if onsets:
            leads = []
            for x in g:
                near = min(onsets, key=lambda o: abs(o - x["tIn"]))
                if abs(near - x["tIn"]) <= 0.5:
                    leads.append(near - x["tIn"])
            if len(leads) * 10 >= 6 * len(g):
                med = float(np.median(leads))
                if med > 1.5 * frame:
                    show, lead = "before-onset", round(med, 3)
                ev["measured"] += ["show", "leadSec"]
            else:
                ev["unmeasured"] += ["show", "leadSec"]
        elif beats and sum(any(abs(x["tIn"] - b["tIn"]) <= 1.5 * frame for b in beats) for x in g) * 10 >= 6 * len(g):
            show = "beat-start"
            ev["measured"] += ["show", "leadSec"]
        else:
            ev["unmeasured"] += ["show", "leadSec"]

        nexts = [g[i + 1]["tIn"] - g[i]["tOut"] for i in range(len(g) - 1)]
        if nexts and sum(abs(d) <= 1.5 * frame for d in nexts) * 10 >= 7 * len(nexts):
            hide = "next-card"
            ev["measured"].append("hide")
        elif beats and any(abs(x["tOut"] - b["tOut"]) <= 1.5 * frame for x in g for b in beats):
            hide = "beat-end"
            ev["inferred"].append("hide")
        else:
            hide = "phrase-end"
            ev["inferred"].append("hide")

        if beats:
            used = [b["id"] for b in beats if any(x["tIn"] < b["tOut"] and b["tIn"] < x["tOut"] for x in g)]
            layer_beats = [] if len(used) == len(beats) else used
            ev["measured"].append("beats")
        else:
            layer_beats = []
            ev["unmeasured"].append("beats")

        ev["measured"] += ["capHeightRatio", "color", "stroke", "shadow", "position", "linesMax", "motionIn",
                           "motionOut", "minHoldSec", "lastCard"]
        ev["inferred"] += ["role", "unit", "writingMode", "font", "plate"]
        (ev["measured"] if ocr else ev["inferred"]).append("charsPerCard")

        layers.append({
            "id": f"c{li}",
            "role": role,
            "beats": layer_beats,
            "unit": unit,
            "writingMode": "horizontal",
            "font": font,
            "capHeightRatio": round(base_h, 4),
            "emphasis": emphasis,
            "color": color,
            "stroke": stroke,
            "shadow": bool(shadow),
            "plate": plate,
            "position": {"cx": round(cx, 3), "cy": round(cy, 3), "align": align},
            "linesMax": int(lines_max),
            "charsPerCard": {"min": int(min(counts)), "max": int(max(counts))},
            "motionIn": motion_in,
            "motionOut": motion_out,
            "show": show,
            "leadSec": lead,
            "hide": hide,
            "minHoldSec": round(min(holds), 3),
            "lastCard": "hold-to-end" if g[-1]["tOut"] >= duration - frame / 2 else "phrase-end",
            "_cards": [x["id"] for x in g],
            "_sizes": [{"capHeightRatio": round(float(np.median(s)), 4), "cards": len(s)} for s in sizes],
            "_evidence": ev,
        })
    if any(c.get("thicknessRatio") is None for c in cards):
        warnings.append("一部のカードで字の太さを測れなかった")
    return layers


def write_source_text(path: Path, video_name: str, texts: list[dict]) -> None:
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            data = {}
    data.setdefault("schema", SOURCE_TEXT_SCHEMA)
    data.setdefault("video", video_name)
    data["captions"] = texts
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="テロップの箱を測り、playbook の captions[] の層を下書きする")
    p.add_argument("video", type=Path)
    p.add_argument("work_dir", type=Path)
    p.add_argument("--threshold", type=int, default=220, help="字の画素とみなす下限（white は最小チャンネル）")
    p.add_argument("--color", default="white", help="white、auto、または #RRGGBB")
    p.add_argument("--step", default="0.1", help="native か、粗く見る間隔の秒")
    p.add_argument("--roi", default=None, help="x,y,w,h（画面比）。この中だけを見る")
    p.add_argument("--min-hold", type=float, default=0.15)
    p.add_argument("--min-contrast", type=int, default=90, help="字の画素と近くの暗い画素の差の下限")
    p.add_argument("--beats", type=Path, default=None)
    p.add_argument("--onsets", type=Path, default=None)
    p.add_argument("--ocr", action="store_true")
    p.add_argument("--ocr-lang", default="jpn", help="tesseract の言語。jpn+eng は和文の太字を英字に誤読しやすい")
    p.add_argument("--no-face-filter", action="store_true")
    p.add_argument("--json", action="store_true", help="captions.json と同じものを標準出力に出す")
    args = p.parse_args(argv)
    try:
        if not args.video.is_file():
            raise InputError(f"動画が無い: {args.video}")
        if not (args.color in ("white", "auto") or re.fullmatch(r"#[0-9A-Fa-f]{6}", args.color)):
            raise InputError(f"--color は white、auto、#RRGGBB: {args.color}")
        if args.step != "native":
            try:
                if float(args.step) <= 0:
                    raise ValueError
            except ValueError as e:
                raise InputError(f"--step は native か正の秒: {args.step}") from e
        for opt in (args.beats, args.onsets):
            if opt is not None and not opt.is_file():
                raise InputError(f"ファイルが無い: {opt}")
        out = measure(args)
    except InputError as e:
        print(f"caption_boxes: {e}", file=sys.stderr)
        return 2
    args.work_dir.mkdir(parents=True, exist_ok=True)
    cap_path = args.work_dir / "captions.json"
    cap_path.write_text(json.dumps(out["captions"], ensure_ascii=False, indent=2) + "\n")
    write_source_text(args.work_dir / "source-text.json", args.video.name, out["texts"])
    res = out["captions"]
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"{len(res['cards'])} cards, {len(res['playbook']['captions'])} layers, "
              f"lastCard holdsToEnd={res['lastCard']['holdsToEnd']}")
        for lay in res["playbook"]["captions"]:
            print(f"{lay['id']} {lay['role']} capHeightRatio={lay['capHeightRatio']} "
                  f"cy={lay['position']['cy']} emphasis={lay['emphasis']}")
        print(f"wrote {cap_path} and {args.work_dir / 'source-text.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
