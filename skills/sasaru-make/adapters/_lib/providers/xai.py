"""xAI Grok Imagine video and image (docs.x.ai, prices checked 2026-10-25)."""

from __future__ import annotations

import base64
import math

from .. import AS_OF
from ..errors import InputError, ProviderError
from ..http import check
from ..media import data_uri, probe_duration, require_kind
from ..provider import (Provider, RunContext, billed_seconds, require_aspect, require_choice,
                        require_inputs)
from ..quote import Quote
from ..request import Request

API = "https://api.x.ai/v1"
PRICING = "https://docs.x.ai/developers/pricing"
VIDEO_DOC = "https://docs.x.ai/developers/model-capabilities/video/generation"
IMAGE_DOC = "https://docs.x.ai/developers/model-capabilities/images/generation"
ASPECTS = ("1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9", "5:2")
IMAGE_MAX_BYTES = 10 * 1024 * 1024
VIDEO_MAX_BYTES = 25 * 1024 * 1024


class _XaiBase(Provider):
    vendor = "xai"
    env_keys = ("XAI_API_KEY",)
    auth_hosts = ("api.x.ai",)


class _XaiVideo(_XaiBase):
    per_sec: dict[str, float] = {}
    image_usd = 0.01
    max_sec = 15
    max_images = 0
    min_images = 0
    sources = (PRICING, VIDEO_DOC)

    def _resolution(self, req: Request) -> str:
        return require_choice(req.resolution, tuple(self.per_sec), "720p", "resolution")

    def validate(self, req: Request) -> None:
        billed_seconds(req, 1, self.max_sec)
        if self.need != "i2v":
            require_aspect(req, ASPECTS)
        self._resolution(req)
        require_inputs(req, self.min_images, self.max_images, "画像")
        require_kind(req.inputs, "image")

    def quote(self, req: Request) -> Quote:
        secs = billed_seconds(req, 1, self.max_sec)
        res = self._resolution(req)
        n = len(req.inputs)
        usd = self.per_sec[res] * secs + self.image_usd * n
        basis = f"{self.model} {res} ${self.per_sec[res]}/秒 × {secs} 秒"
        if n:
            basis += f" + 入力画像 ${self.image_usd} × {n} 枚"
        return Quote(usd, usd, AS_OF, f"{basis}。{PRICING}")

    def payload(self, req: Request) -> dict:
        body = {
            "model": self.model,
            "prompt": req.prompt,
            "duration": billed_seconds(req, 1, self.max_sec),
            "resolution": self._resolution(req),
        }
        if self.need != "i2v":
            body["aspect_ratio"] = require_aspect(req, ASPECTS)
        return body

    endpoint = "/videos/generations"

    def run(self, req: Request, ctx: RunContext) -> list:
        client = self.client(ctx)
        submitted = client.submit_json(API + self.endpoint, self.payload(req)).json()
        request_id = submitted.get("request_id") or submitted.get("id")
        if not request_id:
            raise ProviderError("送信の応答に request_id がありません")
        ctx.log(f"xai: request_id {request_id}")

        def step():
            r = client.get(f"{API}/videos/{request_id}")
            if r.status == 202:
                return None
            body = check(r, "xai の状態の取得").json()
            status = str(body.get("status", "")).lower()
            video = body.get("video") or {}
            if video.get("url") and status in ("", "done", "completed", "succeeded"):
                return video["url"]
            if status in ("failed", "expired", "error", "rejected"):
                raise ProviderError(f"xai のジョブが {status}: {body.get('error', '')}")
            return None

        url = self.poll(ctx, step, "xai の動画生成")
        return [self.download(client, ctx, req, url, ".mp4")]


class GrokVideoLite(_XaiVideo):
    model = "grok-imagine-video-1.5-lite"
    per_sec = {"480p": 0.02, "720p": 0.03, "1080p": 0.14}


class GrokVideo(_XaiVideo):
    model = "grok-imagine-video-1.5"
    per_sec = {"480p": 0.08, "720p": 0.14, "1080p": 0.25}


class GrokVideoLiteT2V(GrokVideoLite):
    id, need = "xai-grok-imagine-video-1.5-lite", "t2v"


class GrokVideoT2V(GrokVideo):
    id, need = "xai-grok-imagine-video-1.5", "t2v"


class _I2V:
    min_images = max_images = 1

    def payload(self, req: Request) -> dict:
        body = super().payload(req)
        body["image"] = {"url": data_uri(req.inputs[0], IMAGE_MAX_BYTES)}
        return body


class GrokVideoLiteI2V(_I2V, GrokVideoLite):
    id, need = "xai-grok-imagine-video-1.5-lite", "i2v"


