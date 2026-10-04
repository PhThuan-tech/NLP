#!/usr/bin/env bash
set -euo pipefail

IMAGE_TAG="${1:-vlsp2026-legal-mt:latest}"
OUTPUT_DIR="${2:-dist}"
ARCHIVE_NAME="vlsp2026_legal_mt_image.tar.gz"
RELEASE_NAME="vlsp2026_legal_mt_submission.tar.gz"

mkdir -p "${OUTPUT_DIR}"
docker image inspect "${IMAGE_TAG}" >/dev/null

docker save "${IMAGE_TAG}" | gzip -n > "${OUTPUT_DIR}/${ARCHIVE_NAME}"
cp submission/translate.sh "${OUTPUT_DIR}/translate.sh"
cp submission/README.md "${OUTPUT_DIR}/README.md"
chmod +x "${OUTPUT_DIR}/translate.sh"

(
  cd "${OUTPUT_DIR}"
  md5sum "${ARCHIVE_NAME}" translate.sh README.md > MD5SUMS
  tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
    -czf "${RELEASE_NAME}" "${ARCHIVE_NAME}" translate.sh README.md MD5SUMS
  md5sum "${RELEASE_NAME}" > "${RELEASE_NAME}.md5"
)

echo "Exported ${IMAGE_TAG} to ${OUTPUT_DIR}/${ARCHIVE_NAME}"
echo "Final upload: ${OUTPUT_DIR}/${RELEASE_NAME}"
echo "Verify download with: cd ${OUTPUT_DIR} && md5sum -c ${RELEASE_NAME}.md5"
