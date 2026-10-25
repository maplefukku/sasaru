"""ElevenLabs Eleven v4 TTS with character timestamps (elevenlabs.io, prices checked 2026-10-25)."""

from __future__ import annotations

import base64
import json
import os
import re

from .. import AS_OF
from ..errors import InputError, ProviderError
from ..keys import Secret
from ..provider import Provider, RunContext, require_inputs
from ..quote import Quote
from ..request import Request

API = "https://api.elevenlabs.io/v1"
PRICING = "https://elevenlabs.io/pricing/api"
DOC = "https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps"
OUTPUT_FORMAT = "mp3_44100_128"
_VOICE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class _Eleven(Provider):
    vendor = "elevenlabs"
    need = "tts"
    env_keys = ("ELEVENLABS_API_KEY",)
    auth_hosts = ("api.elevenlabs.io",)
    sources = (PRICING, DOC)
    per_1k_chars = 0.0
    # v4 documents 10,000 characters per request; v4 Turbo's limit is not published, so it shares v4's.
    max_chars = 10_000

    def auth_headers(self, key: Secret) -> dict:
        return {"xi-api-key": key.reveal()}

    def validate(self, req: Request) -> None:
        if len(req.prompt) > self.max_chars:
            raise InputError(f"text は {self.max_chars} 字までです（{len(req.prompt)} 字）。分けてください")
        require_inputs(req, 0, 0, "入力")

    def quote(self, req: Request) -> Quote:
        n = len(req.prompt)
        usd = n * self.per_1k_chars / 1000
        return Quote(usd, usd, AS_OF, f"{self.model} ${self.per_1k_chars}/1000 字 × {n} 字（有料プランの単価）。{PRICING}")

    def _voice(self, req: Request) -> str:
        voice = req.voice or os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
        if not voice:
            raise InputError("voice（ElevenLabs の voice_id）を req.json か ELEVENLABS_VOICE_ID で渡してください")
        if not _VOICE_ID.match(voice):
            raise InputError("voice は ElevenLabs の voice_id の形（英数字、-、_）にしてください")
        return voice

    def run(self, req: Request, ctx: RunContext) -> list:
        voice = self._voice(req)
        client = self.client(ctx)
        payload = {"text": req.prompt, "model_id": self.model}
        body = client.submit_json(
            f"{API}/text-to-speech/{voice}/with-timestamps?output_format={OUTPUT_FORMAT}", payload
        ).json()
        audio = body.get("audio_base64")
        if not audio:
            raise ProviderError("応答に audio_base64 がありません")
        files = [self.save(ctx, req, base64.b64decode(audio), ".mp3")]
        timing = {k: body[k] for k in ("alignment", "normalized_alignment") if body.get(k)}
        if timing:
            data = json.dumps(timing, ensure_ascii=False, indent=2).encode("utf-8")
            files.append(self.save(ctx, req, data, ".json", suffix=".alignment"))
        return files


class ElevenV4(_Eleven):
    id, model = "elevenlabs-eleven-v4", "eleven_v4"
    per_1k_chars = 0.08


class ElevenV4Turbo(_Eleven):
    id, model = "elevenlabs-eleven-v4-turbo", "eleven_v4_turbo"
    per_1k_chars = 0.04
