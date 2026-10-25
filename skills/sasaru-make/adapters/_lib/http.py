from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Protocol
from urllib.parse import urlsplit

from .errors import ProviderError
from .keys import Secret, redact


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    headers: dict

    def json(self):
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProviderError(f"JSON でない応答: {redact(self.body[:200].decode('utf-8', 'replace'))}") from None


class Transport(Protocol):
    def __call__(self, method: str, url: str, headers: dict, body: bytes | None, timeout: float) -> Response: ...


def urllib_transport(method: str, url: str, headers: dict, body: bytes | None, timeout: float) -> Response:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return Response(r.status, r.read(), dict(r.headers))
    except urllib.error.HTTPError as e:
        return Response(e.code, e.read(), dict(e.headers or {}))


class Client:
    """HTTP for one provider. Sends the key only to that provider's hosts."""

    def __init__(
        self,
        transport: Transport,
        *,
        auth_hosts: tuple[str, ...],
        auth_headers: Callable[[Secret], dict],
        key: Secret,
        timeout: float = 120.0,
    ) -> None:
        self._transport = transport
        self._auth_hosts = auth_hosts
        self._auth_headers = auth_headers
        self._key = key
        self._timeout = timeout

    def _headers_for(self, url: str, extra: dict | None) -> dict:
        host = (urlsplit(url).hostname or "").lower()
        headers = {"User-Agent": "sasaru-make-adapters/0.1"}
        if any(host == h or host.endswith("." + h) for h in self._auth_hosts):
            headers.update(self._auth_headers(self._key))
        headers.update(extra or {})
        return headers

    def _send(self, method: str, url: str, body: bytes | None, headers: dict | None) -> Response:
        try:
            return self._transport(method, url, self._headers_for(url, headers), body, self._timeout)
        except OSError as e:
            raise ProviderError(f"{method} {_host(url)} に届きませんでした: {redact(str(e))}") from None

    def submit_json(self, url: str, payload: dict, headers: dict | None = None) -> Response:
        """The one paid call. Never retried: a lost reply may still have been billed."""
        body = json.dumps(payload).encode("utf-8")
        h = {"Content-Type": "application/json", **(headers or {})}
        try:
            r = self._transport("POST", url, self._headers_for(url, h), body, self._timeout)
        except OSError as e:
            raise ProviderError(
                f"送信の応答が届きませんでした（{redact(str(e))}）。課金された可能性があるので再送しません。"
                "プロバイダの管理画面でジョブを確かめてください"
            ) from None
        return check(r, "送信")

    def get(self, url: str, headers: dict | None = None) -> Response:
        return self._send("GET", url, None, headers)


def check(r: Response, what: str) -> Response:
    if 200 <= r.status < 300:
        return r
    snippet = redact(r.body[:300].decode("utf-8", "replace"))
    raise ProviderError(f"{what}が HTTP {r.status} で失敗: {snippet}")


def _host(url: str) -> str:
    return urlsplit(url).hostname or "?"
