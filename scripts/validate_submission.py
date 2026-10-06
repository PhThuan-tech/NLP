"""Validate the two merged models before creating the VLSP submission image."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path


MODEL_SPECS = {
    "en2vi": {
        "base_model": "vinai/vinai-translate-en2vi-v2",
        "revision": "1e47495b5dac16097b1d9e7b4133c27e1f40504f",
    },
    "vi2en": {
        "base_model": "vinai/vinai-translate-vi2en-v2",
        "revision": "4eb2219d447d4352861e71e371a6b6abcb0509c8",
    },
}
PARAMETER_LIMIT = 3_000_000_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safetensors_parameters(path: Path) -> int:
    with path.open("rb") as handle:
        raw_length = handle.read(8)
        if len(raw_length) != 8:
            raise ValueError(f"Invalid safetensors header: {path}")
        header_length = struct.unpack("<Q", raw_length)[0]
        if header_length <= 0 or header_length > 100 * 1024 * 1024:
            raise ValueError(f"Unsafe safetensors header length in {path}: {header_length}")
        header = json.loads(handle.read(header_length))
    total = 0
    for name, metadata in header.items():
        if name == "__metadata__":
            continue
        shape = metadata.get("shape")
        if not isinstance(shape, list) or not all(isinstance(value, int) and value >= 0 for value in shape):
            raise ValueError(f"Invalid tensor shape for {name!r} in {path}")
        total += math.prod(shape)
    return total


def weight_files(model_dir: Path) -> list[Path]:
    index_files = sorted(model_dir.glob("*.safetensors.index.json"))
    if index_files:
        names: set[str] = set()
        for index_path in index_files:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            names.update(index.get("weight_map", {}).values())
        files = [model_dir / name for name in sorted(names)]
    else:
        files = sorted(model_dir.glob("*.safetensors"))
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing safetensors shard(s): " + ", ".join(missing))
    if not files:
        raise FileNotFoundError(
            f"No safetensors weights in {model_dir}. Merge with safe_serialization=True."
        )
    return files


def validate_model(direction: str, model_dir: Path) -> dict:
    model_dir = model_dir.resolve()
    if not model_dir.is_dir():
        raise FileNotFoundError(f"Missing {direction} model directory: {model_dir}")
    for required in ("config.json", "merge_manifest.json"):
        if not (model_dir / required).is_file():
            raise FileNotFoundError(f"Missing {required} in {model_dir}")
    tokenizer_files = [
        path for path in model_dir.iterdir()
        if path.is_file() and (
            path.name.startswith("tokenizer")
            or path.name.startswith("sentencepiece")
            or path.name.startswith("spiece")
            or path.name in {"source.spm", "target.spm"}
        )
    ]
    if not tokenizer_files:
        raise FileNotFoundError(f"Missing tokenizer files in {model_dir}")

    manifest = json.loads((model_dir / "merge_manifest.json").read_text(encoding="utf-8"))
    expected = MODEL_SPECS[direction]
    identity = {
        "direction": manifest.get("direction"),
        "base_model": manifest.get("base_model"),
        "base_model_revision": manifest.get("base_model_revision"),
    }
    required_identity = {
        "direction": direction,
        "base_model": expected["base_model"],
        "base_model_revision": expected["revision"],
    }
    if identity != required_identity:
        raise ValueError(
            f"Wrong {direction} merge identity: {identity}; expected {required_identity}"
        )

    checked_manifest_files = 0
    for name, expected_file in manifest.get("files", {}).items():
        path = model_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"Manifest file is missing: {path}")
        if path.stat().st_size != expected_file.get("bytes"):
            raise ValueError(f"Size mismatch for {path}")
        if sha256_file(path) != expected_file.get("sha256"):
            raise ValueError(f"SHA-256 mismatch for {path}")
        checked_manifest_files += 1
    if checked_manifest_files == 0:
        raise ValueError(f"Merge manifest has no file inventory: {model_dir}")

    weights = weight_files(model_dir)
    parameter_count = sum(safetensors_parameters(path) for path in weights)
    if parameter_count <= 0:
        raise ValueError(f"No model parameters found in {model_dir}")
    return {
        "direction": direction,
        "model_dir": str(model_dir),
        "base_model": expected["base_model"],
        "base_model_revision": expected["revision"],
        "parameter_count": parameter_count,
        "weight_files": [path.name for path in weights],
        "manifest_files_checked": checked_manifest_files,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--en2vi-dir", type=Path, required=True)
    parser.add_argument("--vi2en-dir", type=Path, required=True)
    parser.add_argument("--json-output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    models = [
        validate_model("en2vi", args.en2vi_dir),
        validate_model("vi2en", args.vi2en_dir),
    ]
    total = sum(model["parameter_count"] for model in models)
    if total >= PARAMETER_LIMIT:
        raise ValueError(
            f"Aggregate parameter count {total:,} is not below the 3B limit"
        )
    report = {
        "status": "passed",
        "parameter_limit": PARAMETER_LIMIT,
        "aggregate_parameter_count": total,
        "models": models,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
