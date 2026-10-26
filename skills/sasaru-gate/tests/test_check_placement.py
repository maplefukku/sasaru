# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7", "jsonschema>=4.21,<5"]
# ///
"""Placement checks: a product route needs words, a pitch subject fails, no slot may omit the field."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schema" / "playbook.schema.json"
TEMPLATE = ROOT / "templates" / "playbook.md"
SCRIPTS = ROOT / "skills" / "sasaru-gate" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_placement import check_placement, split_playbook  # noqa: E402
from validate_playbook import validate  # noqa: E402


def base():
    text = TEMPLATE.read_text(encoding="utf-8")
    fm = split_playbook(text)
    body = text.split("---\n", 2)[2]
    return fm, body


def placement_errors(fm, content=None):
    result = check_placement(fm, content)
    errs, _, _ = validate(fm, body_of[0], schema_path=str(SCHEMA), template_path=str(TEMPLATE))
    return result, [e for e in errs if e.startswith("placement:")]


body_of = [None]


def case_missing_on_product_route():
    fm, _ = base()
    fm["contentRoute"] = "in-world"
    fm.pop("productPlacement", None)
    result, wired = placement_errors(fm)
    assert not result["ok"], result
    assert any("product route" in e for e in result["errors"]), result
    assert any("product route" in e for e in wired), wired
    assert result["productPlacement"] == {"slot": False}
    assert "end-card" not in json.dumps(result["productPlacement"])


def case_pitch_subject():
    fm, _ = base()
    fm["subject"] = {"of": "reference-world", "words": "商品の機能を紹介してダウンロードして"}
    result, wired = placement_errors(fm)
    assert not result["ok"], result
    assert any("pitch-shaped" in e for e in result["errors"]), result
    assert any("pitch-shaped" in e for e in wired), wired
    script = check_placement(base()[0], {"subject": "商品の機能を紹介してダウンロードして"})
    assert not script["ok"] and any("content.subject" in e for e in script["errors"]), script


def case_omit_when_no_slot():
    fm, body = base()
    assert "productPlacement" not in fm
    result = check_placement(fm)
    errs, _, _ = validate(fm, body, schema_path=str(SCHEMA), template_path=str(TEMPLATE))
    assert result["ok"], result
    assert result["productPlacement"] == {"slot": False}
    assert not any(e.startswith("placement:") for e in errs), errs
    for path in sorted((ROOT / "playbooks").glob("*.md")):
        play = split_playbook(path.read_text(encoding="utf-8"))
        got = check_placement(play)
        assert got["ok"] and got["productPlacement"] == {"slot": False}, (path.name, got)


def case_null_is_not_an_end_card():
    fm, _ = base()
    fm["productPlacement"] = None
    result, _ = placement_errors(fm)
    assert not result["ok"], result
    assert any("null is not a placement" in e for e in result["errors"]), result
    assert result["productPlacement"].get("role") != "end-card"


def case_in_world_prop_passes():
    fm, _ = base()
    fm["contentRoute"] = "in-world"
    fm["productPlacement"] = {
        "beat": "b2",
        "role": "prop",
        "directness": "世界の小道具として一度だけ映し、名前は出さない",
    }
    result = check_placement(fm)
    assert result["ok"], result
    assert result["productPlacement"]["role"] == "prop"
    assert result["productPlacement"]["slot"] is True


def case_cli_on_template():
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_placement.py"), "--playbook", str(TEMPLATE)],
        check=False, capture_output=True, text=True,
    )
    result = json.loads(proc.stdout)
    assert proc.returncode == 0 and result["ok"] and result["productPlacement"] == {"slot": False}, result


def main() -> int:
    global body_of
    _, body = base()
    body_of = [body]
    tests = [
        case_missing_on_product_route,
        case_pitch_subject,
        case_omit_when_no_slot,
        case_null_is_not_an_end_card,
        case_in_world_prop_passes,
        case_cli_on_template,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - report every case
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}", file=sys.stderr)
        else:
            print(f"ok {fn.__name__}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
