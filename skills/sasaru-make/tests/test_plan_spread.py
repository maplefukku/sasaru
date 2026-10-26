# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7", "jsonschema>=4.23,<5"]
# ///
"""plan.py reads spreadPsychology and refuses a view-count claim."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "skills" / "sasaru-make" / "scripts" / "plan.py"
PLAYBOOK = ROOT / "skills" / "sasaru-make" / "examples" / "caption-only-smoke.md"
CONTENT = "cut: spread-cut\ndurationSec: 10\nbeats:\n  b1: { c1: ['問い'] }\n  b2: { c1: ['中'] }\n  b3: { c1: ['結び'] }\n"


def main() -> int:
    text = PLAYBOOK.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as home:
        path = Path(home) / "caption-only-smoke.md"
        path.write_text(text, encoding="utf-8")
        content = Path(home) / "content.yaml"
        content.write_text(CONTENT, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(PLAN), str(path), str(content), "--home", home, "--no-quote"],
            check=False, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr, proc.stdout, file=sys.stderr)
            return 1
        cut = json.loads((Path(home) / "cuts" / "spread-cut" / "cut.json").read_text(encoding="utf-8"))
        reading = cut.get("spreadPsychology") or {}
        if reading.get("watchToEnd") is not True:
            print(json.dumps(reading, ensure_ascii=False), file=sys.stderr)
            return 1
        mechanisms = []
        for name in ("plays", "comments", "shares"):
            part = reading.get(name) or {}
            if part.get("basis") != "inferred" or not part.get("mechanism") or not part.get("trigger"):
                print(name, json.dumps(part, ensure_ascii=False), file=sys.stderr)
                return 1
            if part["mechanism"] == part["trigger"]:
                print("same words", name, file=sys.stderr)
                return 1
            mechanisms.append(part["mechanism"])
        if len(set(mechanisms)) != 3:
            print(mechanisms, file=sys.stderr)
            return 1
        bad = path.with_name("caption-only-smoke.md")
        bad.write_text(text.replace(
            "問いの未完了。開いた問いが、答えの一句まで注意を残す",
            "120万回再生されたから止まる",
        ), encoding="utf-8")
        refused = subprocess.run(
            [sys.executable, str(PLAN), str(bad), str(content), "--home", home, "--no-quote"],
            check=False, capture_output=True, text=True,
        )
        if refused.returncode != 3 or "view-count" not in refused.stderr:
            print(refused.returncode, refused.stderr, refused.stdout, file=sys.stderr)
            return 1
        if (Path(home) / "cuts" / "spread-cut" / "cut.json").read_text(encoding="utf-8").find("120万回") != -1:
            print("view count was written into the earlier plan", file=sys.stderr)
            return 1
    print("ok plan spread")
    return 0


if __name__ == "__main__":
    sys.exit(main())
