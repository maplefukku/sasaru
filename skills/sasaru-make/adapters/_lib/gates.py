from __future__ import annotations

import math
import os
import re
import unicodedata
from pathlib import Path

from .errors import Refused
from .quote import Quote
from .request import Request

TALKING_HEAD_NEEDS = frozenset({"lipsync", "r2v"})
FACE_IDENTITY_NEEDS = frozenset({"r2v"})

# Deliberately broad: a false positive costs a rephrase, a miss costs a talking-head cut.
_SPEECH_EN = r"(talk|talks|talking|speak|speaks|speaking|says|saying|explains|explaining|tells|telling|pitches|pitching)"
_TALKING_HEAD_PATTERNS = [
    rf"\b{_SPEECH_EN}\s+(directly\s+|straight\s+)?(to|into|at|toward|towards)\s+(the\s+)?(camera|viewer|lens|audience)",
    rf"\b(camera|lens)\b[^.]{{0,60}}\b{_SPEECH_EN}\b",
    rf"\b{_SPEECH_EN}\b[^.]{{0,60}}\b(camera|lens)\b",
    r"\b(direct|straight)\s+(to|into)\s+(the\s+)?(camera|lens)",
    r"\b(to|into)\s+camera\b",
    r"\blip\s?sync",
    r"\btalking\s?head",
    r"\b(vlog|vlogger|vlogging|monologue|presenter|spokesperson|news\s?anchor|testimonial|ugc|interview)\b",
    r"\b(he|she|they|person|man|woman|host|girl|boy|guy|influencer)\s+(says|said|speaks|talks|explains|tells)\b",
    r"(カメラ|視聴者|こちら|画面|レンズ)(に|へ|を見て|を見ながら|目線で)[^。]{0,8}(話|喋|しゃべ|語|説明|紹介)",
    r"カメラ目線",
    r"(喋|しゃべ)(る|り|っ)",
    r"(語りかけ|一人語り|リップシンク|口パク|自撮り|トーキングヘッド|顔出し|インタビュー|レビュー動画)",
    r"(人|男性|女性|演者|話者|キャスター|インフルエンサー)が[^。]{0,8}(話す|話して|語る|語って|説明する|説明して|紹介する|紹介して)",
]
_TALKING_HEAD_RE = [re.compile(p, re.IGNORECASE) for p in _TALKING_HEAD_PATTERNS]
_INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"))


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_INVISIBLE)
    return re.sub(r"[-_‐‑‒–—―]+", " ", text).lower()


def looks_like_talking_head(text: str) -> bool:
    t = _normalize(text)
    return any(r.search(t) for r in _TALKING_HEAD_RE)


def check_people(req: Request) -> None:
    """Talking heads and face-identity references only when the playbook route lists them."""
    if req.need == "tts":
        return
    allowed = set(req.route_needs)

    if req.talking_head or looks_like_talking_head(req.prompt):
        if not allowed & TALKING_HEAD_NEEDS:
            reason = "talkingHead: true" if req.talking_head else "プロンプトが人のカメラへの語りを指している"
            raise Refused(
                f"人がカメラに喋る生成は既定で拒否します（{reason}）。"
                "playbook のルートの needs に lipsync か r2v が明示されているときだけ、"
                "routeNeeds にその値を渡せば通ります"
            )

    kind = req.reference_kind
    if kind is None and req.need == "r2v":
        kind = "face"
    if kind == "face" and not allowed & FACE_IDENTITY_NEEDS:
        hint = "referenceKind が無い R2V は顔として扱います。" if req.reference_kind is None else ""
        raise Refused(
            f"顔の同一性を使う参照の生成は既定で拒否します。{hint}"
            "playbook のルートの needs に r2v が明示されているときだけ、routeNeeds に r2v を渡せば通ります。"
            "顔でない参照（キャラクター、製品、物、風景、画風）なら referenceKind で宣言してください"
        )


def _work_dirs() -> list[Path]:
    home = os.environ.get("SASARU_HOME")
    if not home:
        return []
    work = Path(os.path.abspath(Path(home).expanduser() / "work"))
    return [work, work.resolve()]


def _under_default_work(p: Path) -> bool:
    parts = p.parts
    return any(parts[i] == "sasaru" and parts[i + 1] == "work" for i in range(len(parts) - 1))


def check_inputs_are_not_reference(req: Request) -> None:
    """Reference reels live under sasaru/work/; they never go to a generator.

    A tripwire, not a boundary: a copy made elsewhere passes. Symlinks are caught on both ends.
    """
    work_dirs = _work_dirs()
    for given in req.inputs:
        for p in (given, given.resolve()):
            if _under_default_work(p) or any(p.is_relative_to(d) for d in work_dirs):
                raise Refused(
                    f"取り込みの作業フォルダ（sasaru/work/）のファイルは生成 API に渡しません: {given.name}。"
                    "参照の映像や静止画を入力にしないでください"
                )


def check_spend(quote: Quote, *, yes: bool, cap_usd: float | None) -> None:
    if not yes or cap_usd is None:
        missing = [flag for flag, ok in (("--yes", yes), ("--cap-usd", cap_usd is not None)) if not ok]
        raise Refused(
            f"課金する送信には --yes と --cap-usd の両方が要ります（無いもの: {', '.join(missing)}）。"
            f"見積もりは {quote.usd_min:.4f}〜{quote.usd_max:.4f} USD"
        )
    if not math.isfinite(cap_usd) or cap_usd <= 0:
        raise Refused("--cap-usd は正の数にしてください")
    if quote.usd_max <= 0:
        raise Refused("見積もりが 0 USD の有料送信はしません。見積もりの根拠を確かめてください")
    if quote.usd_max > cap_usd:
        raise Refused(
            f"見積もりの上限 {quote.usd_max:.4f} USD が --cap-usd {cap_usd:.4f} を超えるので送信しません"
        )
