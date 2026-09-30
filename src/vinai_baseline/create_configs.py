"""Create six frozen experiment configs for a newly finalized dataset."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence


CONFIG_NAMES = (
    "en2vi_zero_shot.json",
    "en2vi_lora.json",
    "en2vi_full.json",
    "vi2en_zero_shot.json",
    "vi2en_lora.json",
    "vi2en_full.json",
)


def _portable_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def create_configs(
    *,
    project_root: Path,
    dataset_dir: Path,
    output_dir: Path,
    learning_rate: float = 5e-5,
    checkpoint_samples: int = 256,
    length_penalty: float = 0.8,
    repetition_penalty: float = 1.1,
    max_new_tokens: int = 448,
    overwrite: bool = False,
) -> dict[str, Any]:
    if learning_rate <= 0:
        raise ValueError("learning_rate must be positive")
    if checkpoint_samples < 1:
        raise ValueError("checkpoint_samples must be positive")
    if length_penalty <= 0 or repetition_penalty <= 0:
        raise ValueError("generation penalties must be positive")
    if max_new_tokens < 8:
        raise ValueError("max_new_tokens must be at least 8")
    manifest_path = dataset_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Dataset manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("semantic_audit_only"):
        raise ValueError(
            "Cannot create experiment configs from a score-only semantic audit; "
            "freeze the dataset first"
        )
    dataset_id = str(manifest.get("dataset_id", "")).strip()
    split_seed = manifest.get("split_contract", {}).get("seed")
    if not dataset_id or split_seed != 67:
        raise ValueError("The frozen dataset must have a dataset_id and split seed 67")
    required = [
        dataset_dir / f"segments_{split}_{direction}.jsonl"
        for split in ("train", "dev")
        for direction in ("en2vi", "vi2en")
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Frozen dataset files are missing: " + ", ".join(missing))
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"Config output is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    template_dir = project_root / "configs/vinai"
    created = []
    for name in CONFIG_NAMES:
        template = json.loads((template_dir / name).read_text(encoding="utf-8"))
        config = deepcopy(template)
        direction = str(config["direction"])
        mode = str(config["training"]["mode"])
        config["run_name"] = f"{config['run_name']}_{dataset_id}"
        config["seed"] = 67
        mode_label = "zero_shot" if mode == "none" else mode
        config["output_dir"] = f"outputs/{dataset_id}/{direction}/{mode_label}"
        config["data"].update(
            {
                "dataset_id": dataset_id,
                "manifest_file": _portable_path(manifest_path, project_root),
                "train_file": (
                    ""
                    if mode == "none"
                    else _portable_path(
                        dataset_dir / f"segments_train_{direction}.jsonl",
                        project_root,
                    )
                ),
                "validation_file": _portable_path(
                    dataset_dir / f"segments_dev_{direction}.jsonl", project_root
                ),
                "overlength_policy": "error",
            }
        )
        config["generation"].update(
            {
                "max_new_tokens": max_new_tokens,
                "length_penalty": length_penalty,
                "repetition_penalty": repetition_penalty,
                "renormalize_logits": True,
            }
        )
        if mode != "none":
            config["training"]["checkpoint_eval_samples"] = checkpoint_samples
            config["training"]["checkpoint_max_per_document"] = 6
        if mode == "lora":
            config["training"]["learning_rate"] = learning_rate
        destination = output_dir / name
        destination.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        created.append(str(destination))
    report = {
        "dataset_id": dataset_id,
        "split_seed": 67,
        "dataset_manifest": _portable_path(manifest_path, project_root),
        "learning_rate_lora": learning_rate,
        "checkpoint_samples": checkpoint_samples,
        "generation": {
            "length_penalty": length_penalty,
            "repetition_penalty": repetition_penalty,
            "max_new_tokens": max_new_tokens,
        },
        "created": created,
    }
    (output_dir / "configuration_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--checkpoint-samples", type=int, default=256)
    parser.add_argument("--length-penalty", type=float, default=0.8)
    parser.add_argument("--repetition-penalty", type=float, default=1.1)
    parser.add_argument("--max-new-tokens", type=int, default=448)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = create_configs(
        project_root=args.project_root,
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        learning_rate=args.learning_rate,
        checkpoint_samples=args.checkpoint_samples,
        length_penalty=args.length_penalty,
        repetition_penalty=args.repetition_penalty,
        max_new_tokens=args.max_new_tokens,
        overwrite=args.overwrite,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