class GrokVideoI2V(_I2V, GrokVideo):
    id, need = "xai-grok-imagine-video-1.5", "i2v"


class GrokVideoR2V(GrokVideo):
    """Reference images keep a subject consistent; capped at 720p and 15 s."""

    id, need = "xai-grok-imagine-video-1.5", "r2v"
    per_sec = {"480p": 0.08, "720p": 0.14}
    min_images, max_images = 1, 14

    def payload(self, req: Request) -> dict:
        body = super().payload(req)
        body["reference_images"] = [{"url": data_uri(p, IMAGE_MAX_BYTES)} for p in req.inputs]
        return body


class GrokVideoEdit(_XaiVideo):
    """V2V edit of a clip up to 8.7 s. Output length follows the input."""

    id, need = "xai-grok-imagine-video", "v2v"
    model = "grok-imagine-video"
    per_sec = {"480p": 0.05, "720p": 0.07}
    input_per_sec = 0.01
    max_input_sec = 8.7
    endpoint = "/videos/edits"

    def validate(self, req: Request) -> None:
        require_inputs(req, 1, 1, "動画")
        require_kind(req.inputs, "video")
        self._resolution(req)
        secs = probe_duration(req.inputs[0])
        if secs is not None and secs > self.max_input_sec:
            raise InputError(f"編集元は {self.max_input_sec} 秒までです（{secs:.2f} 秒）")

    def quote(self, req: Request) -> Quote:
        res = self._resolution(req)
        secs = probe_duration(req.inputs[0])
        rate = self.per_sec[res] + self.input_per_sec
        if secs is None:
            hi = math.ceil(self.max_input_sec)
            lo = min(math.ceil(req.duration_sec or 1), hi)
            return Quote(rate * lo, rate * hi, AS_OF,
                         f"ffprobe が無く入力の尺が不明。上限は編集元の最大 {self.max_input_sec} 秒で計算。"
                         f"出力 ${self.per_sec[res]}/秒 + 入力 ${self.input_per_sec}/秒。{PRICING}")
        s = math.ceil(secs - 1e-9)
        usd = rate * s
        return Quote(usd, usd, AS_OF,
                     f"{self.model} {res} 出力 ${self.per_sec[res]}/秒 + 入力動画 ${self.input_per_sec}/秒 × {s} 秒。{PRICING}")

    def payload(self, req: Request) -> dict:
        if probe_duration(req.inputs[0]) is None:
            raise InputError("送信には ffprobe で入力の尺を確かめる必要があります")
        return {
            "model": self.model,
            "prompt": req.prompt,
            "video": {"url": data_uri(req.inputs[0], VIDEO_MAX_BYTES)},
            "resolution": self._resolution(req),
        }


class GrokImage(_XaiBase):
    id, need = "xai-grok-imagine-image-2.0", "image-gen"
    model = "grok-imagine-image-2.0"
    prices = {("1k", "low"): 0.04, ("1k", "medium"): 0.06, ("2k", "low"): 0.06, ("2k", "medium"): 0.08}
    sources = (PRICING, IMAGE_DOC)

    def _opts(self, req: Request) -> tuple[str, str]:
        res = require_choice(req.resolution, ("1k", "2k"), "1k", "resolution")
        quality = require_choice(req.quality, ("low", "medium"), "low", "quality")
        return res, quality

    def validate(self, req: Request) -> None:
        require_aspect(req, ASPECTS)
        self._opts(req)
        require_inputs(req, 0, 0, "参照画像")

    def quote(self, req: Request) -> Quote:
        res, quality = self._opts(req)
        unit = self.prices[(res, quality)]
        usd = unit * req.count
        return Quote(usd, usd, AS_OF, f"{self.model} {res} {quality} ${unit}/枚 × {req.count} 枚。{PRICING}")

    def run(self, req: Request, ctx: RunContext) -> list:
        res, quality = self._opts(req)
        client = self.client(ctx)
        body = client.submit_json(f"{API}/images/generations", {
            "model": self.model,
            "prompt": req.prompt,
            "n": req.count,
            "aspect_ratio": require_aspect(req, ASPECTS),
            "resolution": res,
            "quality": quality,
            "response_format": "b64_json",
        }).json()
        items = body.get("data") or []
        if len(items) != req.count:
            raise ProviderError(f"画像が {req.count} 枚の予定で {len(items)} 枚返りました")
        files = []
        for i, item in enumerate(items):
            if item.get("b64_json"):
                files.append(self.save(ctx, req, base64.b64decode(item["b64_json"]), ".jpg", i))
            elif item.get("url"):
                files.append(self.download(client, ctx, req, item["url"], ".jpg", i))
            else:
                raise ProviderError("画像の応答に b64_json も url もありません")
        return files
