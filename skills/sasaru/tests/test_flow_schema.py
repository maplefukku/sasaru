# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7", "jsonschema>=4.23,<5"]
# ///
"""Watched-to-the-end fields pass plan.py. An empty story does not.

verbalization.picture and verbalization.words follow their procedures:
second 0 has no enter or leave, an undecided point is 決められない, and an
unmeasured word box is 未計測 rather than a constant or a copied glyph.
verbalization.accountPattern keeps the account headings and rejects a shot
list, a seconds table, a view count, a source-text key, and null.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "skills" / "sasaru-make" / "scripts" / "plan.py"
TEMPLATE = ROOT / "templates" / "playbook.md"
SCHEMA = json.loads((ROOT / "schema" / "playbook.schema.json").read_text(encoding="utf-8"))


class Yaml12Loader(yaml.SafeLoader):
    """YAML 1.2 booleans, matching plan.py, so yes/no/on stay strings."""


Yaml12Loader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag not in ("tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp")]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
Yaml12Loader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", __import__("re").compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF")
)


def load_frontmatter(text: str) -> dict:
    parts = text.split("---\n")
    if not text.startswith("---\n") or len(parts) < 3:
        raise SystemExit("template has no frontmatter")
    return yaml.load(parts[1], Loader=Yaml12Loader)


def errors_of(fm: dict) -> list[str]:
    validator = jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker())
    found = sorted(validator.iter_errors(fm), key=lambda e: list(e.path))
    return [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in found]


def playbook_text() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    return text.replace("id: replace-with-format-id", "id: flow-v4", 1)


def story_of(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("  story: "):
            return line[len("  story: ") :]
    raise SystemExit("template has no scenario.story")


def plan(text: str, cut: str) -> tuple[int, str, Path]:
    home = Path(tempfile.mkdtemp(prefix="sasaru-flow-"))
    path = home / "flow-v4.md"
    path.write_text(text, encoding="utf-8")
    content = home / "content.yaml"
    content.write_text(
        f"cut: {cut}\ndurationSec: 6\nbeats:\n  b1: {{ c1: ['完成'] }}\n  b2: {{ c1: ['着地'] }}\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(PLAN), str(path), str(content), "--home", str(home), "--no-quote"],
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stderr + proc.stdout, home / "cuts" / cut / "cut.json"


def expect_schema(fm: dict, ok: bool, label: str) -> bool:
    found = errors_of(fm)
    if ok and found:
        print(label, *found, sep="\n  ", file=sys.stderr)
        return False
    if not ok and not found:
        print(label, "expected a schema error", file=sys.stderr)
        return False
    return True


def main() -> int:
    text = playbook_text()
    base = load_frontmatter(text)
    if not expect_schema(base, True, "template"):
        return 1

    code, out, cut = plan(text, "flow-cut")
    if code != 0 or not cut.is_file():
        print(code, out, file=sys.stderr)
        return 1

    story = story_of(text)
    refused = {
        "empty": text.replace(f"  story: {story}", '  story: ""', 1),
        "null": text.replace(f"  story: {story}", "  story: null", 1),
        "missing": text.replace(f"scenario:\n  story: {story}\n", "", 1),
        "shots": text.replace(
            f"  story: {story}",
            "  story: |\n    1. 完成の名前を先に置く。\n    2. 普通の一手を止める。\n    3. ほどけた完成を残す。\n",
            1,
        ),
        "words": text.replace(
            f"  story: {story}",
            "  story: 完成の名前、普通の一手、画面の止まり、ほどけた着地、残る約束、指させる物、次の秒。",
            1,
        ),
    }
    for label, bad in refused.items():
        code, out, bad_cut = plan(bad, f"flow-cut-{label}")
        if code != 3 or bad_cut.exists():
            print(label, code, out, file=sys.stderr)
            return 1

    picture = base["verbalization"]["picture"]
    undecided = copy.deepcopy(base)
    undecided["verbalization"]["picture"][0]["inferred"]["pointAt"] = "決められない"
    if not expect_schema(undecided, True, "pointAt 決められない"):
        return 1

    operation = copy.deepcopy(base)
    operation["verbalization"]["picture"][0]["seen"]["camera"] = "パン"
    if not expect_schema(operation, False, "operation name in seen.camera"):
        return 1

    entered = copy.deepcopy(base)
    entered["verbalization"]["picture"][0]["seen"]["entered"] = "前の画は無いが、何かが入ったと書いた"
    if not expect_schema(entered, False, "second 0 entered"):
        return 1

    no_zero = copy.deepcopy(base)
    no_zero["verbalization"]["picture"] = [s for s in picture if s["sec"] != 0]
    if not expect_schema(no_zero, False, "picture without second 0"):
        return 1

    measured = copy.deepcopy(base)
    interval = measured["verbalization"]["words"]["intervals"][0]
    interval["capHeightRatio"] = 0.08
    interval["cx"] = 0.5
    interval["cy"] = 0.4
    if not expect_schema(measured, True, "measured word box"):
        return 1

    omitted = copy.deepcopy(base)
    for key in ("capHeightRatio", "cx", "cy"):
        del omitted["verbalization"]["words"]["intervals"][0][key]
    if not expect_schema(omitted, False, "omitted word box"):
        return 1

    constant = copy.deepcopy(base)
    constant["verbalization"]["words"]["intervals"][0]["capHeightRatio"] = None
    if not expect_schema(constant, False, "null word box"):
        return 1

    glyph = copy.deepcopy(base)
    glyph["verbalization"]["words"]["intervals"][0]["text"] = "橋"
    if not expect_schema(glyph, False, "copied glyph"):
        return 1

    pattern = base["verbalization"]["accountPattern"]
    shot_list = copy.deepcopy(base)
    shot_list["verbalization"]["accountPattern"]["物語の機械"] = (
        "1. 完成の名前を先に置く。\n2. 普通の一手を止める。\n3. ほどけた完成を残す。\n"
    )
    if not expect_schema(shot_list, False, "account pattern shot list"):
        return 1

    seconds = copy.deepcopy(base)
    seconds["verbalization"]["accountPattern"]["物語の機械"] = (
        "0秒: 完成の名前を置く。\n1秒: 普通の一手を止める。\n2秒: ほどけた完成を残す。\n"
    )
    if not expect_schema(seconds, False, "account pattern seconds table"):
        return 1

    views = copy.deepcopy(base)
    views["verbalization"]["accountPattern"]["繰り返さないところ"] = (
        "本ごとに変わるのは物の種類だけである。再生数は測っていないので、型の根拠にはしない。"
    )
    if not expect_schema(views, False, "account pattern view count"):
        return 1

    missing_open = copy.deepcopy(base)
    del missing_open["verbalization"]["accountPattern"]["繰り返すところ"]["冒頭"]
    if not expect_schema(missing_open, False, "account pattern missing opening"):
        return 1

    copied_line = copy.deepcopy(base)
    copied_line["verbalization"]["accountPattern"]["text"] = pattern["物語の機械"]
    if not expect_schema(copied_line, False, "account pattern source key"):
        return 1

    nulled = copy.deepcopy(base)
    nulled["verbalization"]["accountPattern"] = None
    if not expect_schema(nulled, False, "null account pattern"):
        return 1

    absent = copy.deepcopy(base)
    absent["verbalization"]["words"]["missing"] = ["absent.mp4"]
    absent["verbalization"]["words"]["intervals"] = []
    if not expect_schema(absent, True, "missing video has no word intervals"):
        return 1

    skipped = copy.deepcopy(base)
    for beat in skipped["beats"]:
        if beat["role"] == "payoff":
            beat["role"] = "item"
    for key in ("verbalization", "spread", "scenario"):
        del skipped[key]
    if not expect_schema(skipped, True, "omit when the format is not watched to the end"):
        return 1

    print("ok flow schema")
    return 0


if __name__ == "__main__":
    sys.exit(main())
