"""Gemini API: Nano Banana 2.1 images and Gemini 3.8 TTS (ai.google.dev, prices checked 2026-10-25)."""

from __future__ import annotations

import base64
import re
from datetime import date, datetime, timezone

from .. import AS_OF
from ..errors import InputError, ProviderError
from ..keys import Secret
from ..media import mime, require_kind, write_wav
from ..provider import Provider, RunContext, require_aspect, require_choice, require_inputs
from ..quote import Quote
from ..request import Request

API = "https://generativelanguage.googleapis.com/v1beta"
PRICING = "https://ai.google.dev/gemini-api/docs/pricing"
IMAGE_DOC = "https://ai.google.dev/gemini-api/docs/image-generation"
TTS_DOC = "https://ai.google.dev/gemini-api/docs/speech-generation"
INLINE_MAX_BYTES = 18 * 1024 * 1024


def _today() -> date:
    return datetime.now(timezone.utc).date()


class _Gemini(Provider):
    vendor = "google"
    env_keys = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
    auth_hosts = ("generativelanguage.googleapis.com",)

    def auth_headers(self, key: Secret) -> dict:
        return {"x-goog-api-key": key.reveal()}

    def generate(self, client, body: dict) -> list[dict]:
        resp = client.submit_json(f"{API}/models/{self.model}:generateContent", body).json()
        candidates = resp.get("candidates") or []
        parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
        inline = [p.get("inlineData") or p.get("inline_data") for p in parts]
        inline = [d for d in inline if d and d.get("data")]
        if not inline:
            block = (resp.get("promptFeedback") or {}).get("blockReason")
            finish = candidates[0].get("finishReason") if candidates else None
            raise ProviderError(f"Gemini が中身を返しませんでした（blockReason={block}, finishReason={finish}）")
        return inline


class NanoBanana21(_Gemini):
    """Image output is billed per output tokens by size tier; 9:16 1K is 768x1376."""

    id, need = "google-nano-banana-2.1", "image-gen"
    model = "gemini-nano-banana-2.1"
    sources = (PRICING, IMAGE_DOC)
    out_per_m = 30.0
    # 4K: the image guide says 2520 tokens, the pricing footnote 3780. Quote both ends.
    tokens = {"1k": (1120, 1120), "2k": (1680, 1680), "4k": (2520, 3780)}
    aspects = ("9:16", "16:9", "1:1", "3:4", "4:3", "2:3", "3:2", "4:5", "5:4", "21:9")
    max_refs = 14
    # Input prices for 2.1 are not in the route notes; Nano Banana Pro bills image input at $2/1M.
    assumed_in_per_m = 2.0
    assumed_ref_tokens = 1120

    def _res(self, req: Request) -> str:
        return require_choice(req.resolution, tuple(self.tokens), "1k", "resolution")

    def validate(self, req: Request) -> None:
        require_aspect(req, self.aspects)
        self._res(req)
        require_inputs(req, 0, self.max_refs, "参照画像")
        require_kind(req.inputs, "image")
        if sum(p.stat().st_size for p in req.inputs) * 4 // 3 > INLINE_MAX_BYTES:
            raise InputError("参照画像の合計が大きすぎます（インラインの上限を超える）")

    def quote(self, req: Request) -> Quote:
        res = self._res(req)
        lo_tok, hi_tok = self.tokens[res]
        lo = lo_tok * self.out_per_m / 1e6 * req.count
        in_tok = len(req.prompt) + self.assumed_ref_tokens * len(req.inputs)
        allowance = in_tok * self.assumed_in_per_m / 1e6 * req.count
        hi = hi_tok * self.out_per_m / 1e6 * req.count + allowance
        return Quote(lo, hi, AS_OF,
                     f"{self.model} {res} 出力 {lo_tok}"
                     + (f"〜{hi_tok}" if hi_tok != lo_tok else "")
                     + f" トークン × ${self.out_per_m}/100万 × {req.count} 枚。"
                     f"上限には入力（プロンプト {len(req.prompt)} 字と参照 {len(req.inputs)} 枚）を"
                     f"${self.assumed_in_per_m}/100万の仮定で足した。{PRICING}")

    def run(self, req: Request, ctx: RunContext) -> list:
        client = self.client(ctx)
        parts = [{"text": req.prompt}]
        parts += [{"inlineData": {"mimeType": mime(p), "data": base64.b64encode(p.read_bytes()).decode("ascii")}}
                  for p in req.inputs]
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": require_aspect(req, self.aspects), "imageSize": self._res(req).upper()},
            },
        }
        files = []
        for i in range(req.count):
            data = self.generate(client, body)[0]
            ext = ".png" if "png" in data.get("mimeType", "png") else ".jpg"
            files.append(self.save(ctx, req, base64.b64decode(data["data"]), ext, i))
        return files


class _GeminiTTS(_Gemini):
    need = "tts"
    sources = (PRICING, TTS_DOC)
    in_per_m = 0.50
    out_per_m = 0.0
    tokens_per_sec = 25
    max_in_tokens = 8192
    max_out_tokens = 16384
    price_doubles_on = date(2027, 1, 1)
    default_voice = "Kore"

    def validate(self, req: Request) -> None:
        # Japanese runs close to one token per character; this keeps the request under the input limit.
        if len(req.prompt) > 8000:
            raise InputError(f"text は 8000 字までにしてください（{len(req.prompt)} 字）")
        require_inputs(req, 0, 0, "入力")

    def quote(self, req: Request) -> Quote:
        k = 2.0 if _today() >= self.price_doubles_on else 1.0
        in_rate, out_rate = self.in_per_m * k / 1e6, self.out_per_m * k / 1e6
        est_sec = req.duration_sec * 0.8 if req.duration_sec else len(req.prompt) / 12
        hi = self.max_out_tokens * out_rate + self.max_in_tokens * in_rate
        lo = min(hi, est_sec * self.tokens_per_sec * out_rate)
        note = "（2027-01-01 からの倍額）" if k > 1 else "（2027-01-01 から倍額）"
        return Quote(lo, hi, AS_OF,
                     f"{self.model} 出力 ${self.out_per_m * k}/100万トークン、25 トークン/秒{note}。"
                     f"下限は約 {est_sec:.1f} 秒の音声、上限は出力 {self.max_out_tokens} と入力 {self.max_in_tokens} "
                     f"トークンの上限いっぱい。{PRICING}")

    def run(self, req: Request, ctx: RunContext) -> list:
        client = self.client(ctx)
        body = {
            "contents": [{"parts": [{"text": req.prompt}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": req.voice or self.default_voice}}},
            },
        }
        data = self.generate(client, body)[0]
        audio = base64.b64decode(data["data"])
        mt = data.get("mimeType", "")
        if "L16" in mt or "pcm" in mt.lower():
            m = re.search(r"rate=(\d+)", mt)
            ctx.out_dir.mkdir(parents=True, exist_ok=True)
            path = ctx.out_dir / f"{req.stem}-{self.id}.wav"
            write_wav(path, audio, int(m.group(1)) if m else 24000)
            return [path]
        ext = ".mp3" if "mpeg" in mt or "mp3" in mt else ".wav"
        return [self.save(ctx, req, audio, ext)]


class GeminiFlashTTS(_GeminiTTS):
    id, model = "google-gemini-3.8-flash-tts", "gemini-3.8-flash-tts"
    out_per_m = 9.0


class GeminiFlashLiteTTS(_GeminiTTS):
    id, model = "google-gemini-3.8-flash-lite-tts", "gemini-3.8-flash-lite-tts"
    out_per_m = 6.0
