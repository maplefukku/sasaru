"""Providers per need. The first one in each list is the default."""

from __future__ import annotations

from .errors import InputError
from .provider import Provider
from .providers import bfl, elevenlabs, google, runway, xai

PROVIDERS: dict[str, list[type[Provider]]] = {
    "t2v": [xai.GrokVideoLiteT2V, xai.GrokVideoT2V, runway.Gen45T2V],
    "i2v": [xai.GrokVideoLiteI2V, xai.GrokVideoI2V, runway.Gen45I2V],
    "r2v": [xai.GrokVideoR2V],
    "v2v": [runway.Aleph2V2V, xai.GrokVideoEdit],
    "image-gen": [google.NanoBanana21, bfl.Flux3Klein, bfl.Flux3Image, xai.GrokImage],
    "tts": [elevenlabs.ElevenV4, elevenlabs.ElevenV4Turbo, google.GeminiFlashTTS, google.GeminiFlashLiteTTS],
}


def resolve(need: str, provider_id: str | None) -> Provider:
    classes = PROVIDERS[need]
    if provider_id is None:
        return classes[0]()
    for cls in classes:
        if cls.id == provider_id:
            return cls()
    ids = ", ".join(c.id for c in classes)
    raise InputError(f"{need} のプロバイダに {provider_id} はありません（{ids}）")
