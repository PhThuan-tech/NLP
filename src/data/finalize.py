"""Finalize a frozen EN-VI dataset with deterministic leakage and quality gates."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import shutil
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Protocol, Sequence

import numpy as np


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


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


def batched(
    records: Iterable[dict[str, Any]], batch_size: int
) -> Iterator[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for record in records:
        batch.append(record)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def score_batch(
    records: Sequence[dict[str, Any]],
    encoder: SentenceEncoder,
    batch_size: int,
) -> np.ndarray:
    sources = [str(record["source"]) for record in records]
    targets = [str(record["target"]) for record in records]
    encode_kwargs = {
        "batch_size": batch_size,
        "convert_to_numpy": True,
        "normalize_embeddings": True,
        "show_progress_bar": False,
    }
    source_embeddings = encoder.encode(sources, **encode_kwargs)
    target_embeddings = encoder.encode(targets, **encode_kwargs)
    if source_embeddings.shape != target_embeddings.shape:
        raise ValueError("Source and target embedding shapes differ")
    return np.sum(source_embeddings * target_embeddings, axis=1)


TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
VIETNAMESE_MARK_RE = re.compile(
    r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩị"
    r"óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]",
    re.IGNORECASE,
)
ENGLISH_MARKERS = {
    "the", "and", "of", "to", "in", "for", "on", "with", "is", "are",
    "shall", "this", "that", "from", "by", "article", "clause", "section",
    "law", "government", "ministry", "decision", "decree", "rights",
}
VIETNAMESE_MARKERS = {
    "và", "của", "có", "được", "trong", "cho", "với", "theo", "này", "là",
    "tại", "từ", "điều", "khoản", "mục", "luật", "chính", "phủ", "nghị",
    "định", "quyết", "quyền", "trách", "nhiệm", "không",
}


@dataclass(frozen=True)
class FinalizationConfig:
    dataset_id: str = "legal_envi_clean_seed67_v2"
    split_seed: int = 67
    minimum_alignment_score: float = 0.75
    minimum_semantic_similarity: float | None = None
    semantic_model: str | None = None
    semantic_model_revision: str = "main"
    semantic_batch_size: int = 64
    reuse_semantic_scores: bool = False

    def validate(self) -> None:
        if not re.fullmatch(r"[a-z0-9_-]+", self.dataset_id):
            raise ValueError("dataset_id must use lowercase ASCII, digits, _ or -")
        if not 0 <= self.minimum_alignment_score <= 1:
            raise ValueError("minimum_alignment_score must be in [0, 1]")
        if self.minimum_semantic_similarity is not None:
            if not -1 <= self.minimum_semantic_similarity <= 1:
                raise ValueError("minimum_semantic_similarity must be in [-1, 1]")
            if not self.semantic_model:
                raise ValueError("semantic_model is required with a semantic threshold")
        if self.semantic_model and not self.semantic_model_revision.strip():
            raise ValueError("semantic_model_revision cannot be empty")
        if self.semantic_batch_size < 1:
            raise ValueError("semantic_batch_size must be positive")
        if self.reuse_semantic_scores and not self.semantic_model:
            raise ValueError("semantic_model identifies reused semantic scores")


def normalize_for_identity(text: str) -> str:
    return " ".join(str(text).casefold().split())


def language_scores(text: str) -> tuple[int, int, int]:
    tokens = TOKEN_RE.findall(str(text).casefold())
    english = sum(token in ENGLISH_MARKERS for token in tokens)
    vietnamese = sum(token in VIETNAMESE_MARKERS for token in tokens)
    marked = len(VIETNAMESE_MARK_RE.findall(str(text)))
    return english, vietnamese, marked


def language_rejection_reason(source: str, target: str) -> str | None:
    source_en, source_vi, source_marks = language_scores(source)
    target_en, target_vi, target_marks = language_scores(target)
    source_is_strong_vi = source_vi >= 5 and source_vi >= 2 * max(1, source_en)
    target_is_strong_en = (
        target_en >= 6
        and target_en >= 2 * max(1, target_vi)
        and target_marks == 0
    )
    if source_is_strong_vi and source_marks >= 3:
        return "source_looks_vietnamese"
    if target_is_strong_en:
        return "target_looks_english"
    return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at {path}:{line_number}") from error
            for field in ("segment_id", "source", "target", "direction"):
                if not str(row.get(field, "")).strip():
                    raise ValueError(f"Missing {field} at {path}:{line_number}")
            if row["direction"] != "en2vi":
                raise ValueError(f"Expected en2vi at {path}:{line_number}")
            rows.append(row)
    return rows


def reverse_direction(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    segment_id = str(result["segment_id"])
    if segment_id.endswith("::en2vi"):
        segment_id = segment_id[: -len("::en2vi")] + "::vi2en"
    result.update(
        segment_id=segment_id,
        direction="vi2en",
        source_lang="vi",
        target_lang="en",
        source=record["target"],
        target=record["source"],
        source_word_count=record.get("target_word_count"),
        target_word_count=record.get("source_word_count"),
    )
    for source_key, target_key in (
        ("source_token_count", "target_token_count"),
        ("semantic_source_token_count", "semantic_target_token_count"),
    ):
        if source_key in record or target_key in record:
            result[source_key] = record.get(target_key)
            result[target_key] = record.get(source_key)
    return result


def _reject(
    rejected: list[dict[str, Any]], row: dict[str, Any], reason: str
) -> None:
    rejected.append({**row, "finalization_rejection_reason": reason})


def deterministic_filter(
    rows: Sequence[dict[str, Any]],
    *,
    config: FinalizationConfig,
    forbidden_sources: set[str] | None = None,
    forbidden_targets: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    forbidden_sources = forbidden_sources or set()
    forbidden_targets = forbidden_targets or set()
    for row in rows:
        source = normalize_for_identity(row["source"])
        target = normalize_for_identity(row["target"])
        pair = (source, target)
        reason = None
        if source == target:
            reason = "identical_source_target"
        elif float(row.get("alignment_score_min", 1.0)) < config.minimum_alignment_score:
            reason = "alignment_score_below_threshold"
        elif pair in seen_pairs:
            reason = "duplicate_pair_same_split"
        elif source in forbidden_sources:
            reason = "source_overlap_with_dev"
        elif target in forbidden_targets:
            reason = "target_overlap_with_dev"
        else:
            reason = language_rejection_reason(str(row["source"]), str(row["target"]))
        if reason:
            _reject(rejected, row, reason)
            continue
        seen_pairs.add(pair)
        accepted.append(dict(row))
    return accepted, rejected


def semantic_filter(
    rows: Sequence[dict[str, Any]],
    *,
    encoder: SentenceEncoder,
    threshold: float | None,
    batch_size: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for batch in batched(rows, batch_size):
        scores = score_batch(batch, encoder, batch_size)
        token_metadata = semantic_token_metadata(batch, encoder)
        for row, raw_score, metadata in zip(
            batch, scores, token_metadata, strict=True
        ):
            score = float(raw_score)
            scored = {**row, **metadata, "semantic_similarity": score}
            if threshold is None or score >= threshold:
                accepted.append(scored)
            else:
                _reject(rejected, scored, "semantic_similarity_below_threshold")
    return accepted, rejected


def semantic_token_metadata(
    rows: Sequence[dict[str, Any]], encoder: SentenceEncoder
) -> list[dict[str, Any]]:
    """Expose SentenceTransformer truncation instead of silently hiding it."""

    tokenizer = getattr(encoder, "tokenizer", None)
    maximum = getattr(encoder, "max_seq_length", None)
    if tokenizer is None or maximum is None:
        return [{} for _ in rows]
    maximum = int(maximum)
    texts = [str(row["source"]) for row in rows] + [
        str(row["target"]) for row in rows
    ]
    encoded = tokenizer(
        texts,
        add_special_tokens=True,
        truncation=False,
        padding=False,
    )
    lengths = [len(ids) for ids in encoded["input_ids"]]
    split = len(rows)
    return [
        {
            "semantic_source_token_count": lengths[index],
            "semantic_target_token_count": lengths[index + split],
            "semantic_encoder_max_seq_length": maximum,
            "semantic_input_truncated": (
                lengths[index] > maximum or lengths[index + split] > maximum
            ),
        }
        for index in range(split)
    ]


def filter_existing_semantic_scores(
    rows: Sequence[dict[str, Any]], threshold: float | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        if row.get("semantic_similarity") is None:
            raise ValueError(
                "reuse_semantic_scores was requested but a row has no "
                f"semantic_similarity: {row.get('segment_id')}"
            )
        score = float(row["semantic_similarity"])
        if threshold is None or score >= threshold:
            accepted.append(dict(row))
        else:
            _reject(rejected, dict(row), "semantic_similarity_below_threshold")
    return accepted, rejected


def semantic_audit_report(
    rows_by_split: dict[str, Sequence[dict[str, Any]]],
) -> dict[str, Any]:
    """Summarize scored pairs without pretending a cosine score is a probability."""

    bins = (-1.0, 0.60, 0.65, 0.70, 0.72, 0.75, 0.80, 0.85, 0.90, 1.000001)
    maximums = sorted(
        {
            int(row["semantic_encoder_max_seq_length"])
            for rows in rows_by_split.values()
            for row in rows
            if row.get("semantic_encoder_max_seq_length") is not None
        }
    )
    report: dict[str, Any] = {
        "bins": list(bins),
        "encoder_max_seq_lengths": maximums,
        "splits": {},
    }
    for split, rows in rows_by_split.items():
        scored = [row for row in rows if row.get("semantic_similarity") is not None]
        values = np.asarray(
            [float(row["semantic_similarity"]) for row in scored], dtype=float
        )
        categories: dict[str, Any] = {}
        for category in sorted({str(row.get("category", "unknown")) for row in scored}):
            category_rows = [
                row for row in scored if str(row.get("category", "unknown")) == category
            ]
            category_values = np.asarray(
                [float(row["semantic_similarity"]) for row in category_rows],
                dtype=float,
            )
            bin_counts = {}
            for lower, upper in zip(bins, bins[1:]):
                label = f"[{lower:.2f},{upper:.2f})"
                bin_counts[label] = int(
                    np.sum((category_values >= lower) & (category_values < upper))
                )
            lowest = sorted(
                category_rows,
                key=lambda row: (
                    float(row["semantic_similarity"]),
                    str(row.get("segment_id", "")),
                ),
            )[:5]
            categories[category] = {
                "records": len(category_rows),
                "truncated_records": sum(
                    bool(row.get("semantic_input_truncated"))
                    for row in category_rows
                ),
                "truncated_rate": (
                    100
                    * sum(
                        bool(row.get("semantic_input_truncated"))
                        for row in category_rows
                    )
                    / len(category_rows)
                ),
                "p05": float(np.quantile(category_values, 0.05)),
                "p25": float(np.quantile(category_values, 0.25)),
                "p50": float(np.quantile(category_values, 0.50)),
                "p75": float(np.quantile(category_values, 0.75)),
                "p95": float(np.quantile(category_values, 0.95)),
                "bin_counts": bin_counts,
                "lowest_examples": [
                    {
                        "segment_id": row.get("segment_id"),
                        "score": row.get("semantic_similarity"),
                        "source_preview": str(row.get("source", ""))[:500],
                        "target_preview": str(row.get("target", ""))[:500],
                    }
                    for row in lowest
                ],
            }
        report["splits"][split] = {
            "records": len(scored),
            "truncated_records": sum(
                bool(row.get("semantic_input_truncated")) for row in scored
            ),
            "truncated_rate": (
                100
                * sum(bool(row.get("semantic_input_truncated")) for row in scored)
                / len(scored)
                if scored
                else 0.0
            ),
            "minimum": float(values.min()) if len(values) else None,
            "maximum": float(values.max()) if len(values) else None,
            "categories": categories,
        }
    return report


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    temporary.replace(path)
    return count


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finalize_dataset(
    input_dir: Path,
    output_dir: Path,
    config: FinalizationConfig,
    *,
    encoder: SentenceEncoder | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    config.validate()
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"Output is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    parent_manifest_path = input_dir / "manifest.json"
    parent_manifest_payload = (
        json.loads(parent_manifest_path.read_text(encoding="utf-8"))
        if parent_manifest_path.exists()
        else {}
    )
    parent_files = parent_manifest_payload.get("files")
    if parent_manifest_path.exists() and not isinstance(parent_files, dict):
        raise ValueError(f"Parent manifest has no file checksum map: {parent_manifest_path}")
    for filename, metadata in (parent_files or {}).items():
        expected_sha256 = metadata.get("sha256") if isinstance(metadata, dict) else None
        if not expected_sha256:
            raise ValueError(f"Parent manifest has no SHA-256 for {filename}")
        source_path = input_dir / filename
        if not source_path.is_file():
            raise FileNotFoundError(f"Parent manifest file is missing: {source_path}")
        if sha256_file(source_path).lower() != str(expected_sha256).lower():
            raise ValueError(f"Parent dataset checksum mismatch: {source_path}")
    parent_seed = (parent_manifest_payload.get("split_contract", {}) or {}).get(
        "seed"
    )
    if parent_seed is not None and int(parent_seed) != config.split_seed:
        raise ValueError(
            f"Parent split seed {parent_seed} does not match requested seed "
            f"{config.split_seed}"
        )
    if config.reuse_semantic_scores:
        parent_finalization = parent_manifest_payload.get("finalization", {}) or {}
        if not isinstance(parent_finalization, dict):
            raise ValueError("Parent dataset has an invalid finalization contract")
        if (
            parent_finalization.get("semantic_model") != config.semantic_model
            or parent_finalization.get("semantic_model_revision")
            != config.semantic_model_revision
        ):
            raise ValueError(
                "Reused semantic scores do not match semantic model/revision "
                "recorded by the parent dataset"
            )

    splits = {
        split: read_jsonl(input_dir / f"segments_{split}_en2vi.jsonl")
        for split in ("train", "dev", "public_test")
    }
    dev_clean, dev_rejected = deterministic_filter(splits["dev"], config=config)
    if config.semantic_model is not None:
        if encoder is None and not config.reuse_semantic_scores:
            raise ValueError("An encoder is required for semantic filtering")
        if config.reuse_semantic_scores:
            dev_clean, semantic_rejected = filter_existing_semantic_scores(
                dev_clean, config.minimum_semantic_similarity
            )
        else:
            dev_clean, semantic_rejected = semantic_filter(
                dev_clean,
                encoder=encoder,
                threshold=config.minimum_semantic_similarity,
                batch_size=config.semantic_batch_size,
            )
        dev_rejected.extend(semantic_rejected)

    # During score-only audit the semantic threshold is intentionally unknown.
    # Keep deterministic train rows available so freeze can recover a train row
    # when the colliding dev row is later rejected by the chosen threshold.
    semantic_audit_only = (
        config.semantic_model is not None
        and config.minimum_semantic_similarity is None
        and not config.reuse_semantic_scores
    )
    # Dev is finalized first so only examples that remain in the frozen benchmark
    # reserve matching source/target texts from training.
    dev_sources = {normalize_for_identity(row["source"]) for row in dev_clean}
    dev_targets = {normalize_for_identity(row["target"]) for row in dev_clean}
    train_clean, train_rejected = deterministic_filter(
        splits["train"],
        config=config,
        forbidden_sources=None if semantic_audit_only else dev_sources,
        forbidden_targets=None if semantic_audit_only else dev_targets,
    )
    public_clean, public_rejected = deterministic_filter(
        splits["public_test"], config=config
    )

    clean = {"train": train_clean, "dev": dev_clean, "public_test": public_clean}
    rejected = {
        "train": train_rejected,
        "dev": dev_rejected,
        "public_test": public_rejected,
    }
    if config.semantic_model is not None:
        for split in ("train", "public_test"):
            if config.reuse_semantic_scores:
                clean[split], semantic_rejected = filter_existing_semantic_scores(
                    clean[split], config.minimum_semantic_similarity
                )
            else:
                clean[split], semantic_rejected = semantic_filter(
                    clean[split],
                    encoder=encoder,
                    threshold=config.minimum_semantic_similarity,
                    batch_size=config.semantic_batch_size,
                )
            rejected[split].extend(semantic_rejected)
    empty_splits = [split for split, rows in clean.items() if not rows]
    if empty_splits:
        raise ValueError(
            "Finalization removed every record from: " + ", ".join(empty_splits)
        )

    counts: dict[str, int] = {}
    rejection_reasons: dict[str, dict[str, int]] = {}
    for split in ("train", "dev", "public_test"):
        counts[f"segments_{split}_en2vi"] = write_jsonl(
            output_dir / f"segments_{split}_en2vi.jsonl", clean[split]
        )
        counts[f"segments_{split}_vi2en"] = write_jsonl(
            output_dir / f"segments_{split}_vi2en.jsonl",
            (reverse_direction(row) for row in clean[split]),
        )
        counts[f"rejected_{split}"] = write_jsonl(
            output_dir / f"rejected_{split}.jsonl", rejected[split]
        )
        rejection_reasons[split] = dict(
            Counter(row["finalization_rejection_reason"] for row in rejected[split])
        )

    semantic_audit = None
    if config.semantic_model is not None:
        semantic_audit = semantic_audit_report(
            {
                split: [
                    *clean[split],
                    *[
                        row
                        for row in rejected[split]
                        if row.get("semantic_similarity") is not None
                    ],
                ]
                for split in ("train", "dev", "public_test")
            }
        )
        (output_dir / "semantic_audit.json").write_text(
            json.dumps(semantic_audit, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    source_split = input_dir / "document_splits.csv"
    if source_split.exists():
        shutil.copy2(source_split, output_dir / "document_splits.csv")

    files: dict[str, dict[str, Any]] = {}
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "manifest.json":
            entry: dict[str, Any] = {"sha256": sha256_file(path)}
            count_key = path.stem
            if count_key in counts:
                entry["records"] = counts[count_key]
            files[path.name] = entry

    parent_manifest = parent_manifest_path
    manifest = {
        "dataset_id": config.dataset_id,
        "parent_dataset": (
            parent_manifest_payload.get("dataset_id")
            if parent_manifest.exists()
            else None
        ),
        "parent_manifest_sha256": (
            sha256_file(parent_manifest) if parent_manifest.exists() else None
        ),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sentence_transformers_version": (
            package_version("sentence-transformers")
            if config.semantic_model is not None
            else None
        ),
        "semantic_audit_only": semantic_audit_only,
        "split_contract": {
            "method": "sklearn.model_selection.train_test_split",
            "unit": "duplicate_group",
            "stratify": "category",
            "seed": config.split_seed,
            "dev_ratio": 0.10,
        },
        "finalization": asdict(config),
        "counts": counts,
        "rejection_reasons": rejection_reasons,
        "semantic_audit": semantic_audit,
        "files": files,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-id", default="legal_envi_clean_seed67_v2")
    parser.add_argument("--split-seed", type=int, default=67)
    parser.add_argument("--minimum-alignment-score", type=float, default=0.75)
    parser.add_argument("--semantic-model")
    parser.add_argument("--semantic-model-revision", default="main")
    parser.add_argument("--minimum-semantic-similarity", type=float)
    parser.add_argument("--semantic-batch-size", type=int, default=64)
    parser.add_argument("--reuse-semantic-scores", action="store_true")
    parser.add_argument("--device")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = FinalizationConfig(
        dataset_id=args.dataset_id,
        split_seed=args.split_seed,
        minimum_alignment_score=args.minimum_alignment_score,
        minimum_semantic_similarity=args.minimum_semantic_similarity,
        semantic_model=args.semantic_model,
        semantic_model_revision=args.semantic_model_revision,
        semantic_batch_size=args.semantic_batch_size,
        reuse_semantic_scores=args.reuse_semantic_scores,
    )
    encoder = None
    if args.semantic_model is not None and not args.reuse_semantic_scores:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise SystemExit(
                "Install requirements-semantic.txt for semantic filtering"
            ) from error
        encoder = SentenceTransformer(
            args.semantic_model,
            revision=args.semantic_model_revision,
            device=args.device,
        )
    manifest = finalize_dataset(
        args.input_dir,
        args.output_dir,
        config,
        encoder=encoder,
        overwrite=args.overwrite,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
