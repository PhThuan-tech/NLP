"""Merge a trained LoRA adapter into its pinned VinAI base model for inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import ExperimentConfig
from .data import sha256_file, write_json
from .inference import load_inference_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ExperimentConfig.from_json(args.config)
    if config.training.mode != "lora":
        raise ValueError("merge_lora requires a config with training.mode='lora'")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(
            f"Merge output is not empty: {args.output_dir}. Use a new directory."
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer, model = load_inference_model(
        config,
        saved_model_dir=args.adapter_dir,
        merge_lora=True,
    )
    model.save_pretrained(args.output_dir, safe_serialization=True)
    tokenizer.save_pretrained(args.output_dir)
    files = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(args.output_dir.iterdir())
        if path.is_file()
    }
    manifest = {
        "base_model": config.model_name,
        "base_model_revision": config.model_revision,
        "adapter_dir": str(args.adapter_dir.resolve()),
        "direction": config.direction,
        "training_seed": config.seed,
        "files": files,
    }
    write_json(args.output_dir / "merge_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
