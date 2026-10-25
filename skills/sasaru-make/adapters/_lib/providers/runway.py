"""Runway API gen4.5 (T2V, I2V) and aleph2 (V2V) (docs.dev.runwayml.com, prices checked 2026-10-25)."""

from __future__ import annotations

import math

from .. import AS_OF
from ..errors import InputError, ProviderError
from ..http import check
from ..keys import Secret
from ..media import data_uri, probe_duration, require_kind
from ..provider import Provider, RunContext, billed_seconds, require_aspect, require_inputs
from ..quote import Quote
from ..request import Request

API = "https://api.dev.runwayml.com/v1"
API_VERSION = "2024-11-06"
PRICING = "https://docs.dev.runwayml.com/guides/pricing/"
API_DOC = "https://docs.dev.runwayml.com/api"
IMAGE_MAX_BYTES = 5 * 1024 * 1024
VIDEO_MAX_BYTES = 16 * 1024 * 1024

T2V_RATIOS = {"9:16": "720:1280", "16:9": "1280:720"}
I2V_RATIOS = {**T2V_RATIOS, "1:1": "960:960", "4:3": "1104:832", "3:4": "832:1104", "21:9": "1584:672"}


def require_prompt_len(req: Request) -> None:
    if len(req.prompt) > 1000:
        raise InputError(f"prompt は 1000 字までです（{len(req.prompt)} 字）")


class _Runway(Provider):
    vendor = "runway"
    env_keys = ("RUNWAYML_API_SECRET",)
    auth_hosts = ("api.dev.runwayml.com",)
    sources = (PRICING, API_DOC)

    def auth_headers(self, key: Secret) -> dict:
        return {"Authorization": f"Bearer {key.reveal()}", "X-Runway-Version": API_VERSION}

    endpoint = ""

    def payload(self, req: Request) -> dict:
        raise NotImplementedError

    def run(self, req: Request, ctx: RunContext) -> list:
        client = self.client(ctx)
        task = client.submit_json(API + self.endpoint, self.payload(req)).json()
        task_id = task.get("id")
        if not task_id:
            raise ProviderError("送信の応答に id がありません")
        ctx.log(f"runway: task {task_id}")

        def step():
            body = check(client.get(f"{API}/tasks/{task_id}"), "runway の状態の取得").json()
            status = body.get("status")
            if status == "SUCCEEDED":
                output = body.get("output") or []
                if not output:
                    raise ProviderError("SUCCEEDED なのに output が空です")
                return output
            if status in ("FAILED", "CANCELLED"):
                raise ProviderError(f"runway のタスクが {status}: {body.get('failureCode') or body.get('failure') or ''}")
            return None

        urls = self.poll(ctx, step, "runway の生成")
        return [self.download(client, ctx, req, u, ".mp4", i) for i, u in enumerate(urls)]


class _Gen45(_Runway):
    model = "gen4.5"
    per_sec = 0.12
    ratios = T2V_RATIOS

    def validate(self, req: Request) -> None:
        require_prompt_len(req)
        billed_seconds(req, 2, 10)
        require_aspect(req, tuple(self.ratios))

    def quote(self, req: Request) -> Quote:
        secs = billed_seconds(req, 2, 10)
        usd = self.per_sec * secs
        return Quote(usd, usd, AS_OF, f"{self.model} 12 クレジット/秒 = ${self.per_sec}/秒 × {secs} 秒。{PRICING}")

    def _common(self, req: Request) -> dict:
        return {
            "model": self.model,
            "promptText": req.prompt,
            "ratio": self.ratios[require_aspect(req, tuple(self.ratios))],
            "duration": billed_seconds(req, 2, 10),
        }


class Gen45T2V(_Gen45):
    id, need = "runway-gen4.5", "t2v"
    endpoint = "/text_to_video"

    def validate(self, req: Request) -> None:
        super().validate(req)
        require_inputs(req, 0, 0, "入力")

    def payload(self, req: Request) -> dict:
        return self._common(req)


class Gen45I2V(_Gen45):
    """First frame only; gen4.5 has no last-frame position."""

    id, need = "runway-gen4.5", "i2v"
    endpoint = "/image_to_video"
    ratios = I2V_RATIOS

    def validate(self, req: Request) -> None:
        super().validate(req)
        require_inputs(req, 1, 1, "先頭フレームの画像")
        require_kind(req.inputs, "image")

    def payload(self, req: Request) -> dict:
        body = self._common(req)
        body["promptImage"] = [{"uri": data_uri(req.inputs[0], IMAGE_MAX_BYTES), "position": "first"}]
        return body


class Aleph2V2V(_Runway):
    """Text-driven edit of a 2–30 s clip; billed per second of video, minimum 56 credits."""

    id, need = "runway-aleph2", "v2v"
    model = "aleph2"
    endpoint = "/video_to_video"
    per_sec = 0.28
    min_usd = 0.56
    max_input_sec = 30

    def validate(self, req: Request) -> None:
        require_prompt_len(req)
        require_inputs(req, 1, 1, "編集元の動画")
        require_kind(req.inputs, "video")
        secs = probe_duration(req.inputs[0])
        if secs is not None and not 2 <= secs <= self.max_input_sec:
            raise InputError(f"編集元は 2〜{self.max_input_sec} 秒です（{secs:.2f} 秒）")

    def quote(self, req: Request) -> Quote:
        secs = probe_duration(req.inputs[0])
        if secs is None:
            lo = max(self.min_usd, self.per_sec * min(math.ceil(req.duration_sec or 2), self.max_input_sec))
            return Quote(lo, self.per_sec * self.max_input_sec, AS_OF,
                         f"ffprobe が無く入力の尺が不明。上限は編集元の最大 {self.max_input_sec} 秒で計算。"
                         f"${self.per_sec}/秒、最低 ${self.min_usd}。{PRICING}")
        s = math.ceil(secs - 1e-9)
        usd = max(self.min_usd, self.per_sec * s)
        return Quote(usd, usd, AS_OF,
                     f"{self.model} 28 クレジット/秒 = ${self.per_sec}/秒 × {s} 秒（最低 ${self.min_usd}）。{PRICING}")

    def payload(self, req: Request) -> dict:
        if probe_duration(req.inputs[0]) is None:
            raise InputError("送信には ffprobe で入力の尺を確かめる必要があります")
        return {
            "model": self.model,
            "videoUri": data_uri(req.inputs[0], VIDEO_MAX_BYTES),
            "promptText": req.prompt,
        }
