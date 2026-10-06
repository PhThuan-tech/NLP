"""Fixed 256-record zero-shot gate or old-adapter diagnostic without retraining."""
import argparse
from dataclasses import asdict
from pathlib import Path

from .config import ExperimentConfig
from .data import JsonlCorpus, TokenizerAuditor, sha256_file, write_json, write_jsonl
from .inference import DocumentChunk, load_inference_model, token_length, translate_chunks
from .language import LANGUAGE_CONTROL_VERSION
from .metrics import TranslationMetricSuite
from .quality import QUALITY_GATE_VERSION, quality_report
from .runner import BaselineRunner


def identity(config):
    """Bind gate results to data, direction, model, decoding and implementation."""
    modules = ("language.py", "modeling.py", "data.py", "inference.py", "quality.py", "preflight_cli.py", "runner.py", "config.py")
    return {"model": config.model_name, "revision": config.model_revision,
            "direction": config.direction, "seed": config.seed,
            "dataset_id": config.data.dataset_id,
            "manifest_sha256": sha256_file(config.data.manifest_file),
            "validation_sha256": sha256_file(config.data.validation_file),
            "generation": asdict(config.generation),
            "max_source_length": config.data.max_source_length,
            "max_target_length": config.data.max_target_length,
            "overlength_policy": config.data.overlength_policy,
            "language_control_version": LANGUAGE_CONTROL_VERSION,
            "quality_gate_version": QUALITY_GATE_VERSION,
            "code": {name: sha256_file(Path(__file__).with_name(name)) for name in modules}}


def require_zero_shot_gate(config, report_path):
    import json
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    expected_identity = identity(config)
    mismatches = []
    if report.get("kind") != "zero_shot":
        mismatches.append(f"kind={report.get('kind')!r}")
    actual_identity = report.get("identity")
    if actual_identity != expected_identity:
        actual_identity = actual_identity if isinstance(actual_identity, dict) else {}
        fields = sorted(
            key
            for key in set(actual_identity) | set(expected_identity)
            if actual_identity.get(key) != expected_identity.get(key)
        )
        mismatches.append("identity fields=" + ",".join(fields))
    if report.get("requested_samples") != 256:
        mismatches.append(f"requested_samples={report.get('requested_samples')!r}")
    quality = report.get("quality", {})
    if quality.get("evaluated_records") != 256:
        mismatches.append(f"evaluated_records={quality.get('evaluated_records')!r}")
    if quality.get("status") != "passed":
        mismatches.append(f"quality.status={quality.get('status')!r}")
    if mismatches:
        raise ValueError(
            "A passing zero-shot 256 gate with matching data/model/decoding/code "
            "is required. Mismatch: " + "; ".join(mismatches)
        )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--saved-model-dir", type=Path)
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args(argv)
    if args.samples < 1 or args.batch_size < 1:
        raise ValueError("samples and batch-size must be positive")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(f"Use a fresh diagnostic output: {args.output_dir}")
    config = ExperimentConfig.from_json(args.config)
    if args.saved_model_dir is None:
        config.training.mode = "none"
    elif config.training.mode == "none":
        raise ValueError("Adapter diagnostic requires the matching LoRA/full config")
    config.data.max_validation_samples = None
    config.training.checkpoint_eval_samples = args.samples
    runner = BaselineRunner(config)
    runner._validate_dataset_contract()
    import torch
    from transformers import set_seed
    if not torch.cuda.is_available() and not args.allow_cpu:
        raise RuntimeError("Enable GPU; --allow-cpu is only for small local diagnostics")
    set_seed(config.seed)
    print("Loading model/tokenizer with corrected language control...", flush=True)
    tokenizer, model = load_inference_model(config, saved_model_dir=args.saved_model_dir)
    corpus = JsonlCorpus(config.data.validation_file, direction=config.direction,
                        source_field=config.data.source_field, target_field=config.data.target_field).load()
    prepared = TokenizerAuditor(tokenizer, max_source_length=config.data.max_source_length,
        max_target_length=config.data.max_target_length, batch_size=config.data.audit_batch_size,
        policy=config.data.overlength_policy).prepare(corpus)
    subset, subset_report = runner._checkpoint_validation_dataset(prepared)
    if len(subset.records) != args.samples:
        raise ValueError("Not enough retained records for the requested diagnostic")
    chunks = [DocumentChunk(index=i, source=r.source, separator_before="", separator_after="",
                            source_tokens=token_length(tokenizer, r.source))
              for i, r in enumerate(subset.records)]
    write_json(args.output_dir / "subset.json", subset_report)
    print(f"Generating {len(chunks)} fixed validation records; no training.", flush=True)
    predictions, runtime = translate_chunks(chunks, tokenizer=tokenizer, model=model, config=config,
        batch_size=args.batch_size, device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        fail_on_empty=False, log_progress=True)
    refs = [r.target for r in subset.records]
    suite = TranslationMetricSuite(tokenizer)
    metrics = suite.score_texts(predictions, refs)
    metrics.update(suite.score_source_preservation(predictions, [r.source for r in subset.records]))
    report = {"kind": "adapter" if args.saved_model_dir else "zero_shot",
              "identity": identity(config), "requested_samples": args.samples,
              "saved_model_dir": str(args.saved_model_dir) if args.saved_model_dir else None,
              "metrics": metrics, "runtime": runtime,
              "quality": quality_report(predictions, refs, config.direction,
                                        [r.segment_id for r in subset.records])}
    write_jsonl(args.output_dir / "predictions.jsonl",
                [r.to_output_mapping(p) for r, p in zip(subset.records, predictions, strict=True)])
    write_json(args.output_dir / "gate_report.json", report)
    quality = report["quality"]
    print(f"{report['kind']}: BLEU={metrics['bleu']:.3f}, chrF++={metrics['chrf']:.3f}; "
          f"gate={quality['status']}; hard_failures={quality['failed_records']}; "
          f"warnings={quality['warning_records']}; report={args.output_dir / 'gate_report.json'}", flush=True)
    return 0 if report["quality"]["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
