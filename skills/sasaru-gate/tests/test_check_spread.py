# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7", "jsonschema>=4.21,<5"]
# ///
"""Spread checks: a payoff format needs three inferred mechanisms, and a view count fails."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schema" / "playbook.schema.json"
TEMPLATE = ROOT / "templates" / "playbook.md"
SCRIPTS = ROOT / "skills" / "sasaru-gate" / "scripts"
PICK = ROOT / "skills" / "sasaru-pick" / "scripts" / "pick.py"
sys.path.insert(0, str(SCRIPTS))

from check_spread import check_spread, split_playbook  # noqa: E402
from validate_playbook import validate  # noqa: E402

BRIDGE = {
    "plays": {
        "mechanism": "情報の隙間。到達点の名前は先に渡されていて、そこへの道が不可能に見えるので、未完了が注意を残す",
        "trigger": "完成した物の名前が先に出て、その完成が不可能に見える。見る人は変化を見届けるまで再生を閉じない",
        "basis": "inferred",
    },
    "comments": {
        "mechanism": "見えた変化の原因を、自分の文で埋めたい。因果の穴を自分で閉じる",
        "trigger": "変化は見せるが、作り方の名前は言わない。コメントがその穴の一文になる",
        "basis": "inferred",
    },
    "shares": {
        "mechanism": "相手がまだ持っていない到達を渡す社会的通貨",
        "trigger": "名前の付いた結末が、変化のあとでしか像にならない。送る人は、その到達を相手より先に持っている",
        "basis": "inferred",
    },
}


def base():
    text = TEMPLATE.read_text(encoding="utf-8")
    fm = split_playbook(text)
    body = text.split("---\n", 2)[2]
    return fm, body


def payoff():
    return {"beats": [{"id": "b1", "role": "hook"}, {"id": "b2", "role": "payoff"}]}


def no_payoff():
    return {"beats": [{"id": "b1", "role": "hook"}, {"id": "b2", "role": "item"}]}


body_of = [None]


def spread_errors(fm):
    result = check_spread(fm)
    errs, _, _ = validate(fm, body_of[0], schema_path=str(SCHEMA), template_path=str(TEMPLATE))
    return result, [e for e in errs if e.startswith("spread:")]


def case_bridge_shape_names_three_mechanisms():
    fm = payoff()
    fm["spreadPsychology"] = BRIDGE
    result = check_spread(fm)
    assert result["ok"], result
    reading = result["spreadPsychology"]
    assert reading["watchToEnd"] is True
    mechanisms = []
    for name in ("plays", "comments", "shares"):
        part = reading[name]
        assert part["basis"] == "inferred", part
        assert part["mechanism"] != part["trigger"]
        mechanisms.append(part["mechanism"])
    assert len(set(mechanisms)) == 3
    assert "不可能" in reading["plays"]["trigger"] and "変化" in reading["plays"]["trigger"]
    assert "名前" in reading["plays"]["trigger"]
    blob = json.dumps(reading, ensure_ascii=False)
    assert "再生数" not in blob and "views" not in blob.lower()


def case_omit_on_watch_to_end_fails():
    fm, _ = base()
    assert any(b["role"] == "payoff" for b in fm["beats"])
    fm.pop("spreadPsychology")
    result, wired = spread_errors(fm)
    assert not result["ok"], result
    assert any("watched to the end" in e for e in result["errors"]), result
    assert any("watched to the end" in e for e in wired), wired
    assert result["spreadPsychology"] == {"watchToEnd": True}
    bare = check_spread(payoff())
    assert not bare["ok"] and bare["spreadPsychology"] == {"watchToEnd": True}


def case_null_is_invalid():
    fm = payoff()
    fm["spreadPsychology"] = None
    result = check_spread(fm)
    assert not result["ok"], result
    assert any("null is not a reading" in e for e in result["errors"]), result
    fm["spreadPsychology"] = dict(BRIDGE)
    fm["spreadPsychology"]["comments"] = None
    result = check_spread(fm)
    assert not result["ok"] and any("comments" in e and "null" in e for e in result["errors"]), result


def case_view_count_is_not_the_field():
    fm = payoff()
    fm["spreadPsychology"] = json.loads(json.dumps(BRIDGE))
    fm["spreadPsychology"]["plays"]["mechanism"] = "120万回再生されたから止まる"
    result = check_spread(fm)
    assert not result["ok"], result
    assert any("view-count" in e for e in result["errors"]), result


def case_basis_must_be_inferred():
    fm = payoff()
    fm["spreadPsychology"] = json.loads(json.dumps(BRIDGE))
    fm["spreadPsychology"]["shares"]["basis"] = "measured"
    result = check_spread(fm)
    assert not result["ok"], result
    assert any("mark this inference as inferred" in e for e in result["errors"]), result


def case_omit_when_not_watch_to_end():
    result = check_spread(no_payoff())
    assert result["ok"], result
    assert result["spreadPsychology"] == {"watchToEnd": False}
    glued = check_spread(no_payoff() | {"spreadPsychology": None})
    assert not glued["ok"] and any("null is not a reading" in e for e in glued["errors"]), glued
    for path in (
        ROOT / "skills" / "sasaru-pick" / "tests" / "fixtures" / "playbooks" / "hands-desk-broll.md",
        ROOT / "skills" / "sasaru-pick" / "tests" / "fixtures" / "playbooks" / "screen-demo-voiceover.md",
    ):
        play = split_playbook(path.read_text(encoding="utf-8"))
        assert "spreadPsychology" not in play
        got = check_spread(play)
        assert got["ok"] and got["spreadPsychology"] == {"watchToEnd": False}, (path.name, got)


def case_shipped_playbooks_are_words():
    import jsonschema

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    paths = list((ROOT / "playbooks").glob("*.md"))
    paths.append(TEMPLATE)
    paths.append(ROOT / "skills" / "sasaru-make" / "examples" / "caption-only-smoke.md")
    paths.append(ROOT / "skills" / "sasaru-pick" / "tests" / "fixtures" / "playbooks" / "list-countdown-captions.md")
    paths.append(ROOT / "skills" / "sasaru-pick" / "tests" / "fixtures" / "playbooks" / "talking-confession.md")
    for path in paths:
        play = split_playbook(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(play), key=lambda e: list(e.absolute_path))
        assert not errors, (path.name, [f"{list(e.absolute_path)}: {e.message}" for e in errors[:4]])
        got = check_spread(play)
        assert got["ok"] and got["spreadPsychology"]["watchToEnd"] is True, (path.name, got)
        for name in ("plays", "comments", "shares"):
            assert got["spreadPsychology"][name]["basis"] == "inferred"


def case_pick_skips_a_view_count():
    text = (ROOT / "skills" / "sasaru-pick" / "tests" / "fixtures" / "playbooks" / "list-countdown-captions.md").read_text(encoding="utf-8")
    text = text.replace(
        "数えの未完了。約束した個数に届くまで、課題が閉じない",
        "120万回再生されたから止まる",
    )
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "list-countdown-captions.md"
        path.write_text(text, encoding="utf-8")
        brief = Path(d) / "brief.yaml"
        brief.write_text("content:\n  kind: 勉強法のコツ\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(PICK), "--brief", str(brief), "--library", d],
            check=False, capture_output=True, text=True,
        )
    result = json.loads(proc.stdout)
    assert proc.returncode == 0, proc.stderr
    assert result["status"] == "empty-library", result
    assert result["skipped"] and "view-count" in result["skipped"][0]["reason"], result["skipped"]


def case_cli_on_template():
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_spread.py"), "--playbook", str(TEMPLATE)],
        check=False, capture_output=True, text=True,
    )
    result = json.loads(proc.stdout)
    assert proc.returncode == 0 and result["ok"] and result["spreadPsychology"]["watchToEnd"] is True, result


def main() -> int:
    global body_of
    _, body = base()
    body_of = [body]
    tests = [
        case_bridge_shape_names_three_mechanisms,
        case_omit_on_watch_to_end_fails,
        case_null_is_invalid,
        case_view_count_is_not_the_field,
        case_basis_must_be_inferred,
        case_omit_when_not_watch_to_end,
        case_shipped_playbooks_are_words,
        case_pick_skips_a_view_count,
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
