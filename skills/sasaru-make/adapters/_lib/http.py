from __future__ import annotations

import ipaddress
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Protocol
from urllib.parse import urljoin, urlsplit

from .errors import ProviderError
from .keys import Secret, redact

REDIRECTS = (301, 302, 303, 307, 308)
MAX_REDIRECTS = 5


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

    def header(self, name: str) -> str | None:
        for k, v in self.headers.items():
            if k.lower() == name.lower():
                return v
        return None


class Transport(Protocol):
    def __call__(self, method: str, url: str, headers: dict, body: bytes | None, timeout: float) -> Response: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """urllib copies every header, keys included, to the redirect target. Client follows redirects itself."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def urllib_transport(method: str, url: str, headers: dict, body: bytes | None, timeout: float) -> Response:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with _opener.open(req, timeout=timeout) as r:
            return Response(r.status, r.read(), dict(r.headers))
    except urllib.error.HTTPError as e:
        return Response(e.code, e.read(), dict(e.headers or {}))


def require_public_https(url: str) -> None:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host:
        raise ProviderError(f"https でない URL は開きません: {parts.scheme}://{host}")
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".internal"):
        raise ProviderError(f"内部のホストは開きません: {host}")
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return
    raise ProviderError(f"IP アドレスの URL は開きません: {host}")


class Client:
    """HTTP for one provider. Sends the key only over https to that provider's exact API hosts."""

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
        parts = urlsplit(url)
        headers = {"User-Agent": "sasaru-make-adapters/0.1"}
        if parts.scheme == "https" and (parts.hostname or "").lower() in self._auth_hosts:
            headers.update(self._auth_headers(self._key))
        headers.update(extra or {})
        return headers

    def submit_json(self, url: str, payload: dict, headers: dict | None = None) -> Response:
        """The one paid call. Never retried and never redirected: a lost reply may still have been billed."""
        require_public_https(url)
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
        for _ in range(MAX_REDIRECTS + 1):
            require_public_https(url)
            try:
                r = self._transport("GET", url, self._headers_for(url, headers), None, self._timeout)
            except OSError as e:
                raise ProviderError(f"GET {urlsplit(url).hostname} に届きませんでした: {redact(str(e))}") from None
            location = r.header("location")
            if r.status not in REDIRECTS or not location:
                return r
            url = urljoin(url, location)
        raise ProviderError(f"リダイレクトが {MAX_REDIRECTS} 回を超えました")


def check(r: Response, what: str) -> Response:
    if isinstance(r.status, int) and 200 <= r.status < 300:
        return r
    snippet = redact(r.body[:300].decode("utf-8", "replace"))
    raise ProviderError(f"{what}が HTTP {r.status} で失敗: {snippet}")
