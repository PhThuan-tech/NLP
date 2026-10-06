#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
OUTPUT_DIR="${2:-dist/smoke}"
mkdir -p "${OUTPUT_DIR}"

TRANSLATION_DIRECTION=en2vi bash submission/translate.sh \
  "${BASE_URL}" submission/smoke/input_en.md "${OUTPUT_DIR}/output_vi.md"
TRANSLATION_DIRECTION=vi2en bash submission/translate.sh \
  "${BASE_URL}" submission/smoke/input_vi.md "${OUTPUT_DIR}/output_en.md"

test -s "${OUTPUT_DIR}/output_vi.md"
test -s "${OUTPUT_DIR}/output_en.md"
python - "${OUTPUT_DIR}/output_vi.md" "${OUTPUT_DIR}/output_en.md" <<'PY'
from pathlib import Path
import sys

for raw in sys.argv[1:]:
    path = Path(raw)
    text = path.read_text(encoding="utf-8")
    if "\ufffd" in text:
        raise SystemExit(f"Invalid UTF-8 replacement character in {path}")
print("Smoke outputs are non-empty UTF-8 files.")
PY
