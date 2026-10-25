# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "pyyaml>=6,<7",
#   "jsonschema>=4.23,<5",
#   "rfc3987-syntax>=1.1,<2",
# ]
# ///
"""Playbook check: report pass, fail, or unmeasured per column. Reports only; never edits the file.

Usage:
  uv run --script validate_playbook.py <playbook.md> [--work <work_dir>] [--schema <schema.json>]
      [--template <playbook.md template>] [--json]

Columns:
  schema     frontmatter passes schema/playbook.schema.json (dates from yaml.safe_load are turned back into strings)
  headings   the body has every "## " heading of the template, in order, and one "### <route id>" per route in routes order
  id         id equals the file name without .md
  beats      beats are ordered, do not overlap, and fit the reference length; every at.beat, captions[].beats,
             and camera.moves[].beat names an existing beat; offsetSec stays inside its beat
  wording    no 6-character CJK run and no 3-word Latin run from source-text.json appears anywhere in the file.
             source-text.json is looked up at --work, then <dir>/source-text.json, then <dir>/../work/<id>/source-text.json.
             Missing for an ingested playbook, or a null part that the playbook needs (captions when it has caption
             layers, transcript when source.reference.speech is not none), is unmeasured.
  todo       no 未記入 placeholder left by draft_playbook.py
Unmeasured counts as fail. Exit codes: 0 all pass, 2 bad input, 3 any column not pass.
"""
import argparse
import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path

import jsonschema
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
TODO = "未記入"
CJK_RUN = 6
LATIN_RUN = 3


def stringify_dates(x):
    if isinstance(x, (datetime.date, datetime.datetime)):
        return x.isoformat()
    if isinstance(x, dict):
        return {k: stringify_dates(v) for k, v in x.items()}
    if isinstance(x, list):
        return [stringify_dates(v) for v in x]
    return x


