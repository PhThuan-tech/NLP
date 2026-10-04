"""Download pinned VinAI snapshots and Linux wheels for offline Kaggle runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


MODELS = {
    "en2vi": (
        "vinai/vinai-translate-en2vi-v2",
        "1e47495b5dac16097b1d9e7b4133c27e1f40504f",
        "vinai-translate-en2vi-v2",
    ),
    "vi2en": (
        "vinai/vinai-translate-vi2en-v2",
        "4eb2219d447d4352861e71e371a6b6abcb0509c8",
        "vinai-translate-vi2en-v2",
    ),
}
MODEL_FILES = (
    "config.json",
    "generation_config.json",
    "model.safetensors",
    "sentencepiece.bpe.model",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_directory(source: Path, destination: Path) -> None:
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and ".cache" not in path.parts:
                archive.write(path, (Path(source.name) / path.relative_to(source)).as_posix())


def download_model(direction: str, output: Path) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as error:
        raise SystemExit(
            "Install the downloader first: python -m pip install -U huggingface_hub"
        ) from error
    repo_id, revision, folder = MODELS[direction]
    destination = output / "models" / folder
    destination.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo_id,
        revision=revision,
        local_dir=destination,
        allow_patterns=list(MODEL_FILES),
    )
    cache = destination / ".cache"
    if cache.exists():
        shutil.rmtree(cache)
    missing = [name for name in MODEL_FILES if not (destination / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Incomplete {direction} snapshot: {missing}")
    manifest = {
        "repo_id": repo_id,
        "revision": revision,
        "files": {
            name: {
                "bytes": (destination / name).stat().st_size,
                "sha256": sha256_file(destination / name),
            }
            for name in MODEL_FILES
        },
    }
    (destination / "offline_model_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    archive = output / f"{folder}.zip"
    zip_directory(destination, archive)
    print(f"MODEL {direction}: {archive} ({archive.stat().st_size / 1024**3:.2f} GiB)")
    return archive


def download_wheelhouse(project: Path, output: Path, python_version: str) -> Path:
    destination = output / "wheelhouse"
    destination.mkdir(parents=True, exist_ok=True)
    requirement = project / "requirements-training-colab.txt"
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--dest",
        str(destination),
        "--only-binary=:all:",
        "--platform",
        "manylinux_2_28_x86_64",
        "--platform",
        "manylinux_2_17_x86_64",
        "--platform",
        "manylinux2014_x86_64",
        "--python-version",
        python_version,
        "--implementation",
        "cp",
        "--abi",
        f"cp{python_version}",
        "-r",
        str(requirement),
    ]
    subprocess.run(command, cwd=project, check=True)
    # Kaggle supplies its CUDA-matched PyTorch stack. Shipping these wheels is
    # large and risks replacing the runtime build.
    excluded_prefixes = ("torch-", "torch_", "nvidia_", "triton-")
    for wheel in destination.glob("*.whl"):
        if wheel.name.casefold().startswith(excluded_prefixes):
            wheel.unlink()
    archive = output / "vinai-training-wheelhouse-py313-linux.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for wheel in sorted(destination.glob("*.whl")):
            zipped.write(wheel, f"wheelhouse/{wheel.name}")
    print(f"WHEELHOUSE: {archive} ({archive.stat().st_size / 1024**2:.2f} MiB)")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("offline_training_assets"))
    parser.add_argument(
        "--directions", choices=("en2vi", "vi2en", "both"), default="both"
    )
    parser.add_argument("--python-version", default="313")
    parser.add_argument("--skip-models", action="store_true")
    parser.add_argument("--skip-wheelhouse", action="store_true")
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    directions = tuple(MODELS) if args.directions == "both" else (args.directions,)
    if not args.skip_models:
        for direction in directions:
            download_model(direction, output)
    if not args.skip_wheelhouse:
        download_wheelhouse(project, output, args.python_version)
    print("Offline assets ready:", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
