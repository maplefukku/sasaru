from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .errors import InputError

NEEDS = ("image-gen", "t2v", "i2v", "r2v", "v2v", "tts")

# Values a playbook route may list in `needs` (schema/playbook.schema.json).
ROUTE_NEEDS = (
    "none", "image-gen", "t2v", "i2v", "v2v", "r2v", "lipsync", "tts",
    "screen-capture", "own-footage", "stock-footage",
)

REFERENCE_KINDS = ("face", "character", "product", "object", "scene", "style")

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class Request:
    need: str
    cut_id: str
    beat: str
    duration_sec: float | None
    aspect: str | None
    fps: float | None
    prompt: str
    inputs: tuple[Path, ...]
    provider: str | None = None
    resolution: str | None = None
    quality: str | None = None
    count: int = 1
    voice: str | None = None
    language: str | None = None
    route_needs: tuple[str, ...] = ()
    talking_head: bool = False
    reference_kind: str | None = None
    raw: dict = field(default_factory=dict, compare=False, repr=False)

    @property
    def stem(self) -> str:
        return f"{_SAFE.sub('-', self.cut_id)}-{_SAFE.sub('-', self.beat)}"


def _str(d: dict, key: str, *, required: bool = False) -> str | None:
    v = d.get(key)
    if v is None:
        if required:
            raise InputError(f"req.json に {key} がありません")
        return None
    if not isinstance(v, str) or not v.strip():
        raise InputError(f"req.json の {key} は空でない文字列にしてください")
    return v.strip()


def _num(d: dict, key: str) -> float | None:
    v = d.get(key)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
        raise InputError(f"req.json の {key} は正の数にしてください")
    return float(v)


def parse(data: dict, base_dir: Path) -> Request:
    if not isinstance(data, dict):
        raise InputError("req.json はオブジェクトにしてください")
    need = _str(data, "need", required=True).replace("_", "-")
    if need not in NEEDS:
        raise InputError(f"need は {', '.join(NEEDS)} のどれかです: {need}")

    text_key = "text" if need == "tts" else "prompt"
    prompt = _str(data, text_key, required=True)

    inputs_raw = data.get("inputs", [])
    if not isinstance(inputs_raw, list) or not all(isinstance(p, str) for p in inputs_raw):
        raise InputError("req.json の inputs はパスの配列にしてください")
    inputs = []
    for p in inputs_raw:
        path = Path(p)
        if not path.is_absolute():
            path = base_dir / path
        if not path.is_file():
            raise InputError(f"入力ファイルがありません: {p}")
        inputs.append(path.resolve())

    route_needs = data.get("routeNeeds", [])
    if not isinstance(route_needs, list) or not all(n in ROUTE_NEEDS for n in route_needs):
        raise InputError(f"routeNeeds は playbook の routes[].needs の値の配列です: {route_needs}")

    talking_head = data.get("talkingHead", False)
    if not isinstance(talking_head, bool):
        raise InputError("talkingHead は true か false です")

    reference_kind = _str(data, "referenceKind")
    if reference_kind is not None and reference_kind not in REFERENCE_KINDS:
        raise InputError(f"referenceKind は {', '.join(REFERENCE_KINDS)} のどれかです")

    count = data.get("count", 1)
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 4:
        raise InputError("count は 1 から 4 の整数です")

    return Request(
        need=need,
        cut_id=_str(data, "cutId", required=True),
        beat=_str(data, "beat", required=True),
        duration_sec=_num(data, "durationSec"),
        aspect=_str(data, "aspect"),
        fps=_num(data, "fps"),
        prompt=prompt,
        inputs=tuple(inputs),
        provider=_str(data, "provider"),
        resolution=(_str(data, "resolution") or "").lower() or None,
        quality=_str(data, "quality"),
        count=count,
        voice=_str(data, "voice"),
        language=_str(data, "language"),
        route_needs=tuple(route_needs),
        talking_head=talking_head,
        reference_kind=reference_kind,
        raw=data,
    )


def load(path: Path) -> Request:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise InputError(f"req.json がありません: {path}") from None
    except json.JSONDecodeError as e:
        raise InputError(f"req.json が JSON として読めません: {e}") from None
    return parse(data, path.parent)
