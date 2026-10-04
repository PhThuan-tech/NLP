#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <host:port/web-path> <input.md> <output.md>" >&2
  exit 64
fi

url="$1"
input_path="$2"
output_path="$3"

if [[ ! -f "$input_path" ]]; then
  echo "Input file does not exist: $input_path" >&2
  exit 66
fi

case "$url" in
  http://*|https://*) ;;
  *) url="http://$url" ;;
esac
if [[ "$url" =~ ^https?://[^/]+/?$ ]]; then
  url="${url%/}/translate"
fi

mkdir -p "$(dirname -- "$output_path")"
temporary_output="$(mktemp)"
temporary_headers="$(mktemp)"
trap 'rm -f "$temporary_output" "$temporary_headers"' EXIT

started_ns="$(date +%s%N)"
curl_args=(
  --silent
  --show-error
  --output "$temporary_output"
  --dump-header "$temporary_headers"
  --write-out '%{http_code}'
  --header 'Content-Type: text/markdown; charset=utf-8'
  --data-binary "@$input_path"
)
if [[ -n "${TRANSLATION_DIRECTION:-}" ]]; then
  curl_args+=(--header "X-Translation-Direction: $TRANSLATION_DIRECTION")
fi
status="$(curl "${curl_args[@]}" "$url")"
finished_ns="$(date +%s%N)"

if [[ ! "$status" =~ ^2 ]]; then
  echo "Translation service returned HTTP $status" >&2
  cat "$temporary_output" >&2
  exit 69
fi

mv -f "$temporary_output" "$output_path"
elapsed="$(awk -v start="$started_ns" -v end="$finished_ns" 'BEGIN { printf "%.3f", (end-start)/1000000000 }')"
input_words="$(wc -w < "$input_path" | tr -d ' ')"
output_words="$(wc -w < "$output_path" | tr -d ' ')"
direction="$(awk -F': *' 'tolower($1)=="x-translation-direction" {gsub("\r", "", $2); print $2}' "$temporary_headers" | tail -n 1)"
service_runtime="$(awk -F': *' 'tolower($1)=="x-runtime-seconds" {gsub("\r", "", $2); print $2}' "$temporary_headers" | tail -n 1)"
chunks="$(awk -F': *' 'tolower($1)=="x-chunk-count" {gsub("\r", "", $2); print $2}' "$temporary_headers" | tail -n 1)"
words_per_second="$(awk -v words="$input_words" -v seconds="$elapsed" 'BEGIN { if (seconds > 0) printf "%.3f", words/seconds; else print "0.000" }')"
chunks_per_second="$(awk -v chunks="${chunks:-0}" -v seconds="$elapsed" 'BEGIN { if (seconds > 0) printf "%.3f", chunks/seconds; else print "0.000" }')"

echo "direction=${direction:-unknown} elapsed_seconds=$elapsed service_runtime_seconds=${service_runtime:-unknown} chunks=${chunks:-unknown} chunks_per_second=$chunks_per_second input_words=$input_words output_words=$output_words input_words_per_second=$words_per_second"
