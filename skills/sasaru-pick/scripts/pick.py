# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7", "jsonschema>=4.18,<5"]
# ///
"""Pick one playbook for a maker's brief. Reads playbook frontmatter only. Calls no network API.

Exit codes: 0 a result was written (any status), 2 the brief or arguments could not be read.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

import yaml

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PLUGIN_ROOT / "schema" / "playbook.schema.json"

NEEDS = {"image-gen", "t2v", "i2v", "v2v", "r2v", "lipsync", "tts", "screen-capture", "own-footage", "stock-footage"}
ASPECTS = {"9:16", "4:5", "1:1", "16:9"}
VOICES = {"none", "tts-voiceover", "own-voiceover"}
PLAYBOOK_STATUS_RANK = {"produced": 2, "measured": 1, "draft": 0}
ROUTE_STATUS_RANK = {"tested": 2, "written": 1, "design-only": 0}
FIT_THRESHOLD = 0.3
CANDIDATES_SHOWN = 3
BRIEF_KEYS = {"content", "audience", "playbook", "durationSec", "aspect", "assets", "budgetUsd", "voice", "allowTalkingHead", "tags"}


def default_libraries() -> list[Path]:
    home = Path(os.environ["SASARU_HOME"]) if os.environ.get("SASARU_HOME") else Path.cwd() / "sasaru"
    return [home / "playbooks", PLUGIN_ROOT / "playbooks"]


class BriefError(Exception):
    pass


def jsonable(value):
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonable(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def read_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", text, re.DOTALL)
    if not m:
        raise ValueError("フロントマター（--- で囲んだ YAML）が無い")
    data = yaml.safe_load(m.group(1))
    if not isinstance(data, dict):
        raise TypeError("フロントマターが YAML の辞書ではない")
    # yaml.safe_load turns bare dates into date objects; the schema expects strings.
    return jsonable(data)


def load_validator():
    if not SCHEMA_PATH.is_file():
        return None
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())


def minimal_problems(fm: dict) -> list[str]:
    problems = []
    for key in ("id", "fitsContent", "format", "audio", "routes"):
        if key not in fm:
            problems.append(f"{key} が無い")
    if not isinstance(fm.get("routes"), list) or not fm.get("routes"):
        problems.append("routes が空")
    return problems


def load_library(dirs: list[Path]):
    validator = load_validator()
    playbooks, skipped, notes = {}, [], []
    if validator is None:
        notes.append(f"スキーマが見つからない（{SCHEMA_PATH}）。最小の欄だけ確かめた")
    for d in dirs:
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.md")):
            try:
                fm = read_frontmatter(path)
            except Exception as exc:  # noqa: BLE001 - one broken file must not stop the pick
                skipped.append({"file": str(path), "reason": f"読めない: {exc}"})
                continue
            if validator is not None:
                errors = sorted(validator.iter_errors(fm), key=lambda e: list(e.absolute_path))
                problems = [f"{'.'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in errors[:3]]
            else:
                problems = minimal_problems(fm)
            if problems:
                skipped.append({"file": str(path), "reason": "スキーマ不合格: " + " / ".join(problems)})
                continue
            pid = fm["id"]
            if pid != path.stem:
                notes.append(f"{path}: id（{pid}）がファイル名と違う")
            if pid in playbooks:
                notes.append(f"{pid}: {playbooks[pid]['_file']} を使い、{path} は読まなかった")
                continue
            fm["_file"] = str(path)
            playbooks[pid] = fm
    return playbooks, skipped, notes


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[\s\W_]+", "", text)


def bigrams(text: str) -> set[str]:
    t = normalize(text)
    if len(t) < 2:
        return {t} if t else set()
    return {t[i : i + 2] for i in range(len(t) - 1)}


def best_overlap(brief_text: str, items: list[str]) -> tuple[float, str | None]:
    """Share of an item's bigrams found in the brief text; the best item wins."""
    have = bigrams(brief_text)
    best, best_item = 0.0, None
    for item in items:
        grams = bigrams(item)
        if not grams:
            continue
        score = len(grams & have) / len(grams)
        if score > best:
            best, best_item = score, item
    return best, best_item


def content_fit(brief_text: str, brief_tags: list[str], fm: dict):
    best, best_item = best_overlap(brief_text, fm.get("fitsContent", []))
    shared_tags = sorted(set(brief_tags) & set(fm.get("tags", [])))
    return min(1.0, best + 0.15 * len(shared_tags)), best_item, shared_tags


def finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_duration(value):
    if value is None:
        return None
    if finite_number(value) and value > 0:
        return float(value), float(value)
    if isinstance(value, dict) and finite_number(value.get("min")) and finite_number(value.get("max")):
        lo, hi = float(value["min"]), float(value["max"])
        if 0 < lo <= hi:
            return lo, hi
    raise BriefError("durationSec は正の数か {min, max}")


def parse_brief(raw) -> dict:
    if not isinstance(raw, dict):
        raise BriefError("ブリーフは YAML か JSON の辞書")
    unknown = sorted(set(raw) - BRIEF_KEYS)
    content = raw.get("content") or {}
    if isinstance(content, str):
        content = {"message": content}
    if not isinstance(content, dict):
        raise BriefError("content は {kind, message} か文字列")
    assets = raw.get("assets")
    if assets is not None and (not isinstance(assets, list) or not set(map(str, assets)) <= NEEDS | {"none"}):
        raise BriefError(f"assets は次の語の列: {', '.join(sorted(NEEDS))}")
    named = raw.get("playbook")
    if named is not None and (not isinstance(named, str) or not named.strip()):
        raise BriefError("playbook は playbook の id（文字列）")
    aspect = raw.get("aspect")
    if aspect is not None and str(aspect) not in ASPECTS:
        raise BriefError(f"aspect は {', '.join(sorted(ASPECTS))} のどれか")
    voice = raw.get("voice")
    if voice is not None:
        voice = [voice] if isinstance(voice, str) else voice
        if not isinstance(voice, list) or not set(map(str, voice)) <= VOICES:
            raise BriefError(f"voice は次の語の列: {', '.join(sorted(VOICES))}")
    budget = raw.get("budgetUsd")
    if budget is not None and (not finite_number(budget) or budget < 0):
        raise BriefError("budgetUsd は 0 以上の数")
    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        raise BriefError("tags は列")
    return {
        "kind": str(content.get("kind") or "").strip(),
        "message": str(content.get("message") or "").strip(),
        "audience": str(raw.get("audience") or "").strip(),
        "playbook": named.strip() if named is not None else None,
        "duration": parse_duration(raw.get("durationSec")),
        "aspect": str(aspect) if aspect is not None else None,
        "assets": set(map(str, assets)) - {"none"} if assets is not None else None,
        "budget": float(budget) if budget is not None else None,
        "voice": set(voice) if voice is not None else None,
        "allowTalkingHead": raw.get("allowTalkingHead") is True,
        "tags": [str(t) for t in tags],
        "unknownKeys": unknown,
    }


def route_blockers(route: dict, brief: dict) -> list[dict]:
    blockers = []
    if (route["id"] == "r2v-talking" or route.get("talkingHead")) and not brief["allowTalkingHead"]:
        blockers.append({"kind": "talking-head", "text": f"ルート {route['id']} は人がカメラに喋る"})
    needs = set(route.get("needs", [])) - {"none"}
    if needs:
        if brief["assets"] is None:
            blockers.append({"kind": "assets-unknown", "need": sorted(needs), "text": f"ルート {route['id']} は {', '.join(sorted(needs))} が要る（assets 未指定）"})
        elif not needs <= brief["assets"]:
            lack = sorted(needs - brief["assets"])
            blockers.append({"kind": "assets", "need": lack, "text": f"ルート {route['id']} は {', '.join(lack)} が要る"})
    cost = route["costUsdPerVideo"]
    budget = brief["budget"] if brief["budget"] is not None else 0.0
    if cost["max"] > budget:
        kind = "budget-unknown" if brief["budget"] is None else "budget"
        blockers.append({"kind": kind, "needUsd": cost["max"], "text": f"ルート {route['id']} は一本 {cost['min']}〜{cost['max']} USD（上限 {budget:g} USD）"})
    return blockers


def choose_route(fm: dict, brief: dict):
    routes = fm["routes"]
    default = next(r for r in routes if r.get("default"))
    if not route_blockers(default, brief):
        return default, [], True
    open_routes = [r for r in routes if r is not default and not route_blockers(r, brief)]
    if open_routes:
        open_routes.sort(key=lambda r: (-ROUTE_STATUS_RANK[r["status"]], r["costUsdPerVideo"]["max"]))
        return open_routes[0], [], False
    return None, [{"route": r["id"], "blockers": route_blockers(r, brief)} for r in routes], False


