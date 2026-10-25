from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import keys
from .errors import InputError, ProviderError
from .http import Client, Transport, check
from .media import ext_for
from .quote import Quote
from .request import Request


@dataclass
class RunContext:
    out_dir: Path
    transport: Transport
    poll_timeout_sec: float = 900.0
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    log: Callable[[str], None] = field(default=lambda msg: None)


class Provider:
    """One model at one vendor, behind the quote/run interface of one need."""

    id: str = ""
    need: str = ""
    vendor: str = ""
    model: str = ""
    env_keys: tuple[str, ...] = ()
    auth_hosts: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    poll_interval_sec: float = 5.0

    def auth_headers(self, key: keys.Secret) -> dict:
        return {"Authorization": f"Bearer {key.reveal()}"}

    def validate(self, req: Request) -> None:
        raise NotImplementedError

    def quote(self, req: Request) -> Quote:
        raise NotImplementedError

    def run(self, req: Request, ctx: RunContext) -> list[Path]:
        raise NotImplementedError

    def describe(self) -> dict:
        return {"id": self.id, "need": self.need, "vendor": self.vendor, "model": self.model,
                "env": list(self.env_keys), "sources": list(self.sources)}

    def client(self, ctx: RunContext) -> Client:
        return Client(ctx.transport, auth_hosts=self.auth_hosts, auth_headers=self.auth_headers,
                      key=keys.read(*self.env_keys))

    def poll(self, ctx: RunContext, step: Callable[[], object | None], what: str) -> object:
        deadline = ctx.clock() + ctx.poll_timeout_sec
        while True:
            result = step()
            if result is not None:
                return result
            if ctx.clock() >= deadline:
                raise ProviderError(
                    f"{what}が {ctx.poll_timeout_sec:.0f} 秒で終わりませんでした。ジョブは続いている可能性があります"
                )
            ctx.sleep(self.poll_interval_sec)

    def save(self, ctx: RunContext, req: Request, data: bytes, ext: str, index: int = 0, suffix: str = "") -> Path:
        ctx.out_dir.mkdir(parents=True, exist_ok=True)
        n = f"-{index + 1}" if req.count > 1 else ""
        path = ctx.out_dir / f"{req.stem}-{self.id}{n}{suffix}{ext}"
        path.write_bytes(data)
        return path

    def download(self, client: Client, ctx: RunContext, req: Request, url: str, default_ext: str, index: int = 0) -> Path:
        r = check(client.get(url), "生成物の取得")
        return self.save(ctx, req, r.body, ext_for(_header(r.headers, "content-type"), default_ext), index)


def _header(headers: dict, name: str) -> str | None:
    for k, v in headers.items():
        if k.lower() == name:
            return v
    return None


def billed_seconds(req: Request, lo: int, hi: int) -> int:
    """Whole seconds the provider will generate and bill for this request."""
    if req.duration_sec is None:
        raise InputError("durationSec が要ります")
    s = max(lo, math.ceil(req.duration_sec - 1e-9))
    if s > hi:
        raise InputError(f"durationSec {req.duration_sec} は上限 {hi} 秒を超えます。ビートを分けてください")
    return s


def require_aspect(req: Request, allowed: tuple[str, ...], default: str = "9:16") -> str:
    aspect = req.aspect or default
    if aspect not in allowed:
        raise InputError(f"aspect {aspect} はこのプロバイダで使えません（{', '.join(allowed)}）")
    return aspect


def require_choice(value: str | None, allowed: tuple[str, ...], default: str, name: str) -> str:
    v = value or default
    if v not in allowed:
        raise InputError(f"{name} {v} はこのプロバイダで使えません（{', '.join(allowed)}）")
    return v


def require_inputs(req: Request, lo: int, hi: int, what: str) -> None:
    n = len(req.inputs)
    if not lo <= n <= hi:
        span = f"{lo}" if lo == hi else f"{lo}〜{hi}"
        raise InputError(f"inputs は{what}を {span} 個です（今は {n} 個）")
