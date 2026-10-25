#!/usr/bin/env bash
# Video-only copy: drops every audio stream (reference audio, BGM, audio returned by generation APIs).
# Usage: strip_audio.sh <in> <out>
# Prints the output's streams and format as ffprobe JSON. Needs ffmpeg and ffprobe.
# Exit codes: 0 ok, 2 bad input, 3 an audio stream survived.
set -euo pipefail
[[ $# -eq 2 ]] || { sed -n '2,5p' "$0" >&2; exit 2; }
[[ -f "$1" ]] || { echo "no such file: $1" >&2; exit 2; }
mkdir -p "$(dirname "$2")"
ffmpeg -v error -y -i "$1" -map 0:v:0 -c:v copy -an -movflags +faststart "$2"
n=$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$2" | wc -l)
[[ "$n" == 0 ]] || { echo "audio stream still present" >&2; exit 3; }
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate:format=duration,size -of json "$2"