def talking_reference(fm: dict) -> bool:
    return (fm["source"].get("reference") or {}).get("speech") == "on-camera"


def playbook_blockers(fm: dict, brief: dict) -> list[dict]:
    fmt, voice = fm["format"], fm["audio"]["voice"]
    blockers = []
    named = brief["playbook"] == fm["id"]
    if talking_reference(fm) and not (brief["allowTalkingHead"] or named):
        blockers.append({"kind": "talking-head", "text": "参照が人がカメラに喋る型（source.reference.speech: on-camera）。名指しか allowTalkingHead のときだけ選ぶ"})
    if brief["aspect"] and fmt["aspect"] != brief["aspect"]:
        blockers.append({"kind": "aspect", "text": f"画面比 {fmt['aspect']}（希望 {brief['aspect']}）"})
    if brief["duration"]:
        lo, hi = brief["duration"]
        d = fmt["durationSec"]
        if hi < d["min"] or lo > d["max"]:
            want = f"{lo:g}" if lo == hi else f"{lo:g}〜{hi:g}"
            blockers.append({"kind": "duration", "text": f"尺 {d['min']:g}〜{d['max']:g} 秒（希望 {want} 秒）"})
    allowed = brief["voice"] if brief["voice"] is not None else VOICES
    if voice not in allowed:
        blockers.append({"kind": "voice", "text": f"声 {voice}（許す声: {', '.join(sorted(allowed))}）"})
    return blockers


def duration_gap(fm: dict, brief: dict) -> float:
    if not brief["duration"]:
        return 0.0
    d = fm["format"]["durationSec"]
    ref = d.get("reference") or (d["min"] + d["max"]) / 2
    lo, hi = brief["duration"]
    return abs(ref - (lo + hi) / 2)


def evaluate(playbooks: dict, brief: dict) -> tuple[list, list]:
    brief_text = " ".join(x for x in (brief["kind"], brief["message"]) if x)
    open_list, closed = [], []
    for pid, fm in playbooks.items():
        fit, matched, shared_tags = content_fit(brief_text, brief["tags"], fm)
        blockers = playbook_blockers(fm, brief)
        route, route_bl, is_default = choose_route(fm, brief)
        if blockers or route is None:
            closed.append({"id": pid, "fit": fit, "blockers": blockers, "routes": route_bl})
            continue
        aud_fit, aud_item = best_overlap(brief["audience"], fm.get("audience", [])) if brief["audience"] else (0.0, None)
        open_list.append(
            {
                "id": pid, "fm": fm, "route": route, "routeIsDefault": is_default, "fit": fit, "matched": matched, "sharedTags": shared_tags,
                "audienceFit": aud_fit, "audienceMatched": aud_item,
            }
        )
    open_list.sort(
        key=lambda c: (
            -round(c["fit"], 2),
            -round(c["audienceFit"], 2),
            -PLAYBOOK_STATUS_RANK[c["fm"]["status"]],
            -ROUTE_STATUS_RANK[c["route"]["status"]],
            c["route"]["costUsdPerVideo"]["max"],
            duration_gap(c["fm"], brief),
            -len(c["fm"]["evidence"].get("measured", [])),
            c["id"],
        )
    )
    return open_list, closed


def route_view(route: dict, is_default: bool) -> dict:
    cost = route["costUsdPerVideo"]
    return {
        "id": route["id"],
        "default": is_default,
        "container": route["container"],
        "needs": route["needs"],
        "paidApi": route["paidApi"],
        "costUsdPerVideo": {k: cost[k] for k in ("min", "max", "basis", "asOf") if k in cost},
        "status": route["status"],
    }


def candidate_view(c: dict) -> dict:
    fm = c["fm"]
    return {
        "id": c["id"],
        "file": fm["_file"],
        "name": fm.get("name"),
        "status": fm["status"],
        "fit": round(c["fit"], 2),
        "matchedFitsContent": c["matched"],
        "sharedTags": c["sharedTags"],
        "audienceFit": round(c["audienceFit"], 2),
        "matchedAudience": c["audienceMatched"],
        "durationSec": fm["format"]["durationSec"],
        "route": route_view(c["route"], c["routeIsDefault"]),
    }


