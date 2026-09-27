"""Command line entry point for VinAI audit, zero-shot, and fine-tuning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import ExperimentConfig
from .runner import BaselineRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "evaluate", "train"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--train-file")
    parser.add_argument("--validation-file")
    parser.add_argument("--max-train-samples", type=int)
    parser.add_argument("--max-validation-samples", type=int)
    parser.add_argument("--resume-from-checkpoint")
    parser.add_argument(
        "--allow-cpu",
        action="store_true",
        help="Allow CPU only for a small smoke test; full training is impractical.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ExperimentConfig.from_json(args.config)
    config.apply_overrides(
        output_dir=args.output_dir,
        train_file=args.train_file,
        validation_file=args.validation_file,
        max_train_samples=args.max_train_samples,
        max_validation_samples=args.max_validation_samples,
        resume_from_checkpoint=args.resume_from_checkpoint,
        allow_cpu=args.allow_cpu,
    )
    runner = BaselineRunner(config)
    if args.command == "audit":
        result = runner.audit()
    elif args.command == "evaluate":
        if config.training.mode != "none":
            raise ValueError("The evaluate command requires a zero-shot mode='none' config")
        result = runner.evaluate()
    else:
        result = runner.train()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
