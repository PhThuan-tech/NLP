"""Compare completed runs only when they use the same frozen dev set."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Sequence


METRICS = (
    "bleu",
    "chrf",
    "empty_output_rate",
    "length_ratio_mean",
    "number_preservation_f1",
    "reference_preservation_f1",
    "runtime",
    "samples_per_second",
    "peak_vram_mb",
)


def _metric(values: dict[str, Any], name: str) -> Any:
    return values.get(f"validation_{name}", values.get(name))


def load_run(path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(path)
    manifest_path = path if path.name == "run_manifest.json" else path / "run_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing run manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = manifest.get("data_files", {}).get("validation", {})
    if not validation.get("sha256"):
        raise ValueError(f"Run has no validation fingerprint: {manifest_path}")
    metrics = manifest.get("validation_metrics", {})
    row: dict[str, Any] = {
        "run_dir": str(manifest_path.parent),
        "created_at_utc": manifest.get("created_at_utc"),
        "run_name": manifest.get("run_name"),
        "dataset_id": manifest.get("dataset_id"),
        "direction": manifest.get("direction"),
        "training_mode": manifest.get("training_mode"),
        "training_seed": manifest.get("training_seed"),
        "model_name": manifest.get("model_name"),
        "model_revision": manifest.get("model_revision"),
        "metric_code_sha256": manifest.get("metric_code_sha256"),
        "validation_sha256": validation["sha256"],
        "evaluated_records": metrics.get("evaluated_records"),
    }
    row.update({name: _metric(metrics, name) for name in METRICS})
    return manifest, row


def comparable_rows(paths: Sequence[str | Path]) -> list[dict[str, Any]]:
    loaded = [load_run(path) for path in paths]
    if not loaded:
        raise ValueError("Provide at least one completed run directory")
    signatures = {
        (
            manifest.get("dataset_id"),
            manifest.get("direction"),
            manifest.get("model_name"),
            manifest.get("model_revision"),
            manifest.get("data_files", {}).get("validation", {}).get("sha256"),
            manifest.get("validation_metrics", {}).get("evaluated_records"),
            json.dumps(manifest.get("generation_config"), sort_keys=True),
            manifest.get("metric_code_sha256"),
            manifest.get("packages", {}).get("transformers"),
            manifest.get("packages", {}).get("sacrebleu"),
        )
        for manifest, _ in loaded
    }
    if len(signatures) != 1:
        raise ValueError(
            "Runs are not directly comparable: dataset, direction, base model/revision, "
            "dev checksum, evaluated record count, generation config, metric code, "
            "Transformers version, or SacreBLEU version differs"
        )
    return [row for _, row in loaded]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="Run directories or run_manifest.json files")
    parser.add_argument("--output", type=Path, help="Optional comparison CSV path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = comparable_rows(args.runs)
    fieldnames = list(rows[0])
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            output_writer = csv.DictWriter(handle, fieldnames=fieldnames)
            output_writer.writeheader()
            output_writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
