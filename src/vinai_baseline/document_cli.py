"""Translate one UTF-8 Markdown document with a frozen VinAI experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import ExperimentConfig
from .data import write_json
from .inference import (
    assemble_document,
    load_inference_model,
    markdown_structure_report,
    split_markdown_document,
    translate_chunks,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--saved-model-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--maximum-source-tokens", type=int, default=448)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--merge-lora", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ExperimentConfig.from_json(args.config)
    if args.allow_cpu:
        config.apply_overrides(allow_cpu=True)
    try:
        import torch
    except ImportError as error:
        raise RuntimeError("PyTorch is required for document inference") from error
    if config.training.require_cuda and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; use --allow-cpu only for a small smoke test")
    tokenizer, model = load_inference_model(
        config,
        saved_model_dir=args.saved_model_dir,
        merge_lora=args.merge_lora,
    )
    source = args.input.read_text(encoding="utf-8")
    chunks = split_markdown_document(
        source,
        tokenizer,
        maximum_tokens=args.maximum_source_tokens,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    predictions, report = translate_chunks(
        chunks,
        tokenizer=tokenizer,
        model=model,
        config=config,
        batch_size=args.batch_size,
        device=device,
    )
    output = assemble_document(chunks, predictions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8", newline="\n")
    report.update(
        {
            "input": str(args.input.resolve()),
            "output": str(args.output.resolve()),
            "input_characters": len(source),
            "output_characters": len(output),
            "merge_lora": args.merge_lora,
            "markdown_structure": markdown_structure_report(source, output),
            "chunk_map": [
                {
                    "index": chunk.index,
                    "source_tokens": chunk.source_tokens,
                    "source_characters": len(chunk.source),
                    "prediction_characters": len(predictions[chunk.index]),
                }
                for chunk in chunks
            ],
        }
    )
    report_path = args.report or args.output.with_suffix(args.output.suffix + ".report.json")
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