def split(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text
    return text[4:end + 1], text[end + 5:]


def is_cjk(ch):
    o = ord(ch)
    return (0x3040 <= o <= 0x30FF or 0x3400 <= o <= 0x4DBF or 0x4E00 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF
            or 0xAC00 <= o <= 0xD7AF or o == 0x30FC)


def norm(s):
    s = unicodedata.normalize("NFKC", s).lower()
    return "".join(ch for ch in s if unicodedata.category(ch)[0] in "LN")


def latin_words(s):
    return re.findall(r"[a-z0-9']+", unicodedata.normalize("NFKC", s).lower())


def wording_hits(strings, whole):
    flat = norm(whole)
    words = latin_words(whole)
    shingles = {tuple(words[i:i + LATIN_RUN]) for i in range(len(words) - LATIN_RUN + 1)}
    hits = []
    for s in strings:
        n = norm(s)
        for i in range(len(n) - CJK_RUN + 1):
            w = n[i:i + CJK_RUN]
            if all(is_cjk(c) or c.isdigit() for c in w) and any(is_cjk(c) for c in w) and w in flat:
                hits.append(w)
        ws = latin_words(s)
        for i in range(len(ws) - LATIN_RUN + 1):
            t = tuple(ws[i:i + LATIN_RUN])
            if t in shingles:
                hits.append(" ".join(t))
    return sorted(set(hits))


def find_source_text(path, pid, work):
    cands = []
    if work:
        cands.append(Path(work) / "source-text.json")
    cands += [path.parent / "source-text.json", path.parent.parent / "work" / pid / "source-text.json"]
    return next((c for c in cands if c.is_file()), None)


def check_beats(fm):
    beats = fm.get("beats") or []
    ids = {b.get("id"): b for b in beats}
    problems = []
    for a, b in zip(beats, beats[1:]):
        if b["tIn"] < a["tOut"] - 1e-6:
            problems.append(f"{a['id']} と {b['id']} が重なるか順が逆")
    for b in beats:
        if b["tOut"] <= b["tIn"]:
            problems.append(f"{b['id']} の tOut が tIn 以下")
    ref = ((fm.get("format") or {}).get("durationSec") or {}).get("reference")
    if ref and beats and beats[-1]["tOut"] > ref + 1e-6:
        problems.append(f"最後のビートが参照の尺 {ref} 秒を越える")

    def check_at(at, where):
        if at is None:
            return
        b = ids.get(at.get("beat"))
        if b is None:
            problems.append(f"{where} が無いビート {at.get('beat')} を指す")
        elif at.get("offsetSec", 0) > b["tOut"] - b["tIn"] + 1e-6:
            problems.append(f"{where} の offsetSec がビート {b['id']} の長さを越える")

    cam = fm.get("camera") or {}
    for i, z in enumerate(cam.get("zooms") or []):
        check_at(z.get("at"), f"camera.zooms[{i}].at")
    for i, t in enumerate(cam.get("transitions") or []):
        check_at(t.get("at"), f"camera.transitions[{i}].at")
    for i, m in enumerate(cam.get("moves") or []):
        if m.get("beat") not in ids:
            problems.append(f"camera.moves[{i}] が無いビート {m.get('beat')} を指す")
    au = fm.get("audio") or {}
    check_at((au.get("bgm") or {}).get("entersAt"), "audio.bgm.entersAt")
    for i, s in enumerate(au.get("sfx") or []):
        check_at(s.get("at"), f"audio.sfx[{i}].at")
    for layer in fm.get("captions") or []:
        for bid in layer.get("beats") or []:
            if bid not in ids:
                problems.append(f"captions.{layer.get('id')}.beats が無いビート {bid} を指す")
    return problems


def check_headings(body, template, routes):
    want = [l[3:].strip() for l in template.read_text().splitlines() if l.startswith("## ")]
    lines = body.splitlines()
    got = [l[3:].strip() for l in lines if l.startswith("## ")]
    problems = []
    if got != want:
        missing = [h for h in want if h not in got]
        extra = [h for h in got if h not in want]
        problems.append("見出しが順に揃っていない" + (f"。無い: {missing}" if missing else "") + (f"。余分: {extra}" if extra else ""))
    sub, inside = [], False
    for l in lines:
        if l.startswith("## "):
            inside = l[3:].strip() == "制作ルート"
        elif inside and l.startswith("### "):
            sub.append(l[4:].strip())
    want_routes = [r.get("id") for r in routes or []]
    if sub != want_routes:
        problems.append(f"制作ルートの小見出し {sub} が routes の順 {want_routes} と違う")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("playbook")
    ap.add_argument("--work")
    ap.add_argument("--schema", default=str(PLUGIN_ROOT / "schema" / "playbook.schema.json"))
    ap.add_argument("--template", default=str(PLUGIN_ROOT / "templates" / "playbook.md"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    path = Path(a.playbook)
    if not path.is_file():
        print(f"no such file: {path}", file=sys.stderr)
        return 2
    text = path.read_text()
    raw, body = split(text)
    if raw is None:
        print("no YAML frontmatter between --- lines", file=sys.stderr)
        return 2
    try:
        fm = stringify_dates(yaml.safe_load(raw))
    except yaml.YAMLError as e:
        print(f"YAML error: {e}", file=sys.stderr)
        return 2
    if not isinstance(fm, dict):
        print("frontmatter is not a mapping", file=sys.stderr)
        return 2

    cols = {}
    schema = json.loads(Path(a.schema).read_text())
    v = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errs = sorted(v.iter_errors(fm), key=lambda e: list(e.absolute_path))
    cols["schema"] = ("fail", [f"{'.'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in errs[:20]]) if errs else ("pass", [])

    hp = check_headings(body, Path(a.template), fm.get("routes"))
    cols["headings"] = ("fail", hp) if hp else ("pass", [])

    cols["id"] = ("pass", []) if fm.get("id") == path.stem else ("fail", [f"id {fm.get('id')} とファイル名 {path.stem} が違う"])

    try:
        bp = check_beats(fm)
    except (KeyError, TypeError) as e:
        bp = [f"ビートを読めない: {e}"]
    cols["beats"] = ("fail", bp) if bp else ("pass", [])

    ingested = (fm.get("source") or {}).get("kind") == "ingested"
    st_path = find_source_text(path, fm.get("id", ""), a.work)
    if st_path is None:
        cols["wording"] = ("unmeasured", ["source-text.json が無い"]) if ingested else ("pass", ["手書きの型なので照合する文言が無い"])
    else:
        st = json.loads(st_path.read_text())
        strings = [c.get("text", "") for c in st.get("captions") or []] + [s.get("text", "") for s in st.get("transcript") or []]
        hits = wording_hits(strings, text)
        gaps = []
        if st.get("captions") is None and fm.get("captions"):
            gaps.append("テロップの層があるのに source-text.json の captions が null（OCR かシートの読みが要る）")
        speech = ((fm.get("source") or {}).get("reference") or {}).get("speech")
        if st.get("transcript") is None and speech not in (None, "none"):
            gaps.append("参照に声があるのに source-text.json の transcript が null")
        if hits:
            cols["wording"] = ("fail", [f"参照の文言と一致: {len(hits)} 件"] + hits[:10])
        elif gaps:
            cols["wording"] = ("unmeasured", gaps)
        else:
            cols["wording"] = ("pass", [f"{st_path} の {len(strings)} 件と照合"])

    todo = [i + 1 for i, l in enumerate(text.splitlines()) if TODO in l]
    cols["todo"] = ("fail", [f"{TODO} が {len(todo)} 行に残る（行 {', '.join(map(str, todo[:12]))}）"]) if todo else ("pass", [])

    ok = all(s == "pass" for s, _ in cols.values())
    report = {"playbook": str(path), "pass": ok, "columns": {k: {"result": s, "detail": d} for k, (s, d) in cols.items()}}
    for k, (s, d) in cols.items():
        print(f"{k:9} {s}" + ("" if not d else "  " + " / ".join(d[:3])), file=sys.stderr)
    if a.json:
        print(json.dumps(report, ensure_ascii=False))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
