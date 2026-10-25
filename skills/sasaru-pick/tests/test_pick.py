# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7", "jsonschema>=4.18,<5"]
# ///
"""Run pick.py against the fixture playbooks. uv run --script skills/sasaru-pick/tests/test_pick.py"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PICK = HERE.parent / "scripts" / "pick.py"
LIB = HERE / "fixtures" / "playbooks"
BROKEN = HERE / "fixtures" / "broken"


def run(brief: dict | str, *libs: Path, env: dict | None = None, cwd: Path | None = None) -> tuple[int, dict]:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(brief if isinstance(brief, str) else json.dumps(brief, ensure_ascii=False))
    args = [sys.executable, str(PICK), "--brief", f.name]
    for lib in libs:
        args += ["--library", str(lib)]
    full_env = {k: v for k, v in os.environ.items() if k != "SASARU_HOME"} | (env or {})
    proc = subprocess.run(args, check=False, capture_output=True, text=True, env=full_env, cwd=cwd)
    Path(f.name).unlink()
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode, json.loads(proc.stdout)


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def study_tip_without_talking_head():
    _, r = run({"content": {"kind": "勉強法のコツ", "message": "25分で区切ると続く"}, "audience": "資格勉強中の社会人", "durationSec": 12}, LIB, BROKEN)
    assert r["status"] == "picked", r
    assert r["pick"]["id"] == "list-countdown-captions"
    assert r["pick"]["route"]["id"] == "code-motion" and r["pick"]["route"]["costUsdPerVideo"]["max"] == 0
    excluded = {e["id"]: e["blockedBy"] for e in r["excluded"]}
    assert any("カメラに喋る" in t for t in excluded["talking-confession"])
    assert len(r["skipped"]) == 2


@case
def empty_library():
    with tempfile.TemporaryDirectory() as d:
        _, r = run({"content": {"kind": "勉強法のコツ"}}, Path(d))
    assert r["status"] == "empty-library", r


@case
def library_dir_missing():
    _, r = run({"content": {"kind": "勉強法のコツ"}}, HERE / "no-such-dir")
    assert r["status"] == "empty-library" and r["libraries"] == [], r


@case
def only_broken_playbooks():
    _, r = run({"content": {"kind": "勉強法のコツ"}}, BROKEN)
    assert r["status"] == "empty-library" and len(r["skipped"]) == 2, r


@case
def no_content():
    _, r = run({"durationSec": 15}, LIB)
    assert r["status"] == "need-info"
    assert [m["field"] for m in r["missing"]] == ["content.kind", "content.message"]


@case
def routine_needs_assets():
    _, r = run({"content": {"kind": "朝のルーティン"}}, LIB)
    assert r["status"] == "need-info", r
    assert [m["field"] for m in r["missing"]] == ["assets", "budgetUsd"]
    assert {"id": "hands-desk-broll", "fit": 1.0, "route": "caption-over-footage", "assets": ["own-footage"]} in r["unlocks"]
    assert {"id": "hands-desk-broll", "fit": 1.0, "route": "t2v", "assets": ["t2v"], "budgetUsdAtLeast": 2} in r["unlocks"]


@case
def routine_with_own_footage():
    _, r = run({"content": {"kind": "朝のルーティン"}, "assets": ["own-footage"], "budgetUsd": 0}, LIB)
    assert r["status"] == "picked" and r["pick"]["id"] == "hands-desk-broll", r
    assert r["pick"]["route"]["default"] is True


@case
def talking_reference_when_allowed():
    _, r = run({"content": {"kind": "一人語りの体験談"}, "assets": ["own-footage"], "allowTalkingHead": True}, LIB)
    assert r["status"] == "picked" and r["pick"]["id"] == "talking-confession", r
    assert r["pick"]["route"]["id"] == "caption-over-footage"
    assert any("参照は人がカメラに喋る型" in t for t in r["reasons"])


@case
def audience_breaks_a_content_tie():
    brief = {"content": {"kind": "勉強法のコツ"}, "assets": ["own-footage"], "allowTalkingHead": True}
    _, r = run(brief, LIB)
    assert r["pick"]["id"] == "list-countdown-captions", r
    _, r = run(brief | {"audience": "資格勉強中の社会人"}, LIB)
    assert r["status"] == "picked" and r["pick"]["id"] == "talking-confession", r
    assert r["pick"]["matchedAudience"] == "資格勉強中の社会人"
    assert any("audience" in t for t in r["reasons"])


@case
def talking_reference_blocked_by_default():
    _, r = run({"content": {"kind": "一人語りの体験談"}, "assets": ["own-footage"]}, LIB)
    assert r["status"] == "no-fit", r
    assert "talking-confession" not in r["missing"][0]["options"]


@case
def named_talking_reference_after_ingest():
    _, r = run({"playbook": "talking-confession", "assets": ["own-footage"]}, LIB)
    assert r["status"] == "picked" and r["pick"]["id"] == "talking-confession", r
    assert r["pick"]["route"]["id"] == "caption-over-footage" and r["pick"]["route"]["default"] is True


@case
def named_playbook_missing():
    _, r = run({"playbook": "no-such-type"}, LIB)
    assert r["status"] == "need-info" and r["missing"][0]["field"] == "playbook", r
    assert "hands-desk-broll" in r["missing"][0]["options"]


@case
def talking_route_never_without_permission():
    brief = {"playbook": "talking-confession", "assets": ["r2v", "tts"], "budgetUsd": 10}
    _, r = run(brief, LIB)
    assert r["status"] == "no-match", r
    _, r = run(brief | {"allowTalkingHead": True}, LIB)
    assert r["status"] == "picked" and r["pick"]["route"]["id"] == "r2v-talking", r
    assert r["pick"]["route"]["costUsdPerVideo"]["asOf"] == "2026-10-25"
    assert any("喋る人を出す" in t for t in r["reasons"])


@case
def sasaru_home_library():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
        shutil.copytree(LIB, Path(home) / "playbooks")
        _, r = run({"content": {"kind": "勉強法のコツ"}}, env={"SASARU_HOME": home}, cwd=Path(cwd))
    assert r["status"] == "picked" and r["pick"]["file"].startswith(home), r


@case
def paid_alternative_route_within_budget():
    brief = {"content": {"kind": "アプリの使い方"}, "durationSec": {"min": 25, "max": 35}, "assets": ["image-gen", "tts"], "budgetUsd": 1}
    _, r = run(brief, LIB)
    assert r["status"] == "picked" and r["pick"]["id"] == "screen-demo-voiceover", r
    route = r["pick"]["route"]
    assert route["id"] == "image-gen-stills" and route["default"] is False and route["paidApi"] is True


@case
def paid_route_over_budget():
    brief = {"content": {"kind": "アプリの使い方"}, "durationSec": 30, "assets": ["image-gen", "tts"], "budgetUsd": 0.2}
    _, r = run(brief, LIB)
    assert r["status"] == "no-match", r
    blocked = {e["id"]: e["blockedBy"] for e in r["excluded"]}["screen-demo-voiceover"]
    assert any("上限 0.2 USD" in t for t in blocked)


@case
def wrong_aspect():
    _, r = run({"content": {"kind": "勉強法のコツ"}, "aspect": "16:9"}, LIB)
    assert r["status"] == "no-match", r


@case
def weak_fit_asks_instead_of_guessing():
    _, r = run({"content": {"kind": "勉強記録", "message": "毎朝の勉強の記録"}}, LIB)
    assert r["status"] == "need-info", r
    assert r["unlocks"][0]["id"] == "hands-desk-broll"


@case
def better_type_behind_unanswered_assets():
    _, r = run({"content": {"kind": "勉強記録"}, "tags": ["study"]}, LIB)
    assert r["status"] == "picked" and r["pick"]["id"] == "list-countdown-captions", r
    assert r["betterIfAnswered"]["unlocks"][0]["id"] == "hands-desk-broll"


@case
def bad_brief():
    code, r = run("assets: [drone]\n", LIB)
    assert code == 2 and r["status"] == "bad-brief", r


def main() -> int:
    failed = 0
    for fn in CASES:
        try:
            fn()
            print(f"ok   {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
