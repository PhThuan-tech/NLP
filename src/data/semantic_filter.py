"""Semantic quality gate for heuristically aligned EN-VI training segments.

This stage is intentionally separate from structural preparation: the first
stage remains fast and auditable, while this stage may use a GPU and download a
multilingual embedding model. It reads only EN->VI files, scores each pair, and
writes both translation directions for pairs that pass the threshold.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Protocol, Sequence

import numpy as np


class SentenceEncoder(Protocol):
    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray: ...


@dataclass(frozen=True)
class SemanticFilterConfig:
    model_name: str = "sentence-transformers/LaBSE"
    minimum_similarity: float = 0.72
    batch_size: int = 64
    device: str | None = None

    def validate(self) -> None:
        if not -1 <= self.minimum_similarity <= 1:
            raise ValueError("minimum_similarity must be between -1 and 1")
        if self.batch_size < 1:
            raise ValueError("batch_size must be positive")


def read_jsonl(path: Path) -> Iterator[dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at {path}:{line_number}") from error


def batched(
    records: Iterable[dict[str, object]], batch_size: int
) -> Iterator[list[dict[str, object]]]:
    batch: list[dict[str, object]] = []
    for record in records:
        batch.append(record)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def score_batch(
    records: Sequence[dict[str, object]],
    encoder: SentenceEncoder,
    batch_size: int,
) -> np.ndarray:
    sources = [str(record["source"]) for record in records]
    targets = [str(record["target"]) for record in records]
    source_embeddings = encoder.encode(
        sources,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    target_embeddings = encoder.encode(
        targets,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    if source_embeddings.shape != target_embeddings.shape:
        raise ValueError("Source and target embedding shapes differ")
    return np.sum(source_embeddings * target_embeddings, axis=1)


def reverse_direction(record: dict[str, object]) -> dict[str, object]:
    result = dict(record)
    segment_id = str(result["segment_id"])
    if segment_id.endswith("::en2vi"):
        segment_id = segment_id[: -len("::en2vi")] + "::vi2en"
    result.update(
        {
            "segment_id": segment_id,
            "direction": "vi2en",
            "source_lang": "vi",
            "target_lang": "en",
            "source": record["target"],
            "target": record["source"],
            "source_word_count": record["target_word_count"],
            "target_word_count": record["source_word_count"],
        }
    )
    return result


def filter_file(
    input_path: Path,
    accepted_en2vi_path: Path,
    accepted_vi2en_path: Path,
    rejected_path: Path,
    encoder: SentenceEncoder,
    config: SemanticFilterConfig,
) -> dict[str, object]:
    config.validate()
    temp_paths = [
        path.with_suffix(path.suffix + ".tmp")
        for path in [accepted_en2vi_path, accepted_vi2en_path, rejected_path]
    ]
    accepted_count = 0
    rejected_count = 0
    similarities: list[float] = []

    with (
        temp_paths[0].open("w", encoding="utf-8", newline="\n") as en_handle,
        temp_paths[1].open("w", encoding="utf-8", newline="\n") as vi_handle,
        temp_paths[2].open("w", encoding="utf-8", newline="\n") as reject_handle,
    ):
        for batch in batched(read_jsonl(input_path), config.batch_size):
            scores = score_batch(batch, encoder, config.batch_size)
            for record, raw_score in zip(batch, scores, strict=True):
                score = float(raw_score)
                similarities.append(score)
                scored = {**record, "semantic_similarity": score}
                if score >= config.minimum_similarity:
                    en_handle.write(json.dumps(scored, ensure_ascii=False) + "\n")
                    vi_handle.write(
                        json.dumps(reverse_direction(scored), ensure_ascii=False) + "\n"
                    )
                    accepted_count += 1
                else:
                    reject_handle.write(
                        json.dumps(
                            {
                                **scored,
                                "semantic_rejection_reason": "similarity_below_threshold",
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    rejected_count += 1

    for temp_path, final_path in zip(
        temp_paths,
        [accepted_en2vi_path, accepted_vi2en_path, rejected_path],
        strict=True,
    ):
        temp_path.replace(final_path)

    score_array = np.asarray(similarities, dtype=np.float32)
    return {
        "input": str(input_path),
        "accepted": accepted_count,
        "rejected": rejected_count,
        "acceptance_rate": (
            accepted_count / (accepted_count + rejected_count)
            if accepted_count + rejected_count
            else 0.0
        ),
        "similarity_mean": float(score_array.mean()) if len(score_array) else None,
        "similarity_p05": float(np.quantile(score_array, 0.05)) if len(score_array) else None,
        "similarity_p50": float(np.quantile(score_array, 0.50)) if len(score_array) else None,
        "similarity_p95": float(np.quantile(score_array, 0.95)) if len(score_array) else None,
    }


def run_semantic_filter(
    input_dir: Path,
    output_dir: Path,
    encoder: SentenceEncoder,
    config: SemanticFilterConfig,
    overwrite: bool = False,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_outputs = [
        output_dir / f"segments_{split}_{direction}.jsonl"
        for split in ["train", "dev", "public_test"]
        for direction in ["en2vi", "vi2en"]
    ] + [
        output_dir / f"rejected_semantic_{split}.jsonl"
        for split in ["train", "dev", "public_test"]
    ]
    existing = [path for path in expected_outputs if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            f"Semantic output already exists: {existing[0]}. Use --overwrite."
        )

    split_reports: dict[str, object] = {}
    for split in ["train", "dev", "public_test"]:
        input_path = input_dir / f"segments_{split}_en2vi.jsonl"
        if not input_path.exists():
            raise FileNotFoundError(input_path)
        split_reports[split] = filter_file(
            input_path=input_path,
            accepted_en2vi_path=output_dir / f"segments_{split}_en2vi.jsonl",
            accepted_vi2en_path=output_dir / f"segments_{split}_vi2en.jsonl",
            rejected_path=output_dir / f"rejected_semantic_{split}.jsonl",
            encoder=encoder,
            config=config,
        )

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_name": config.model_name,
        "minimum_similarity": config.minimum_similarity,
        "batch_size": config.batch_size,
        "device": config.device,
        "splits": split_reports,
    }
    manifest_path = output_dir / "semantic_filter_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir", type=Path, default=Path("artifacts/processed")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("artifacts/semantic")
    )
    parser.add_argument(
        "--model-name", default="sentence-transformers/LaBSE"
    )
    parser.add_argument("--minimum-similarity", type=float, default=0.72)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    config = SemanticFilterConfig(
        model_name=args.model_name,
        minimum_similarity=args.minimum_similarity,
        batch_size=args.batch_size,
        device=args.device,
    )
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise SystemExit(
            "sentence-transformers is required. Install requirements-semantic.txt"
        ) from error
    encoder = SentenceTransformer(config.model_name, device=config.device)
    manifest = run_semantic_filter(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        encoder=encoder,
        config=config,
        overwrite=args.overwrite,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
