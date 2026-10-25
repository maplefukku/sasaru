from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADAPTERS))

from _lib import keys  # noqa: E402
from _lib.cli import main  # noqa: E402
from _lib.http import Response  # noqa: E402

FAKE_KEY = "sk-test-FAKEKEY-0123456789abcdef"
KEY_ENVS = ("XAI_API_KEY", "RUNWAYML_API_SECRET", "GEMINI_API_KEY", "GOOGLE_API_KEY", "BFL_API_KEY",
            "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "SASARU_HOME")


def resp(status: int = 200, body=b"", headers: dict | None = None) -> Response:
    if isinstance(body, (dict, list)):
        body = json.dumps(body).encode()
        headers = {"Content-Type": "application/json", **(headers or {})}
    return Response(status, body, headers or {})


class FakeTransport:
    """Replays canned responses in order and records every request. Nothing leaves the process."""

    def __init__(self, *steps):
        self.steps = list(steps)
        self.calls: list[dict] = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        if not self.steps:
            raise AssertionError(f"unexpected request {method} {url}")
        want_method, want_prefix, result = self.steps.pop(0)
        assert method == want_method and url.startswith(want_prefix), f"got {method} {url}, want {want_method} {want_prefix}"
        if isinstance(result, Exception):
            raise result
        return result

    def json_body(self, i: int) -> dict:
        return json.loads(self.calls[i]["body"])


def no_network(method, url, headers, body, timeout):
    raise AssertionError(f"network used: {method} {url}")


class AdapterCase(unittest.TestCase):
    def setUp(self) -> None:
        self._env = {k: os.environ.pop(k) for k in KEY_ENVS if k in os.environ}
        self.tmp = Path(tempfile.mkdtemp(prefix="sasaru-adapters-"))
        self.out = self.tmp / "out"
        keys._loaded.clear()

    def tearDown(self) -> None:
        for k in KEY_ENVS:
            os.environ.pop(k, None)
        os.environ.update(self._env)
        keys._loaded.clear()

    def file(self, name: str, data: bytes = b"\x89PNG fake bytes") -> str:
        p = self.tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return str(p)

    def req(self, need: str, **fields) -> Path:
        data = {"need": need, "cutId": "cut-01", "beat": "b2", "durationSec": 5, "aspect": "9:16", "fps": 30,
                "inputs": []}
        data["text" if need == "tts" else "prompt"] = fields.pop("prompt", "rain on a window, slow push in")
        data.update(fields)
        p = self.tmp / f"req-{need}.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return p

    def call(self, need: str, *argv: str, transport=no_network, clock=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        kwargs = {"transport": transport, "stdout": stdout, "stderr": stderr, "sleep": lambda s: None}
        if clock is not None:
            kwargs["clock"] = clock
        code = main(need, list(argv), **kwargs)
        return code, stdout.getvalue(), stderr.getvalue()

    def quote(self, need: str, req: Path, *extra: str) -> dict:
        code, out, err = self.call(need, "quote", "--request", str(req), *extra)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def run_paid(self, need: str, req: Path, transport, cap: str = "5", *extra: str, clock=None):
        return self.call(need, "run", "--request", str(req), "--out", str(self.out), "--cap-usd", cap, "--yes",
                         *extra, transport=transport, clock=clock)

    def assert_no_key_leak(self, *texts: str) -> None:
        for t in texts:
            self.assertNotIn(FAKE_KEY, t)
