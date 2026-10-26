# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Read where a playbook's account style places a target product.

The account style is the playbook field `productPlacement`. One cut does not move it.
Omitting the field means this format never has a product slot. It does not mean an
end-card pitch. null is not a placement.

Usage: uv run --script check_placement.py --playbook <playbook.md> [--content <content.yaml>]
Prints one JSON object. Exit 0 pass, 2 unreadable input, 3 the placement failed.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import yaml

ROUTES = {"reference-world", "moguno", "in-world"}
PRODUCT_ROUTE = "in-world"
ROLES = {"absent", "prop", "payoff", "spoken", "end-card"}
IN_WORLD_ROLE = "prop"
BARE_DIRECTNESS = ROLES | {"true", "false", "yes", "no", "end card", "endcard", "pitch", "ad"}
WORD = re.compile(r"[A-Za-z\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
PITCH = re.compile(
    r"product[\s-]*explainer|end[\s-]*card[\s-]*ad|"
    r"機能を紹介|機能紹介|使い方を紹介|製品を紹介|製品紹介|"
    r"アプリを紹介|アプリ紹介|商品を紹介|商品の機能|商品説明|"
    r"ダウンロードして|今すぐ試",
    re.IGNORECASE,
)


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


def pitch_shaped(value) -> bool:
    """True when the subject of the video is the product, not the reference world or Moguno."""
    if isinstance(value, dict):
        if value.get("of") == "product":
            return True
        return pitch_shaped(value.get("words") or value.get("line") or "")
    if not isinstance(value, str):
        return False
    return PITCH.search(value) is not None


def _placement_view(raw):
    if not isinstance(raw, dict):
        return {"slot": False}
    return {
        "slot": True,
        "beat": raw.get("beat"),
        "role": raw.get("role"),
        "directness": raw.get("directness"),
    }


def check_placement(playbook, content=None) -> dict:
    """Return ok, errors, and the placement reading. slot false is not an end card."""
    errors = []
    fm = playbook if isinstance(playbook, dict) else {}
    if not isinstance(playbook, dict):
        errors.append("playbook: frontmatter is not a mapping")

    route = fm.get("contentRoute")
    subject = fm.get("subject")
    if route not in ROUTES:
        errors.append(
            "contentRoute: say which world this format keeps "
            "(reference-world, moguno, or in-world). A product explainer is not a route."
        )
    if not isinstance(subject, dict):
        errors.append("subject: write what the video is about. The subject is the reference world or Moguno, not the product.")
        subject_of, subject_words = None, ""
    else:
        subject_of = subject.get("of")
        subject_words = subject.get("words") if isinstance(subject.get("words"), str) else ""
        if subject_of == "product" or pitch_shaped(subject):
            errors.append("subject: pitch-shaped. The video's subject is the reference world or Moguno, not the product.")
        elif route == "moguno" and subject_of != "moguno":
            errors.append("subject.of: a moguno route recasts the world as Moguno. The subject is Moguno, not the product.")
        elif route in {"reference-world", "in-world"} and subject_of != "reference-world":
            errors.append("subject.of: this route keeps the reference world. The subject is that world, not the product.")
        elif isinstance(subject.get("words"), str) and not WORD.search(subject_words):
            errors.append("subject.words: say the world in words.")

    present = isinstance(fm, dict) and "productPlacement" in fm
    raw = fm.get("productPlacement") if present else None
    if present and raw is None:
        errors.append("productPlacement: null is not a placement and is not an end-card pitch.")
    elif route == PRODUCT_ROUTE and not present:
        errors.append(
            "productPlacement: missing on a product route (contentRoute in-world). "
            "Omitting the field is only for a format with no product slot, and it is not an end-card pitch."
        )
    elif present and not isinstance(raw, dict):
        errors.append("productPlacement: write the beat, the role, and how direct. A bare value is not a placement.")
    elif isinstance(raw, dict):
        beat, role, directness = raw.get("beat"), raw.get("role"), raw.get("directness")
        beats = {b.get("id") for b in fm.get("beats") or [] if isinstance(b, dict)}
        if beat not in beats:
            errors.append(f"productPlacement.beat: {beat!r} is not a beat in this playbook.")
        if role not in ROLES:
            errors.append(
                "productPlacement.role: use absent, prop, payoff, spoken, or end-card. "
                "Do not leave the role blank and do not invent an end card by default."
            )
        if not isinstance(directness, str) or directness.strip().lower() in BARE_DIRECTNESS or not WORD.search(directness):
            errors.append("productPlacement.directness: write how direct the appearance is, in words. A role name is not the directness.")
        if route == PRODUCT_ROUTE and role != IN_WORLD_ROLE:
            errors.append("productPlacement.role: an in-world route shows the product only as a prop inside the world.")

    if content is not None:
        if not isinstance(content, dict):
            errors.append("content: the maker's script is not a mapping")
        else:
            if "productPlacement" in content:
                errors.append("content.productPlacement: account style lives on the playbook. A cut cannot move it.")
            if content.get("productExplainer") or content.get("explainer"):
                errors.append("content: a product explainer is not a script. The subject stays the world.")
            if pitch_shaped(content.get("subject")):
                errors.append("content.subject: pitch-shaped. A script whose subject is the product is invalid.")
            end_card = content.get("endCard")
            role = raw.get("role") if isinstance(raw, dict) else None
            if end_card is not None and role != "end-card":
                errors.append("content.endCard: this playbook does not place an end card. Do not add one.")
            if end_card is not None and pitch_shaped(end_card if isinstance(end_card, str) else str(end_card)):
                errors.append("content.endCard: pitch-shaped. An end card is not a product explainer.")

    view = _placement_view(raw if isinstance(raw, dict) else None)
    return {
        "ok": not errors,
        "errors": errors,
        "contentRoute": route if isinstance(route, str) else None,
        "subject": subject if isinstance(subject, dict) else None,
        "productPlacement": view,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--playbook", required=True)
    ap.add_argument("--content", help="maker script. Its subject is checked when present.")
    args = ap.parse_args(argv)
    try:
        fm = split_playbook(Path(args.playbook).read_text(encoding="utf-8"))
        content = None
        if args.content:
            loaded = yaml.safe_load(Path(args.content).read_text(encoding="utf-8"))
            content = dates_to_str(loaded) if not isinstance(loaded, str) else loaded
    except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "errors": [f"unreadable: {exc}"]}, ensure_ascii=False))
        return 2
    result = check_placement(fm, content)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
