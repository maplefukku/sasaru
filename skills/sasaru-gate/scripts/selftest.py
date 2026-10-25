# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Build a synthetic cut with ffmpeg and check that check_cut.py passes it, then fails a copy whose last card ends early.

Usage: uv run --script selftest.py [--keep <dir>]
Needs ffmpeg and uv. Downloads the free YuNet face detector into $SASARU_CACHE on first run. Exit 0 when both verdicts match.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[2] / "templates" / "playbook.md"
W, H, FPS, DUR = 1080, 1920, 30, 6.0
CARDS = [(0.0, 2.0, 600, "一枚目の句"), (2.0, 4.0, 480, "二枚目"), (4.0, 6.0, 360, "三枚目です")]
CAP_H, CY, STROKE = 109, 0.3, 8


def playbook_text():
    text = TEMPLATE.read_text(encoding="utf-8")
    fm_raw, body = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S).groups()
    fm = yaml.safe_load(fm_raw)
    fm["id"] = "selftest-cards"
    fm["format"].update({"durationSec": {"min": 5, "max": 8, "reference": DUR}, "speech": "voiceover"})
    fm["beats"] = [
        {"id": "b1", "role": "hook", "tIn": 0.0, "tOut": 2.0, "purpose": "約束を出す", "swap": "自分の約束"},
        {"id": "b2", "role": "item", "tIn": 2.0, "tOut": 4.0, "purpose": "中身を一つ渡す", "swap": "自分の中身"},
        {"id": "b3", "role": "payoff", "tIn": 4.0, "tOut": DUR, "purpose": "回収して残す", "swap": "自分の答え"},
    ]
    c = fm["captions"][0]
    c.update({"capHeightRatio": round(CAP_H / H, 4), "position": {"cx": 0.5, "cy": CY, "align": "center"}, "shadow": False,
              "minHoldSec": 1.0, "charsPerCard": {"min": 2, "max": 10}})
    for key in ("levelDbUnderVoice", "duckUnderVoice"):
        fm["audio"]["bgm"].pop(key, None)
    fm["audio"]["voice"] = "tts-voiceover"
    fm["evidence"] = {"measured": [], "inferred": ["hook.type", "beats", "format.safeArea", "captions.c1.capHeightRatio",
                                                   "captions.c1.position.cy", "captions.c1.minHoldSec"], "unmeasured": []}
    return "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + body


def build(cut_dir, last_end):
    cut_dir.mkdir(parents=True)
    draws = []
    for i, (t0, t1, w, _) in enumerate(CARDS):
        t1 = last_end if i == len(CARDS) - 1 else t1
        x, y = (W - w) // 2, int(CY * H - CAP_H / 2)
        en = f"enable='between(t\\,{t0}\\,{t1 - 0.001})'"
        draws.append(f"drawbox=x={x - STROKE}:y={y - STROKE}:w={w + 2 * STROKE}:h={CAP_H + 2 * STROKE}:color=black:t=fill:{en}")
        draws.append(f"drawbox=x={x}:y={y}:w={w}:h={CAP_H}:color=white:t=fill:{en}")
    gate = "+".join(f"between(t,{t0},{t0 + 1.4})" for t0, _, _, _ in CARDS)
    run = lambda *a: subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)
    run("-f", "lavfi", "-i", f"aevalsrc='0.3*sin(2*PI*220*t)*({gate})':s=48000:d={DUR}", str(cut_dir / "voice.wav"))
    run("-f", "lavfi", "-i", f"aevalsrc=0.01*sin(2*PI*55*t)+0.01*sin(2*PI*82*t):s=48000:d={DUR}", str(cut_dir / "bgm.wav"))
    run("-f", "lavfi", "-i", f"color=c=0x8890A0:s={W}x{H}:r={FPS}:d={DUR}", "-i", str(cut_dir / "voice.wav"), "-i", str(cut_dir / "bgm.wav"),
        "-filter_complex", f"[0:v]noise=alls=8:allf=t,{','.join(draws)}[v];[1:a][2:a]amix=inputs=2:normalize=0[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(cut_dir / "cut.mp4"))
    (cut_dir / "cut.json").write_text(json.dumps({
        "schema": "sasaru-cut/1", "playbook": "selftest-cards", "playbookPath": "../../playbooks/selftest-cards.md", "video": "cut.mp4",
        "route": "code-motion", "routeRequestedByMaker": False, "container": "html-canvas", "stretch": 1.0, "costUsd": 0,
        "cards": [{"layer": "c1", "start": t0, "end": t1, "text": tx} for t0, t1, _, tx in CARDS],
        "captionStyle": {"c1": {"fontFamily": "Noto Sans JP", "fontClass": "extra-bold-gothic", "weight": 900, "shadow": False, "plate": "none"}},
        "audio": {"sources": [{"role": "voice", "path": "voice.wav", "license": "synthetic"}, {"role": "bgm", "path": "bgm.wav", "license": "synthetic"}],
                  "referenceAudioUsed": False},
        "lastMora": {"tIn": 5.2, "tOut": 5.4},
    }, ensure_ascii=False, indent=1), encoding="utf-8")


def check(cut_dir):
    uv = shutil.which("uv")
    cmd = [uv, "run", "--quiet", "--script"] if uv else [sys.executable]
    p = subprocess.run([*cmd, str(HERE / "check_cut.py"), str(cut_dir), "--fetch-models"], capture_output=True, text=True)
    return json.loads(p.stdout), p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep")
    a = ap.parse_args()
    root = Path(a.keep) if a.keep else Path(tempfile.mkdtemp(prefix="sasaru-gate-selftest-"))
    lib = root / "sasaru"
    (lib / "playbooks").mkdir(parents=True, exist_ok=True)
    (lib / "playbooks" / "selftest-cards.md").write_text(playbook_text(), encoding="utf-8")
    build(lib / "cuts" / "good", DUR)
    build(lib / "cuts" / "early-last", DUR - 0.5)
    good, rc_good = check(lib / "cuts" / "good")
    bad, rc_bad = check(lib / "cuts" / "early-last")
    ok = good["verdict"] == "pass" and rc_good == 0 and bad["verdict"] == "fail" and "captions.c1.lastCard" in bad["failed"] and rc_bad == 3
    print(json.dumps({"ok": ok, "good": {"verdict": good["verdict"], "failed": good["failed"], "unmeasured": good["unmeasured"]},
                      "earlyLast": {"verdict": bad["verdict"], "failed": bad["failed"]}, "dir": str(root) if a.keep else None},
                     ensure_ascii=False, indent=1))
    if not a.keep:
        shutil.rmtree(root, ignore_errors=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
