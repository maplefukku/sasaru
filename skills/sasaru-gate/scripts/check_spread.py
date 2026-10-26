# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Read why a playbook's format gets plays, comments, and shares.

The field is `spreadPsychology`. It is words the agent writes: three psychological
mechanisms, not a view count. A beat with role payoff means the format's job is to
be watched to the end, and omitting the field is then not allowed. null is not a value.
Each part names the mechanism and what in the format triggers it, and marks the
inference as inferred.

Usage: uv run --script check_spread.py --playbook <playbook.md>
Prints one JSON object. Exit 0 pass, 2 unreadable input, 3 the reading failed.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import yaml

PARTS = ("plays", "comments", "shares")
WORD = re.compile(r"[A-Za-z\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
VIEW_COUNT = re.compile(
    r"(?:"
    r"\d[\d,.]*\s*(?:万|億)?\s*(?:回|再生|views?|plays?|comments?|shares?|いいね|高評価)"
    r"|再生数|視聴回数|視聴数|view\s*counts?|play\s*counts?|コメント数|シェア数|フォロワー比"
    r"|\d+(?:\.\d+)?\s*(?:%|％)"
    r")",
    re.IGNORECASE,
)
MIN_WORDS = 8


def dates_to_str(obj):
    """safe_load turns ingestedAt and asOf into date objects; callers compare strings."""
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
    loaded = yaml.safe_load(m.group(1))
    if not isinstance(loaded, dict):
        raise ValueError("frontmatter is not a mapping")
    return dates_to_str(loaded)


def watch_to_end(fm) -> bool:
    """A payoff beat is the completion the format asks the viewer to stay for."""
    beats = fm.get("beats") if isinstance(fm, dict) else None
    if not isinstance(beats, list):
        return False
    return any(isinstance(b, dict) and b.get("role") == "payoff" for b in beats)


def _wordy(value) -> bool:
    return isinstance(value, str) and len(WORD.findall(value)) >= MIN_WORDS


def _count_claim(value) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return isinstance(value, str) and VIEW_COUNT.search(value) is not None


def _part_view(raw):
    if not isinstance(raw, dict):
        return None
    return {
        "mechanism": raw.get("mechanism") if isinstance(raw.get("mechanism"), str) else None,
        "trigger": raw.get("trigger") if isinstance(raw.get("trigger"), str) else None,
        "basis": raw.get("basis") if isinstance(raw.get("basis"), str) else None,
    }


def _check_part(name, raw, errors):
    path = f"spreadPsychology.{name}"
    if raw is None:
        errors.append(f"{path}: null is not a reading and is not a view count.")
        return
    if not isinstance(raw, dict):
        errors.append(
            f"{path}: name the psychological mechanism and what in the format triggers it. "
            "A bare value is not a reading."
        )
        return
    extra = set(raw) - {"mechanism", "trigger", "basis"}
    if extra:
        errors.append(f"{path}: {', '.join(sorted(extra))} is not a part of the reading. A view count is not a part.")
    mechanism, trigger, basis = raw.get("mechanism"), raw.get("trigger"), raw.get("basis")
    if _count_claim(mechanism) or _count_claim(trigger):
        errors.append(f"{path}: this field is words, not a view-count claim.")
    if not _wordy(mechanism) or not _wordy(trigger):
        errors.append(f"{path}: name the psychological mechanism and what in the format triggers it.")
    elif isinstance(mechanism, str) and isinstance(trigger, str) and mechanism.strip() == trigger.strip():
        errors.append(
            f"{path}: the mechanism and the trigger are the same words. "
            "Name the mechanism, and name what in the format triggers it."
        )
    if basis != "inferred":
        errors.append(
            f"{path}.basis: mark this inference as inferred. A measured count is not why the format is played."
        )


def check_spread(playbook) -> dict:
    """Return ok, errors, and the reading. Omitting the field is allowed only with no payoff beat."""
    errors = []
    fm = playbook if isinstance(playbook, dict) else {}
    if not isinstance(playbook, dict):
        errors.append("playbook: frontmatter is not a mapping")
    stays = watch_to_end(fm)
    present = isinstance(fm, dict) and "spreadPsychology" in fm
    raw = fm.get("spreadPsychology") if present else None
    parts = {}
    if present and raw is None:
        errors.append("spreadPsychology: null is not a reading and is not a view count.")
    elif stays and not present:
        errors.append(
            "spreadPsychology: missing on a format whose job is to be watched to the end "
            "(a payoff beat). Omitting the field is not allowed. null is not a value."
        )
    elif present and not isinstance(raw, dict):
        errors.append(
            "spreadPsychology: write plays, comments, and shares in words. A bare value is not a reading and is not a view count."
        )
    elif isinstance(raw, dict):
        extra = set(raw) - set(PARTS)
        if extra:
            errors.append(
                "spreadPsychology: plays, comments, and shares are the three parts. A view count is not a part."
            )
        for name in PARTS:
            if name not in raw:
                errors.append(
                    f"spreadPsychology.{name}: name the psychological mechanism and what in the format triggers it."
                )
                continue
            _check_part(name, raw.get(name), errors)
            view = _part_view(raw.get(name))
            if view is not None:
                parts[name] = view
        mechanisms = [parts[n]["mechanism"] for n in PARTS if n in parts and parts[n]["mechanism"]]
        if len(mechanisms) == 3 and len(set(mechanisms)) < 3:
            errors.append(
                "spreadPsychology: plays, comments, and shares are three mechanisms. One mechanism copied three times is not the reading."
            )
    reading = {"watchToEnd": stays}
    reading.update(parts)
    return {"ok": not errors, "errors": errors, "spreadPsychology": reading}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--playbook", required=True)
    args = ap.parse_args(argv)
    try:
        fm = split_playbook(Path(args.playbook).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "errors": [f"unreadable: {exc}"]}, ensure_ascii=False))
        return 2
    result = check_spread(fm)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
