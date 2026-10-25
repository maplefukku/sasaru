# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7", "jsonschema>=4.21,<5"]
# ///
"""Check one playbook file against the schema, the template, and the source wording. Local only.

Usage: uv run --script validate_playbook.py <playbook.md> [--work <work_dir>] [--schema <schema.json>] [--template <playbook.md>]
<work_dir> is the ingest folder that holds source-text.json. Without --work, <playbooks>/../work/<id>/ is tried.
Prints one JSON object. Exit 0 pass, 2 unreadable input, 3 check failed.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA = ROOT / "schema" / "playbook.schema.json"
DEFAULT_TEMPLATE = ROOT / "templates" / "playbook.md"
FALLBACK_HEADINGS = [
    "構成と尺", "フック", "ビート", "テロップ", "カメラとトランジションとズーム", "BGM と効果音", "なぜ伸びるか",
    "差し替える場所", "制作ルート", "編集の器とフォント", "素材の権利", "費用の目安", "測ったことと推論",
]
# The schema says null is "not measured" for these. Elsewhere null may also mean "none".
NULL_IS_UNMEASURED = ("capHeightRatio", "minHoldSec", "levelDbUnderVoice")
LAYER_NULLABLE = ("capHeightRatio", "minHoldSec", "position.cx", "position.cy", "leadSec")
CJK_RUN = 6
LATIN_WORDS = 3
CJK = r"\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f"
PLATFORM_URL = re.compile(r"https?://(www\.)?(instagram\.com|tiktok\.com|youtube\.com|youtu\.be)/", re.I)
HANDLE = re.compile(r"(?<![\w.])@[A-Za-z0-9_.]{3,}")


def dates_to_str(obj):
    """safe_load turns ingestedAt and asOf into date objects; the schema wants ISO strings."""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: dates_to_str(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [dates_to_str(v) for v in obj]
    return obj


def split_playbook(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("no YAML frontmatter between --- lines")
    return dates_to_str(yaml.safe_load(m.group(1))), m.group(2)


def load_playbook(path):
    return split_playbook(Path(path).read_text(encoding="utf-8"))


def get_path(obj, dotted):
    """Resolve a dotted path. A list step may be an index ([0]) or an item id (captions.c1, beats.b2)."""
    cur = obj
    for part in dotted.split("."):
        m = re.fullmatch(r"([^\[\]]+)((\[\d+\])*)", part)
        if not m:
            raise KeyError(dotted)
        key = m.group(1)
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        elif isinstance(cur, list):
            hit = [it for it in cur if isinstance(it, dict) and it.get("id") == key]
            if not hit:
                raise KeyError(dotted)
            cur = hit[0]
        else:
            raise KeyError(dotted)
        for idx in re.findall(r"\[(\d+)\]", m.group(2)):
            if not isinstance(cur, list) or int(idx) >= len(cur):
                raise KeyError(dotted)
            cur = cur[int(idx)]
    return cur


def has_path(obj, dotted):
    try:
        get_path(obj, dotted)
        return True
    except KeyError:
        return False


def headings(body, level):
    mark = "#" * level + " "
    return [ln[len(mark):].strip() for ln in body.splitlines() if ln.startswith(mark)]


def template_headings(template):
    try:
        return headings(load_playbook(template)[1], 2) or FALLBACK_HEADINGS
    except (OSError, ValueError):
        return FALLBACK_HEADINGS


def route_subheadings(body):
    out, inside = [], False
    for ln in body.splitlines():
        if ln.startswith("## "):
            inside = ln[3:].strip() == "制作ルート"
        elif inside and ln.startswith("### "):
            out.append(ln[4:].strip())
    return out


def covered(paths, dotted):
    return any(dotted == p or dotted.startswith(p + ".") for p in paths)


def strings_in(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings_in(v)


def normalize(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def cjk_runs(s):
    """Every CJK_RUN-long window of consecutive CJK characters, punctuation and spaces removed."""
    out = set()
    for run in re.findall(f"[{CJK}]+", re.sub(r"[\s、。，．・「」『』（）()！？!?ー〜…]", "", s)):
        for i in range(len(run) - CJK_RUN + 1):
            out.add(run[i:i + CJK_RUN])
    return out


def latin_grams(s):
    words = re.findall(r"[a-z0-9']+", normalize(s))
    return {" ".join(words[i:i + LATIN_WORDS]) for i in range(len(words) - LATIN_WORDS + 1)}


def wording_check(playbook_text, source_text):
    src = list(strings_in(source_text))
    cj, la = set(), set()
    for s in src:
        cj |= cjk_runs(s)
        la |= latin_grams(s)
    pb_cj = cjk_runs(playbook_text)
    pb_la = latin_grams(playbook_text)
    return sorted(cj & pb_cj), sorted(la & pb_la), len(src)


def find_source_text(playbook_path, work, pid):
    cands = []
    if work:
        cands.append(Path(work) / "source-text.json")
    if playbook_path is not None and pid:
        cands.append(Path(playbook_path).resolve().parent.parent / "work" / pid / "source-text.json")
    return next((c for c in cands if c.is_file()), None)


def validate(fm, body, path=None, schema_path=DEFAULT_SCHEMA, template_path=DEFAULT_TEMPLATE, work=None, full_text=None):
    """Return (errors, warnings, wording) where wording reports the source-text check."""
    errors, warnings = [], []
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    for e in sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(fm), key=lambda e: list(e.absolute_path)):
        where = ".".join(str(p) for p in e.absolute_path) or "(root)"
        errors.append(f"schema: {where}: {e.message}")
    wording = {"status": "not-applicable"}
    if not isinstance(fm, dict):
        return errors, warnings, wording

    if path is not None and fm.get("id") and Path(path).stem != fm["id"]:
        errors.append(f"id '{fm['id']}' differs from file name '{Path(path).stem}'")

    want, got = template_headings(template_path), headings(body, 2)
    if got != want:
        missing = [h for h in want if h not in got]
        extra = [h for h in got if h not in want]
        detail = (["missing " + ", ".join(missing)] if missing else []) + (["extra " + ", ".join(extra)] if extra else [])
        errors.append("body headings: " + ("; ".join(detail) or "order differs from the template"))

    route_ids = [r.get("id") for r in fm.get("routes") or [] if isinstance(r, dict)]
    if route_subheadings(body) != route_ids:
        errors.append(f"制作ルート subheadings {route_subheadings(body)} differ from routes order {route_ids}")

    dur = (fm.get("format") or {}).get("durationSec") or {}
    if isinstance(dur.get("min"), (int, float)) and isinstance(dur.get("max"), (int, float)) and dur["min"] > dur["max"]:
        errors.append("format.durationSec.min is above max")

    beats = [b for b in fm.get("beats") or [] if isinstance(b, dict)]
    beat_ids = {b.get("id") for b in beats}
    prev_out = None
    for i, b in enumerate(beats):
        if b.get("id") != f"b{i + 1}":
            warnings.append(f"beats[{i}].id is '{b.get('id')}', expected 'b{i + 1}'")
        tin, tout = b.get("tIn"), b.get("tOut")
        if isinstance(tin, (int, float)) and isinstance(tout, (int, float)):
            if tout <= tin:
                errors.append(f"beat {b.get('id')}: tOut {tout} is not after tIn {tin}")
            if prev_out is not None and tin < prev_out - 1e-6:
                errors.append(f"beat {b.get('id')} overlaps the previous beat")
            elif prev_out is not None and tin > prev_out + 1e-6:
                warnings.append(f"beat {b.get('id')} leaves a gap of {round(tin - prev_out, 3)} s")
            prev_out = tout
    if beats and beats[0].get("tIn") not in (0, 0.0):
        warnings.append("the first beat does not start at 0")
    ref = dur.get("reference")
    if isinstance(ref, (int, float)) and prev_out is not None and abs(prev_out - ref) > 1e-6:
        warnings.append(f"the last beat ends at {prev_out}, not at format.durationSec.reference {ref}")
    if not isinstance(ref, (int, float)):
        warnings.append("format.durationSec.reference is missing; the cut check scales beats to the last beat's tOut instead")

    def check_at(where, at):
        if isinstance(at, dict) and at.get("beat") not in beat_ids:
            errors.append(f"{where}.beat '{at.get('beat')}' is not a beat id")
        elif isinstance(at, dict):
            b = next(x for x in beats if x.get("id") == at["beat"])
            if isinstance(b.get("tIn"), (int, float)) and isinstance(b.get("tOut"), (int, float)) and at.get("offsetSec", 0) > b["tOut"] - b["tIn"] + 1e-6:
                warnings.append(f"{where}.offsetSec runs past the end of beat {at['beat']}")

    cam = fm.get("camera") or {}
    for i, mv in enumerate(cam.get("moves") or []):
        if isinstance(mv, dict) and mv.get("beat") not in beat_ids:
            errors.append(f"camera.moves[{i}].beat '{mv.get('beat')}' is not a beat id")
    for key in ("zooms", "transitions"):
        for i, it in enumerate(cam.get(key) or []):
            check_at(f"camera.{key}[{i}].at", (it or {}).get("at"))
    aud = fm.get("audio") or {}
    for i, it in enumerate(aud.get("sfx") or []):
        if isinstance(it, dict) and "at" in it:
            check_at(f"audio.sfx[{i}].at", it["at"])
    if (aud.get("bgm") or {}).get("entersAt"):
        check_at("audio.bgm.entersAt", aud["bgm"]["entersAt"])

    layers = [c for c in fm.get("captions") or [] if isinstance(c, dict)]
    lids = [c.get("id") for c in layers]
    if len(set(lids)) != len(lids):
        errors.append("captions: layer ids repeat")
    ev = fm.get("evidence") or {}
    groups = {k: ev.get(k) or [] for k in ("measured", "inferred", "unmeasured")}
    for c in layers:
        lid = c.get("id")
        for bid in c.get("beats") or []:
            if bid not in beat_ids:
                errors.append(f"captions.{lid}.beats names '{bid}', which is not a beat id")
        cpc = c.get("charsPerCard") or {}
        if isinstance(cpc.get("min"), int) and isinstance(cpc.get("max"), int) and cpc["min"] > cpc["max"]:
            errors.append(f"captions.{lid}.charsPerCard.min is above max")
        if c.get("show") == "before-onset" and c.get("leadSec") is None and not covered(groups["unmeasured"], f"captions.{lid}.leadSec"):
            errors.append(f"captions.{lid}: show before-onset needs leadSec, or leadSec listed as unmeasured")
        for field in LAYER_NULLABLE:
            p = f"captions.{lid}.{field}"
            if has_path(fm, p) and get_path(fm, p) is None and not covered(groups["unmeasured"], p):
                if field in NULL_IS_UNMEASURED:
                    errors.append(f"'{p}' is null but not listed in evidence.unmeasured")
                elif field != "leadSec":
                    warnings.append(f"'{p}' is null and not in evidence.unmeasured; the cut check reads it as 'no target'")
    lvl = (aud.get("bgm") or {}).get("levelDbUnderVoice", "absent")
    if lvl is None and not covered(groups["unmeasured"], "audio.bgm.levelDbUnderVoice"):
        warnings.append("'audio.bgm.levelDbUnderVoice' is null but not listed in evidence.unmeasured")

    seen = {}
    for g, paths in groups.items():
        for p in paths:
            if not has_path(fm, p):
                errors.append(f"evidence.{g}: '{p}' is not a path in this frontmatter")
            if p in seen:
                errors.append(f"evidence: '{p}' is listed under both {seen[p]} and {g}")
            seen[p] = g
    for p in groups["measured"]:
        if has_path(fm, p) and get_path(fm, p) is None:
            errors.append(f"evidence.measured: '{p}' is null")
    src = fm.get("source") or {}
    if groups["measured"] and not src.get("measuredFiles"):
        errors.append("evidence.measured is not empty but source.measuredFiles is 0")
    if src.get("kind") == "hand-written" and (src.get("rightsTier") != "none" or src.get("measuredFiles")):
        warnings.append("source.kind hand-written usually has rightsTier none and measuredFiles 0")

    text = full_text if full_text is not None else body
    if PLATFORM_URL.search(text):
        warnings.append("the file links to a short-video platform page; a playbook must not name the source work")
    if HANDLE.search(text):
        warnings.append("the file contains an @handle; a playbook must not name the creator")

    if src.get("kind") == "ingested":
        st_path = find_source_text(path, work, fm.get("id"))
        if st_path is None:
            wording = {"status": "unmeasured", "note": "no source-text.json; an ingested playbook without it does not pass"}
            errors.append("wording: source-text.json not found (pass --work <work_dir>)")
        else:
            try:
                st = json.loads(st_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                st = None
                wording = {"status": "unmeasured", "note": f"source-text.json unreadable: {e}"}
                errors.append("wording: source-text.json unreadable")
            if st is not None:
                cj, la, n = wording_check(text, st)
                wording = {"status": "fail" if cj or la else "pass", "sourceStrings": n,
                           "matchedCjkRuns": len(cj), "matchedLatinGrams": len(la),
                           "rule": f"{CJK_RUN} CJK characters or {LATIN_WORDS} Latin words in a row"}
                if cj or la:
                    errors.append(f"wording: {len(cj)} CJK runs and {len(la)} Latin word runs match the source text")
    return errors, warnings, wording


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("playbook")
    ap.add_argument("--work")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    a = ap.parse_args()
    try:
        text = Path(a.playbook).read_text(encoding="utf-8")
        fm, body = split_playbook(text)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(json.dumps({"file": a.playbook, "ok": False, "errors": [f"unreadable: {e}"]}, ensure_ascii=False))
        sys.exit(2)
    errors, warnings, wording = validate(fm, body, a.playbook, a.schema, a.template, a.work, full_text=text)
    print(json.dumps({"file": Path(a.playbook).name, "ok": not errors, "errors": errors, "warnings": warnings, "wording": wording},
                     ensure_ascii=False, indent=1))
    sys.exit(0 if not errors else 3)


if __name__ == "__main__":
    main()
