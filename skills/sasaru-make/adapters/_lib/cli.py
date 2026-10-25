from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Callable, TextIO

from . import gates, keys, registry
from .errors import AdapterError, InputError, EXIT_INPUT, EXIT_OK, EXIT_PROVIDER
from .http import Transport, urllib_transport
from .provider import RunContext
from .request import load


def _parser(need: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=f"{need.replace('-', '_')}.py",
        description=f"sasaru-make の {need} アダプタ。quote は課金しない。run は --yes と --cap-usd が両方あるときだけ送る。",
    )
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("quote", help="見積もりだけ（課金しない）")
    q.add_argument("--request", required=True, type=Path)
    q.add_argument("--provider")
    r = sub.add_parser("run", help="課金する送信")
    r.add_argument("--request", required=True, type=Path)
    r.add_argument("--out", required=True, type=Path)
    r.add_argument("--cap-usd", type=float)
    r.add_argument("--yes", action="store_true")
    r.add_argument("--provider")
    r.add_argument("--timeout-sec", type=float, default=900.0)
    sub.add_parser("providers", help="入っているプロバイダと既定")
    return p


def main(
    need: str,
    argv: list[str] | None = None,
    *,
    transport: Transport = urllib_transport,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> int:
    def err(msg: str) -> None:
        print(f"{need}: {keys.redact(msg)}", file=stderr)

    def out(obj: dict | list) -> None:
        print(json.dumps(obj, ensure_ascii=False), file=stdout)

    try:
        args = _parser(need).parse_args(argv)
    except SystemExit as e:
        return EXIT_OK if e.code == 0 else EXIT_INPUT

    try:
        if args.command == "providers":
            out([dict(cls().describe(), default=(i == 0)) for i, cls in enumerate(registry.PROVIDERS[need])])
            return EXIT_OK

        req = load(args.request)
        if req.need != need:
            raise InputError(f"req.json の need は {req.need} で、このアダプタは {need} です")
        provider = registry.resolve(need, args.provider or req.provider)
        gates.check_inputs_are_not_reference(req)
        gates.check_people(req)
        provider.validate(req)
        quote = provider.quote(req)

        if args.command == "quote":
            out(quote.to_json())
            return EXIT_OK

        gates.check_spend(quote, yes=args.yes, cap_usd=args.cap_usd)
        keys.read(*provider.env_keys)
        ctx = RunContext(out_dir=args.out, transport=transport, poll_timeout_sec=args.timeout_sec,
                         sleep=sleep, clock=clock, log=err)
        err(f"{provider.id} に送信します（見積もりの上限 {quote.usd_max:.4f} USD、cap {args.cap_usd:.4f} USD）")
        files = provider.run(req, ctx)
        out({"files": [str(f) for f in files], "usd": quote.usd_max, "provider": provider.id})
        return EXIT_OK
    except AdapterError as e:
        err(str(e))
        return e.exit_code
    except Exception as e:  # noqa: BLE001 - last line of defence; message is redacted, no traceback
        err(f"想定外のエラー {type(e).__name__}: {e}")
        return EXIT_PROVIDER
