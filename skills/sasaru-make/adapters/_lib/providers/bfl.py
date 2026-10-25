"""Black Forest Labs FLUX 3 Image and Klein (docs.bfl.ai, prices checked 2026-10-25). Text to image only."""

from __future__ import annotations

from urllib.parse import urlsplit

from .. import AS_OF
from ..errors import ProviderError
from ..http import check
from ..keys import Secret
from ..provider import Provider, RunContext, require_aspect, require_choice, require_inputs
from ..quote import Quote
from ..request import Request

API = "https://api.bfl.ai/v1"
PRICING = "https://bfl.ai/pricing"
DOC = "https://docs.bfl.ai/flux_3/flux3_image_generate.md"
ASPECTS = ("9:16", "16:9", "1:1", "3:4", "4:3", "2:3", "3:2", "4:5", "5:4", "21:9")
DONE, PENDING = "Ready", ("Pending", "Processing", "Queued")


class _Flux3(Provider):
    vendor = "bfl"
    need = "image-gen"
    env_keys = ("BFL_API_KEY",)
    auth_hosts = ("api.bfl.ai", "api.eu.bfl.ai", "api.us.bfl.ai")
    sources = (PRICING, DOC)
    poll_interval_sec = 1.5
    prices: dict[str, float] = {}
    path = ""

    def auth_headers(self, key: Secret) -> dict:
        return {"x-key": key.reveal()}

    def _res(self, req: Request) -> str:
        return require_choice(req.resolution, tuple(self.prices), "1k", "resolution")

    def validate(self, req: Request) -> None:
        require_aspect(req, ASPECTS)
        self._res(req)
        # The endpoint rejects unknown fields (HTTP 422); reference-image fields are not wired yet.
        require_inputs(req, 0, 0, "参照画像")

    def quote(self, req: Request) -> Quote:
        res = self._res(req)
        usd = self.prices[res] * req.count
        return Quote(usd, usd, AS_OF, f"{self.model} {res} ${self.prices[res]}/枚 × {req.count} 枚。{PRICING}")

    def run(self, req: Request, ctx: RunContext) -> list:
        client = self.client(ctx)
        payload = {"prompt": req.prompt, "aspect_ratio": require_aspect(req, ASPECTS), "resolution": self._res(req)}
        files = []
        for i in range(req.count):
            job = client.submit_json(API + self.path, payload).json()
            job_id = job.get("id")
            polling_url = job.get("polling_url") or (f"{API}/get_result?id={job_id}" if job_id else None)
            if not polling_url:
                raise ProviderError("送信の応答に polling_url も id もありません")
            if (urlsplit(polling_url).hostname or "") not in self.auth_hosts:
                raise ProviderError(f"polling_url のホストが想定外です: {urlsplit(polling_url).hostname}")
            ctx.log(f"bfl: job {job_id}")

            def step(url=polling_url):
                body = check(client.get(url), "bfl の状態の取得").json()
                status = body.get("status")
                if status == DONE:
                    sample = (body.get("result") or {}).get("sample")
                    if not sample:
                        raise ProviderError("Ready なのに result.sample がありません")
                    return sample
                if status in PENDING:
                    return None
                raise ProviderError(f"bfl のジョブが {status}")

            files.append(self.download(client, ctx, req, self.poll(ctx, step, "bfl の画像生成"), ".jpg", i))
        return files


class Flux3Image(_Flux3):
    id, model, path = "bfl-flux-3-image", "flux-3-image", "/flux-3-image"
    prices = {"1k": 0.048, "1.5k": 0.07, "2k": 0.10, "4k": 0.607}


class Flux3Klein(_Flux3):
    id, model, path = "bfl-flux-3-image-klein", "flux-3-image-klein", "/flux-3-image-klein"
    prices = {"1k": 0.009, "1.5k": 0.011, "2k": 0.014, "4k": 0.036}
