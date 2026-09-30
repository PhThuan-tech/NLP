"""Evaluate several decoding settings on one fixed, stratified dev subset."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from .config import ExperimentConfig
from .data import JsonlCorpus, TokenizerAuditor, write_json, write_jsonl
from .inference import DocumentChunk, load_inference_model, token_length, translate_chunks
from .metrics import TranslationMetricSuite
from .runner import BaselineRunner


DEFAULT_CANDIDATES = (
    "baseline:2:1.0:1.0:3:none",
    "safe_a:2:0.8:1.05:3:448",
    "safe_b:2:0.8:1.10:3:448",
    "fast_safe:1:0.8:1.10:3:448",
)


def parse_candidate(value: str) -> dict[str, Any]:
    parts = value.split(":")
    if len(parts) != 6:
        raise argparse.ArgumentTypeError(
            "candidate must be name:beams:length_penalty:repetition_penalty:"
            "no_repeat_ngram_size:max_new_tokens"
        )
    name, beams, length_penalty, repetition_penalty, no_repeat, max_new = parts
    if not name.replace("_", "").replace("-", "").isalnum():
        raise argparse.ArgumentTypeError("candidate name must be filesystem-safe")
    return {
        "name": name,
        "num_beams": int(beams),
        "length_penalty": float(length_penalty),
        "repetition_penalty": float(repetition_penalty),
        "no_repeat_ngram_size": int(no_repeat),
        "max_new_tokens": None if max_new.lower() == "none" else int(max_new),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--saved-model-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument(
        "--candidate",
        action="append",
        type=parse_candidate,
        help=(
            "Repeatable name:beams:length_penalty:repetition_penalty:"
            "no_repeat_ngram_size:max_new_tokens (or none for max_length). "
            "Defaults to a safe four-run grid."
        ),
    )
    parser.add_argument("--maximum-over-3-rate", type=float, default=2.0)
    parser.add_argument("--maximum-repeated-trigram-rate", type=float, default=15.0)
    parser.add_argument("--maximum-dominant-token-over-20-rate", type=float, default=5.0)
    parser.add_argument("--merge-lora", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.samples < 1 or args.batch_size < 1:
        raise ValueError("samples and batch-size must be positive")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(
            f"Sweep output is not empty: {args.output_dir}. Use a new directory."
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    config = ExperimentConfig.from_json(args.config)
    if args.allow_cpu:
        config.apply_overrides(allow_cpu=True)
    config.training.checkpoint_eval_samples = args.samples
    runner = BaselineRunner(config)
    runner._validate_dataset_contract()

    try:
        import torch
    except ImportError as error:
        raise RuntimeError("PyTorch is required for generation sweep") from error
    if config.training.require_cuda and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; --allow-cpu is only for a tiny smoke test")
    tokenizer, model = load_inference_model(
        config,
        saved_model_dir=args.saved_model_dir,
        merge_lora=args.merge_lora,
    )
    records = JsonlCorpus(
        config.data.validation_file,
        direction=config.direction,
        source_field=config.data.source_field,
        target_field=config.data.target_field,
        limit=config.data.max_validation_samples,
    ).load()
    prepared = TokenizerAuditor(
        tokenizer,
        max_source_length=config.data.max_source_length,
        max_target_length=config.data.max_target_length,
        batch_size=config.data.audit_batch_size,
        policy=config.data.overlength_policy,
    ).prepare(records)
    subset, subset_report = runner._checkpoint_validation_dataset(prepared)
    selected = subset.records
    chunks = [
        DocumentChunk(
            index=index,
            source=record.source,
            separator_before="",
            separator_after="",
            source_tokens=token_length(tokenizer, record.source),
        )
        for index, record in enumerate(selected)
    ]
    write_json(args.output_dir / "subset.json", subset_report)

    candidates = args.candidate or [parse_candidate(value) for value in DEFAULT_CANDIDATES]
    metric_suite = TranslationMetricSuite(tokenizer)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    summaries = []
    for candidate in candidates:
        print(
            f"[sweep] Starting {candidate['name']} on {len(selected)} records...",
            flush=True,
        )
        candidate_config = deepcopy(config)
        generation = candidate_config.generation
        generation.num_beams = candidate["num_beams"]
        generation.length_penalty = candidate["length_penalty"]
        generation.repetition_penalty = candidate["repetition_penalty"]
        generation.no_repeat_ngram_size = candidate["no_repeat_ngram_size"]
        generation.max_new_tokens = candidate["max_new_tokens"]
        generation.validate()
        predictions, runtime = translate_chunks(
            chunks,
            tokenizer=tokenizer,
            model=model,
            config=candidate_config,
            batch_size=args.batch_size,
            device=device,
        )
        metrics = metric_suite.score_texts(
            predictions, [record.target for record in selected]
        )
        metrics.update(
            metric_suite.score_source_preservation(
                predictions, [record.source for record in selected]
            )
        )
        metrics["runtime_seconds"] = runtime["runtime_seconds"]
        metrics["samples_per_second"] = round(
            len(selected) / max(runtime["runtime_seconds"], 1e-9), 6
        )
        eligible = (
            metrics["empty_output_rate"] == 0
            and metrics["length_ratio_over_3_rate"] <= args.maximum_over_3_rate
            and metrics["repeated_trigram_rate"]
            <= args.maximum_repeated_trigram_rate
            and metrics["dominant_token_over_20_rate"]
            <= args.maximum_dominant_token_over_20_rate
        )
        summary = {
            "name": candidate["name"],
            "eligible": eligible,
            "generation": asdict(generation),
            "metrics": metrics,
        }
        summaries.append(summary)
        print(
            f"[sweep] {candidate['name']}: chrF++={metrics['chrf']:.3f}, "
            f"BLEU={metrics['bleu']:.3f}, over3={metrics['length_ratio_over_3_rate']:.2f}%, "
            f"eligible={eligible}",
            flush=True,
        )
        write_json(args.output_dir / f"{candidate['name']}_metrics.json", summary)
        write_jsonl(
            args.output_dir / f"{candidate['name']}_predictions.jsonl",
            (
                record.to_output_mapping(prediction)
                for record, prediction in zip(selected, predictions, strict=True)
            ),
        )

    eligible = [summary for summary in summaries if summary["eligible"]]
    pool = eligible or summaries
    recommended = max(
        pool,
        key=lambda summary: (
            summary["metrics"]["chrf"],
            summary["metrics"]["bleu"],
            -summary["metrics"]["runtime_seconds"],
        ),
    )
    report = {
        "config": str(args.config.resolve()),
        "saved_model_dir": (
            str(args.saved_model_dir.resolve()) if args.saved_model_dir else None
        ),
        "subset": subset_report,
        "constraints": {
            "maximum_over_3_rate": args.maximum_over_3_rate,
            "maximum_repeated_trigram_rate": args.maximum_repeated_trigram_rate,
            "maximum_dominant_token_over_20_rate": (
                args.maximum_dominant_token_over_20_rate
            ),
        },
        "candidates": summaries,
        "recommended": recommended["name"],
        "recommendation_used_fallback": not bool(eligible),
    }
    write_json(args.output_dir / "sweep_summary.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
