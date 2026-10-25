# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = []
# ///
"""Ingest one local reference short: copy and record provenance, measure, and write one playbook draft.

Usage:
  uv run --script ingest.py <video> --id <playbook-id> --tier A|B|C
      [--home <dir>] [--platform instagram-reels|tiktok|youtube-shorts|other]
      [--language auto|ja|en|...] [--no-transcribe] [--retain-days 14] [--step-timeout 1800] [--json]

Library root: --home, else $SASARU_HOME, else ./sasaru. Everything lands in <home>/work/<id>/:
  prep outputs, captions.json, camera.json, audio.json, people.json, transcript.json, zoom/,
  source-text.json, <id>.md (the draft), ingest.json (what ran, what was missing), validate.json.
The draft goes to <home>/playbooks/<id>.md only after the agent replaces every 未記入 and the gate's
playbook check passes.

Steps, in order. A measuring script that is not in this directory is recorded as missing and its fields
stay unmeasured; a script that fails is recorded as failed and the run goes on.
  prep.py <video> <work> --tier T                                      required
  caption_boxes.py <work>/source.<ext> <work> --json                    -> captions.json [captions.ocr.json]
  camera_motion.py <work>/source.<ext> <work> [--mask-captions <work>/captions.json] --json  -> camera.json
  audio_events.py <work>/source.<ext> <work> --json                     -> audio.json      (only with audio)
  people_voice.py <work>/source.<ext> <work> [--audio-events <work>/audio.json] --json      -> people.json
  transcribe.py <work>/source.<ext> <work>/transcript.json [--speech <work>/audio.json]      (only with audio)
  zoom.sh around each low-confidence cut candidate                      -> zoom/cut-<t>/strip.jpg
  draft_playbook.py <work> --id <id>                                    -> <id>.md, source-text.json
  ../../sasaru-gate/scripts/validate_playbook.py <work>/<id>.md --work <work>   -> validate.json
  The gate does not look for 未記入; ingest.json "todo" counts the lines that still hold one.

Needs uv, ffmpeg, and ffprobe on PATH. Reads no keys. Tier C never leaves the machine; the only network
use is fetching Python packages and the local Whisper model.
Exit codes: 0 draft written, 2 bad input or prep failed.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPTIONAL = ["caption_boxes", "camera_motion", "audio_events", "people_voice"]
GATE_VALIDATE = HERE.parents[1] / "sasaru-gate" / "scripts" / "validate_playbook.py"


def log(*a):
    print(*a, file=sys.stderr)


def run_step(name, cmd, steps, timeout, note=None):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        status = "ok" if p.returncode == 0 else "failed"
        err = p.stderr.strip().splitlines()[-3:] if p.returncode else []
        code = p.returncode
    except subprocess.TimeoutExpired:
        status, err, code = "failed", [f"timeout after {timeout}s"], None
    steps[name] = {"status": status, "seconds": round(time.time() - t0, 1), "exitCode": code}
    if err:
        steps[name]["error"] = err
    if note:
        steps[name]["note"] = note
    log(f"{name}: {status} ({steps[name]['seconds']}s)")
    return status == "ok"


def uv_script(name):
    return ["uv", "run", "-q", "--script", str(HERE / f"{name}.py")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--id", required=True, help="kebab-case format id; describes the form, never the creator or the work")
    ap.add_argument("--tier", required=True, choices=["A", "B", "C"])
    ap.add_argument("--home")
    ap.add_argument("--platform", default="other", choices=["instagram-reels", "tiktok", "youtube-shorts", "other"])
    ap.add_argument("--language", default="auto")
    ap.add_argument("--no-transcribe", action="store_true")
    ap.add_argument("--retain-days", type=int, default=14)
    ap.add_argument("--step-timeout", type=int, default=1800)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    missing = [t for t in ("uv", "ffmpeg", "ffprobe") if shutil.which(t) is None]
    if missing:
        log(f"not on PATH: {', '.join(missing)}")
        return 2
    video = Path(a.video).expanduser().resolve()
    if not video.is_file():
        log(f"no such file: {video}")
        return 2
    home = Path(a.home or os.environ.get("SASARU_HOME") or "sasaru").expanduser().resolve()
    work = home / "work" / a.id
    work.mkdir(parents=True, exist_ok=True)
    steps = {}
    record = {"id": a.id, "video": str(video), "work": str(work), "steps": steps}

    def save():
        (work / "ingest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))

    if not run_step("prep", uv_script("prep") + [str(video), str(work), "--tier", a.tier, "--retain-days", str(a.retain_days)],
                    steps, a.step_timeout):
        save()
        log("prep failed; see ingest.json")
        return 2
    manifest = json.loads((work / "manifest.json").read_text())
    src = work / manifest["provenance"]["copy"]
    has_audio = manifest["probe"]["hasAudio"]

    for name in OPTIONAL:
        if name == "audio_events" and not has_audio:
            steps[name] = {"status": "skipped", "note": "no audio stream"}
            continue
        if not (HERE / f"{name}.py").is_file():
            steps[name] = {"status": "missing"}
            log(f"{name}: missing")
            continue
        cmd = uv_script(name) + [str(src), str(work), "--json"]
        if name == "camera_motion" and (work / "captions.json").is_file():
            cmd += ["--mask-captions", str(work / "captions.json")]
        if name == "people_voice" and (work / "audio.json").is_file():
            cmd += ["--audio-events", str(work / "audio.json")]
        run_step(name, cmd, steps, a.step_timeout)

    if not has_audio:
        steps["transcribe"] = {"status": "skipped", "note": "no audio stream"}
    elif a.no_transcribe:
        steps["transcribe"] = {"status": "skipped", "note": "--no-transcribe"}
    else:
        cmd = uv_script("transcribe") + [str(src), str(work / "transcript.json"), "--language", a.language]
        if (work / "audio.json").is_file():
            cmd += ["--speech", str(work / "audio.json")]
        run_step("transcribe", cmd, steps, a.step_timeout)

    shots = json.loads((work / "shots.json").read_text())
    dur = manifest["probe"]["durationSec"]
    low = [c for c in shots["cuts"] if c["confidence"] == "low"]
    zooms = []
    for c in low:
        out = work / "zoom" / f"cut-{c['t']:.3f}"
        p = subprocess.run(["bash", str(HERE / "zoom.sh"), str(src), f"{max(0, c['t'] - 0.2):.3f}",
                            f"{min(dur, c['t'] + 0.2):.3f}", "native", str(out)], capture_output=True, text=True)
        if p.returncode == 0:
            zooms.append(json.loads(p.stdout.strip().splitlines()[-1]))
    steps["zoom"] = {"status": "ok", "strips": len(zooms), "note": "low-confidence cut candidates only"}
    save()

    if not run_step("draft", uv_script("draft_playbook") + [str(work), "--id", a.id, "--platform", a.platform],
                    steps, a.step_timeout):
        save()
        log("draft_playbook failed; see ingest.json")
        return 2
    draft = work / f"{a.id}.md"
    record["draft"] = str(draft)
    record["todo"] = sum("未記入" in line for line in draft.read_text().splitlines())
    if GATE_VALIDATE.is_file():
        v = subprocess.run(["uv", "run", "-q", "--script", str(GATE_VALIDATE), str(draft), "--work", str(work)],
                           capture_output=True, text=True)
        try:
            report = json.loads(v.stdout)
        except json.JSONDecodeError:
            report = {"ok": False, "errors": v.stderr.strip().splitlines()[-3:]}
        (work / "validate.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        record["validate"] = {"ok": report.get("ok"), "errors": len(report.get("errors") or []),
                              "warnings": len(report.get("warnings") or []),
                              "wording": (report.get("wording") or {}).get("status")}
    else:
        record["validate"] = {"ok": None, "note": f"missing {GATE_VALIDATE}"}
    save()
    log(f"todo: {record['todo']} lines with 未記入; validate: {record['validate']}")
    summary = {"draft": str(draft), "work": str(work), "steps": {k: s["status"] for k, s in steps.items()},
               "todo": record["todo"], "validate": record["validate"]}
    if a.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        log(f"draft: {draft}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
