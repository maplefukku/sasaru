#!/usr/bin/env bash
# Dense frames for one time range, to read caption animation and transitions frame by frame.
# Usage: zoom.sh <video> <start_sec> <end_sec> <fps|native> <out_dir> [crop=w:h:x:y]
# Writes <out_dir>/f_NNN.jpg (full size) and <out_dir>/strip.jpg (tiles 360 px wide).
# Every frame and tile is stamped with its time on the source timeline, not the time since <start_sec>.
# Prints one JSON line: {"frames": n, "strip": path, "start": s, "end": e, "fps": f}
# Needs ffmpeg and ffprobe. Exit codes: 0 ok, 2 bad input.
set -euo pipefail
[[ $# -ge 5 ]] || { sed -n '2,7p' "$0" >&2; exit 2; }
SRC=$1; A=$2; B=$3; FPS=$4; OUT=$5; CROP=${6:-}
[[ -f "$SRC" ]] || { echo "no such file: $SRC" >&2; exit 2; }
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")
read -r A B LEN < <(awk -v a="$A" -v b="$B" -v d="$DUR" 'BEGIN {
  if (a < 0) a = 0; if (b > d) b = d;
  if (b <= a) { print "x x x"; exit }
  printf "%.3f %.3f %.3f\n", a, b, b - a }')
[[ "$A" != x ]] || { echo "empty range" >&2; exit 2; }
if [[ "$FPS" == native ]]; then
  FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of csv=p=0 "$SRC")
fi
mkdir -p "$OUT"
rm -f "$OUT"/f_*.jpg "$OUT"/t_*.jpg
pre="fps=$FPS"
[[ -n "$CROP" ]] && pre="crop=$CROP,$pre"
stamp="drawtext=text='%{pts\:hms\:$A}':x=6:y=6:fontcolor=white:box=1:boxcolor=black@0.7"
ffmpeg -v error -y -ss "$A" -t "$LEN" -i "$SRC" -filter_complex \
  "[0:v]$pre,split=2[a][b];[a]$stamp:fontsize=28[full];[b]scale=360:-2,$stamp:fontsize=22[tile]" \
  -map "[full]" "$OUT/f_%03d.jpg" -map "[tile]" "$OUT/t_%03d.jpg"
n=$(find "$OUT" -maxdepth 1 -name 'f_*.jpg' | wc -l)
[[ "$n" -gt 0 ]] || { echo "no frames in range" >&2; exit 2; }
cols=$(( n < 6 ? n : 6 ))
ffmpeg -v error -y -pattern_type glob -i "$OUT/t_*.jpg" -vf "tile=${cols}x$(( (n + cols - 1) / cols ))" -frames:v 1 "$OUT/strip.jpg"
rm -f "$OUT"/t_*.jpg
printf '{"frames": %d, "strip": "%s", "start": %s, "end": %s, "fps": "%s"}\n' "$n" "$OUT/strip.jpg" "$A" "$B" "$FPS"