def reasons_for(c: dict, brief: dict, runner_up: dict | None) -> list[str]:
    fm, route = c["fm"], c["route"]
    cost = route["costUsdPerVideo"]
    out = []
    if brief["playbook"] == c["id"]:
        out.append("名指しされた型なので、この一本だけを条件と照らした")
    if c["matched"] and c["fit"] > 0:
        out.append(f"載せたい内容が fitsContent の「{c['matched']}」に合う（一致 {c['fit']:.2f}）")
    if c["sharedTags"]:
        out.append(f"タグ {', '.join(c['sharedTags'])} が重なる")
    if c["audienceMatched"] and c["audienceFit"] > 0:
        out.append(f"誰に向けるかが audience の「{c['audienceMatched']}」に合う（一致 {c['audienceFit']:.2f}）")
    d = fm["format"]["durationSec"]
    if brief["duration"]:
        out.append(f"尺の帯 {d['min']:g}〜{d['max']:g} 秒が希望の尺に重なる")
    on, speech, voice = fm["format"]["onCamera"], fm["format"]["speech"], fm["audio"]["voice"]
    lead = "参照は人がカメラに喋る型。このレシピのカットは" if talking_reference(fm) else "作るカットは"
    out.append(f"{lead}人の映り方 {on}、声 {speech}（{voice}）")
    if route["talkingHead"]:
        out.append("このルートは喋る人を出す。allowTalkingHead で許したときだけ選んだ")
    route_note = "既定ルート" if c["routeIsDefault"] else "既定ルートが条件に合わないための代わりのルート"
    out.append(f"{route_note} {route['id']}（器 {route['container']}、要るもの {', '.join(route['needs'])}、状態 {route['status']}）")
    paid = "有料 API を呼ぶ" if route["paidApi"] else "有料 API を呼ばない"
    out.append(f"一本 {cost['min']:g}〜{cost['max']:g} USD、{paid}。根拠: {cost['basis']}")
    out.append(f"playbook の状態は {fm['status']}")
    if runner_up is not None:
        if round(runner_up["fit"], 2) == round(c["fit"], 2):
            out.append(f"次点 {runner_up['id']} とは内容の一致が同じで、audience の一致・状態・ルートの状態・費用・尺の順で上回った")
        else:
            out.append(f"次点 {runner_up['id']}（一致 {runner_up['fit']:.2f}）より内容の一致が高い")
    return out


def unspecified_fields(brief: dict) -> list[str]:
    fields = []
    for key, name in (("duration", "durationSec"), ("aspect", "aspect"), ("assets", "assets"), ("budget", "budgetUsd")):
        if brief[key] is None:
            fields.append(name)
    if not brief["audience"]:
        fields.append("audience")
    return fields


UNKNOWN_KINDS = {"assets-unknown", "budget-unknown"}
QUESTIONS = {
    "assets": "用意できる素材と使える生成を routes[].needs の語で挙げる（own-footage, screen-capture, stock-footage, tts, image-gen など）",
    "budgetUsd": "一本あたりに使ってよい上限（USD）",
}


def unlocks_from_unknowns(closed: list, min_fit: float) -> tuple[list[dict], list[dict]]:
    """Routes that open once the maker answers an unspecified field. Explicit constraints are not asked again."""
    fields, unlocks = set(), []
    for entry in closed:
        if entry["blockers"] or entry["fit"] < min_fit:
            continue
        for rb in entry["routes"]:
            kinds = {b["kind"] for b in rb["blockers"]}
            if not kinds or not kinds <= UNKNOWN_KINDS:
                continue
            item = {"id": entry["id"], "fit": round(entry["fit"], 2), "route": rb["route"]}
            for b in rb["blockers"]:
                if b["kind"] == "assets-unknown":
                    item["assets"] = b["need"]
                    fields.add("assets")
                else:
                    item["budgetUsdAtLeast"] = b["needUsd"]
                    fields.add("budgetUsd")
            unlocks.append(item)
    missing = [{"field": f, "question": QUESTIONS[f]} for f in ("assets", "budgetUsd") if f in fields]
    return missing, unlocks


def relaxations(closed: list) -> list[dict]:
    out = []
    for entry in closed:
        texts = [b["text"] for b in entry["blockers"]]
        texts += [b["text"] for rb in entry["routes"] for b in rb["blockers"]]
        out.append({"id": entry["id"], "blockedBy": texts})
    return out


