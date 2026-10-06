"""Final public-test evaluation for a frozen decoding configuration."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .config import ExperimentConfig
from .data import JsonlCorpus, sha256_file, write_json, write_jsonl
from .inference import (
    assemble_document,
    load_inference_model,
    markdown_structure_report,
    split_markdown_document,
    translate_chunks,
)
from .metrics import TranslationMetricSuite
from .quality import quality_report
from .runner import BaselineRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--saved-model-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--public-test-file", type=Path)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--maximum-source-tokens", type=int, default=448)
    parser.add_argument("--allow-cpu", action="store_true")
    return parser


def _structure_summary(reports: Sequence[dict[str, Any]]) -> dict[str, Any]:
    mismatch_counts: dict[str, int] = {}
    affected = 0
    for report in reports:
        mismatches = report["mismatches"]
        if mismatches:
            affected += 1
        for name in mismatches:
            mismatch_counts[name] = mismatch_counts.get(name, 0) + 1
    return {
        "evaluated_records": len(reports),
        "records_with_mismatch": affected,
        "mismatch_rate": round(100 * affected / max(1, len(reports)), 6),
        "mismatch_counts": mismatch_counts,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.batch_size < 1:
        raise ValueError("batch-size must be positive")
    if args.maximum_source_tokens < 32:
        raise ValueError("maximum-source-tokens must be at least 32")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(f"Use a fresh public-test output: {args.output_dir}")

    config = ExperimentConfig.from_json(args.config)
    manifest_path = Path(config.data.manifest_file)
    public_test_file = args.public_test_file or (
        manifest_path.parent / f"segments_public_test_{config.direction}.jsonl"
    )
    config.data.validation_file = str(public_test_file)
    config.data.max_validation_samples = None
    if args.allow_cpu:
        config.apply_overrides(allow_cpu=True)

    runner = BaselineRunner(config)
    runner._validate_dataset_contract()
    if not args.saved_model_dir.is_dir():
        raise FileNotFoundError(f"Saved model directory not found: {args.saved_model_dir}")

    try:
        import torch
        from transformers import set_seed
    except ImportError as error:
        raise RuntimeError("Install requirements-training.txt before evaluation") from error
    if config.training.require_cuda and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required by the selected config")
    set_seed(config.seed)

    print(f"Loading frozen {config.direction} model; no training.", flush=True)
    tokenizer, model = load_inference_model(
        config, saved_model_dir=args.saved_model_dir
    )
    records = JsonlCorpus(
        public_test_file,
        direction=config.direction,
        source_field=config.data.source_field,
        target_field=config.data.target_field,
    ).load()

    chunks_by_record = []
    flat_chunks = []
    ranges = []
    for record in records:
        chunks = split_markdown_document(
            record.source,
            tokenizer,
            maximum_tokens=args.maximum_source_tokens,
        )
        start = len(flat_chunks)
        flat_chunks.extend(chunks)
        ranges.append((start, len(flat_chunks)))
        chunks_by_record.append(chunks)

    print(
        f"Generating {len(records)} public-test records as {len(flat_chunks)} chunks; "
        "no records are dropped.",
        flush=True,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    chunk_predictions, runtime = translate_chunks(
        flat_chunks,
        tokenizer=tokenizer,
        model=model,
        config=config,
        batch_size=args.batch_size,
        device=device,
        fail_on_empty=False,
        log_progress=True,
    )
    predictions = [
        assemble_document(chunks, chunk_predictions[start:end]).strip()
        for chunks, (start, end) in zip(chunks_by_record, ranges, strict=True)
    ]
    references = [record.target for record in records]
    sources = [record.source for record in records]

    suite = TranslationMetricSuite(tokenizer)
    metrics = suite.score_texts(predictions, references)
    metrics.update(suite.score_source_preservation(predictions, sources))
    structures = [
        markdown_structure_report(source, prediction)
        for source, prediction in zip(sources, predictions, strict=True)
    ]
    quality = quality_report(
        predictions,
        references,
        config.direction,
        [record.segment_id for record in records],
    )
    chunk_counts = [end - start for start, end in ranges]
    report = {
        "kind": "public_test_final_evaluation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "direction": config.direction,
        "dataset_id": config.data.dataset_id,
        "public_test_file": str(public_test_file.resolve()),
        "public_test_sha256": sha256_file(public_test_file),
        "config_file": str(args.config.resolve()),
        "config_sha256": sha256_file(args.config),
        "saved_model_dir": str(args.saved_model_dir.resolve()),
        "generation": asdict(config.generation),
        "records": len(records),
        "source_chunks": len(flat_chunks),
        "records_split_into_multiple_chunks": sum(value > 1 for value in chunk_counts),
        "maximum_chunks_per_record": max(chunk_counts, default=0),
        "maximum_source_tokens_per_chunk": args.maximum_source_tokens,
        "metrics": metrics,
        "runtime": runtime,
        "quality": quality,
        "markdown_structure": _structure_summary(structures),
    }
    rows = []
    for record, prediction, structure, chunk_count in zip(
        records, predictions, structures, chunk_counts, strict=True
    ):
        row = record.to_output_mapping(prediction)
        row["source_chunks"] = chunk_count
        row["markdown_structure"] = structure
        rows.append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "public_test_predictions.jsonl", rows)
    write_json(args.output_dir / "public_test_report.json", report)
    print(
        f"Public test {config.direction}: BLEU={metrics['bleu']:.3f}, "
        f"chrF++={metrics['chrf']:.3f}, records={len(records)}, "
        f"chunks={len(flat_chunks)}, gate={quality['status']}",
        flush=True,
    )
    print(f"Report: {args.output_dir / 'public_test_report.json'}", flush=True)
    return 0 if quality["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
