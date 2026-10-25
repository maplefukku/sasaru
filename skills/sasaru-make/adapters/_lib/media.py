from __future__ import annotations

import base64
import json
import mimetypes
import shutil
import subprocess
import wave
from pathlib import Path

from .errors import InputError

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXT = {".mp4", ".mov", ".webm"}


def mime(path: Path) -> str:
    m, _ = mimetypes.guess_type(path.name)
    if m is None:
        raise InputError(f"拡張子から種類が分かりません: {path.name}")
    return m


def require_kind(paths, kind: str) -> None:
    exts = IMAGE_EXT if kind == "image" else VIDEO_EXT
    for p in paths:
        if p.suffix.lower() not in exts:
            what = "画像" if kind == "image" else "動画"
            raise InputError(f"{p.name} は{what}として受け付けません（{', '.join(sorted(exts))}）")


def data_uri(path: Path, max_bytes: int) -> str:
    size = path.stat().st_size
    if size > max_bytes:
        raise InputError(
            f"{path.name} は {size} バイトで、data URI の上限 {max_bytes} バイトを超えます。縮めてから渡してください"
        )
    return f"data:{mime(path)};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def probe_duration(path: Path) -> float | None:
    """Seconds from ffprobe, or None when ffprobe is missing."""
    exe = shutil.which("ffprobe")
    if exe is None:
        return None
    out = subprocess.run(
        [exe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=False,
    )
    try:
        return float(json.loads(out.stdout)["format"]["duration"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise InputError(f"動画の尺を読めません: {path.name}") from None


def write_wav(path: Path, pcm: bytes, rate: int, channels: int = 1, sample_width: int = 2) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sample_width)
        w.setframerate(rate)
        w.writeframes(pcm)


def ext_for(content_type: str | None, default: str) -> str:
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return ".jpg" if guessed == ".jpe" else guessed
    return default
