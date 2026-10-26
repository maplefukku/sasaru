# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7", "jsonschema>=4.23,<5"]
# ///
"""plan.py reads productPlacement and does not invent an end card or an explainer."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "skills" / "sasaru-make" / "scripts" / "plan.py"
PLAYBOOK = ROOT / "skills" / "sasaru-make" / "examples" / "caption-only-smoke.md"


def run(content: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as home, tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as fh:
        fh.write(content)
        content_path = fh.name
    proc = subprocess.run(
        [sys.executable, str(PLAN), str(PLAYBOOK), content_path, "--home", home, "--no-quote"],
        check=False, capture_output=True, text=True,
    )
    return proc.returncode, proc.stderr + proc.stdout


def main() -> int:
    code, out = run("cut: pitch-cut\nsubject: 商品の機能を紹介してダウンロードして\n")
    if code != 3 or "pitch-shaped" not in out:
        print(out, file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as home:
        content = "cut: slot-absent\ndurationSec: 10\nbeats:\n  b1: { c1: ['問い'] }\n  b2: { c1: ['中'] }\n  b3: { c1: ['結び'] }\n"
        path = Path(home) / "content.yaml"
        path.write_text(content, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(PLAN), str(PLAYBOOK), str(path), "--home", home, "--no-quote"],
            check=False, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr, proc.stdout, file=sys.stderr)
            return 1
        cut = json.loads((Path(home) / "cuts" / "slot-absent" / "cut.json").read_text(encoding="utf-8"))
        if cut.get("productPlacement") != {"slot": False}:
            print(json.dumps(cut.get("productPlacement"), ensure_ascii=False), file=sys.stderr)
            return 1
        blob = json.dumps(cut["cards"], ensure_ascii=False)
        if "エンドカード" in blob or "ダウンロード" in blob:
            print(blob, file=sys.stderr)
            return 1
    code, out = run("cut: extra-card\nendCard: 名前を出す\n")
    if code != 3 or "endCard" not in out:
        print(out, file=sys.stderr)
        return 1
    print("ok plan placement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