def pick(brief: dict, playbooks: dict, skipped: list, notes: list) -> dict:
    result = {"libraryCount": len(playbooks), "skipped": skipped, "notes": notes}
    if brief["unknownKeys"]:
        notes.append(f"ブリーフの知らない欄を無視した: {', '.join(brief['unknownKeys'])}")
    if brief["budget"] is None:
        notes.append("budgetUsd 未指定。0 USD（有料 API を呼ばないルートだけ）として絞った")
    if not playbooks:
        result.update(status="empty-library", message="playbook が 1 本も無い。手元の参照動画を sasaru-ingest で取り込んでから選ぶ", missing=[])
        return result
    named = brief["playbook"]
    if named is not None:
        if named not in playbooks:
            result.update(
                status="need-info",
                message=f"名指しの playbook {named} がライブラリに無い",
                missing=[{"field": "playbook", "question": "次の id のどれか", "options": sorted(playbooks)}],
            )
            return result
        playbooks = {named: playbooks[named]}
    elif not brief["kind"] and not brief["message"]:
        result.update(
            status="need-info",
            message="何を伝えるかが無いので選べない",
            missing=[{"field": "content.kind", "question": "載せる自分のコンテンツの種類（例: 勉強法のコツ、アプリの機能紹介）"},
                     {"field": "content.message", "question": "一本で伝えたいこと"}],
        )
        return result
    open_list, closed = evaluate(playbooks, brief)
    fitting = open_list if named else [c for c in open_list if c["fit"] >= FIT_THRESHOLD]
    result["candidates"] = [candidate_view(c) for c in open_list[:CANDIDATES_SHOWN]]
    result["excluded"] = relaxations(closed)
    if fitting:
        top = fitting[0]
        runner_up = fitting[1] if len(fitting) > 1 else None
        better = unlocks_from_unknowns(closed, top["fit"] + 0.01)
        result.update(
            status="picked",
            pick=candidate_view(top),
            reasons=reasons_for(top, brief, runner_up),
            unspecified=unspecified_fields(brief),
        )
        if better[1]:
            result["betterIfAnswered"] = {"missing": better[0], "unlocks": better[1]}
        return result
    missing, unlocks = unlocks_from_unknowns(closed, FIT_THRESHOLD)
    if missing:
        result.update(status="need-info", message="内容に合う型が未指定の欄で止まった。答えると unlocks のルートが開く", missing=missing, unlocks=unlocks)
        return result
    if open_list:
        result.update(
            status="no-fit",
            message="条件に合う型はあるが、載せたい内容がどの型の fitsContent にも合わない。内容の種類を下の言葉で言い直すか、合う参照動画を取り込む",
            missing=[{"field": "content.kind", "question": "次のどれに近いか", "options": {c["id"]: c["fm"]["fitsContent"] for c in open_list}}],
        )
        return result
    missing, unlocks = unlocks_from_unknowns(closed, 0.0)
    if missing:
        result.update(status="need-info", message="未指定の欄があり、候補が全部止まった。答えると unlocks のルートが開く", missing=missing, unlocks=unlocks)
        return result
    result.update(status="no-match", message="条件を満たす型が無い。下の止まった理由のどれかを緩めるか、合う参照動画を取り込む", missing=[])
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ブリーフに合う playbook を 1 本選ぶ。JSON を標準出力に書く")
    ap.add_argument("--brief", required=True, help="ブリーフの YAML か JSON。- で標準入力")
    ap.add_argument(
        "--library",
        action="append",
        type=Path,
        help="playbook の置き場所。複数可。先に書いた方が優先。省略時は $SASARU_HOME/playbooks（無ければ ./sasaru/playbooks）とプラグインの playbooks/",
    )
    args = ap.parse_args(argv)
    try:
        text = sys.stdin.read() if args.brief == "-" else Path(args.brief).read_text(encoding="utf-8")
        brief = parse_brief(yaml.safe_load(text))
    except (OSError, UnicodeDecodeError, yaml.YAMLError, BriefError) as exc:
        print(json.dumps({"status": "bad-brief", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    dirs = args.library or default_libraries()
    playbooks, skipped, notes = load_library(dirs)
    result = {"libraries": [str(d) for d in dirs if d.is_dir()]}
    result.update(pick(brief, playbooks, skipped, notes))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
