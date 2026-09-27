"""JSONL loading, schema checks, token-length audit, and dynamic collation."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import numpy as np


@dataclass(frozen=True)
class TranslationRecord:
    segment_id: str
    source: str
    target: str
    direction: str
    sample_id: str = ""
    category: str = ""
    semantic_similarity: float | None = None

    @classmethod
    def from_mapping(
        cls,
        row: dict[str, Any],
        *,
        source_field: str,
        target_field: str,
        expected_direction: str,
        line_number: int,
        path: Path,
    ) -> "TranslationRecord":
        missing = [
            key
            for key in ("segment_id", source_field, target_field)
            if key not in row
        ]
        if missing:
            raise ValueError(f"Missing {missing} at {path}:{line_number}")
        direction = str(row.get("direction", expected_direction))
        if direction != expected_direction:
            raise ValueError(
                f"Direction {direction!r} at {path}:{line_number} does not match "
                f"{expected_direction!r}"
            )
        source = str(row[source_field]).strip()
        target = str(row[target_field]).strip()
        if not source or not target:
            raise ValueError(f"Empty source/target at {path}:{line_number}")
        similarity = row.get("semantic_similarity")
        return cls(
            segment_id=str(row["segment_id"]),
            sample_id=str(row.get("sample_id", "")),
            category=str(row.get("category", "")),
            direction=direction,
            source=source,
            target=target,
            semantic_similarity=float(similarity) if similarity is not None else None,
        )

    def to_output_mapping(self, prediction: str) -> dict[str, Any]:
        result = asdict(self)
        result["prediction"] = prediction
        return result


class JsonlCorpus:
    """Load and validate the prepared parallel-segment JSONL format."""

    def __init__(
        self,
        path: str | Path,
        *,
        direction: str,
        source_field: str = "source",
        target_field: str = "target",
        limit: int | None = None,
    ) -> None:
        self.path = Path(path)
        self.direction = direction
        self.source_field = source_field
        self.target_field = target_field
        self.limit = limit

    def load(self) -> list[TranslationRecord]:
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        records: list[TranslationRecord] = []
        seen_ids: set[str] = set()
        with self.path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Invalid JSON at {self.path}:{line_number}"
                    ) from error
                record = TranslationRecord.from_mapping(
                    row,
                    source_field=self.source_field,
                    target_field=self.target_field,
                    expected_direction=self.direction,
                    line_number=line_number,
                    path=self.path,
                )
                if record.segment_id in seen_ids:
                    raise ValueError(
                        f"Duplicate segment_id {record.segment_id!r} in {self.path}"
                    )
                seen_ids.add(record.segment_id)
                records.append(record)
                if self.limit is not None and len(records) >= self.limit:
                    break
        if not records:
            raise ValueError(f"No records found in {self.path}")
        return records


class TranslationDataset:
    """Minimal torch-compatible dataset that keeps untokenized text."""

    def __init__(self, records: Sequence[TranslationRecord]) -> None:
        self.records = list(records)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, str]:
        item = self.records[index]
        return {"source_text": item.source, "target_text": item.target}


@dataclass(frozen=True)
class LengthAudit:
    total: int
    source_quantiles: dict[str, int]
    target_quantiles: dict[str, int]
    source_max: int
    target_max: int
    source_over_limit: int
    target_over_limit: int
    either_over_limit: int
    retained: int
    dropped: int
    category_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PreparedCorpus:
    records: list[TranslationRecord]
    dataset: TranslationDataset
    audit: LengthAudit


def _batches(values: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _quantiles(values: Sequence[int]) -> dict[str, int]:
    if not values:
        return {name: 0 for name in ("p50", "p90", "p95", "p99")}
    ordered = sorted(values)
    result: dict[str, int] = {}
    for label, q in (("p50", 0.50), ("p90", 0.90), ("p95", 0.95), ("p99", 0.99)):
        index = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
        result[label] = int(ordered[index])
    return result


class TokenizerAuditor:
    """Measure exact tokenizer lengths and apply an explicit overflow policy."""

    def __init__(
        self,
        tokenizer: Any,
        *,
        max_source_length: int,
        max_target_length: int,
        batch_size: int,
        policy: str,
    ) -> None:
        self.tokenizer = tokenizer
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length
        self.batch_size = batch_size
        self.policy = policy

    def _lengths(self, texts: Sequence[str], *, target: bool) -> list[int]:
        lengths: list[int] = []
        for batch in _batches(texts, self.batch_size):
            kwargs: dict[str, Any] = {
                "add_special_tokens": True,
                "truncation": False,
                "padding": False,
                "verbose": False,
            }
            if target:
                encoded = self.tokenizer(text_target=list(batch), **kwargs)
            else:
                encoded = self.tokenizer(list(batch), **kwargs)
            lengths.extend(len(ids) for ids in encoded["input_ids"])
        return lengths

    def prepare(self, records: Sequence[TranslationRecord]) -> PreparedCorpus:
        records = list(records)
        source_lengths = self._lengths([r.source for r in records], target=False)
        target_lengths = self._lengths([r.target for r in records], target=True)
        overflow = [
            source_length > self.max_source_length
            or target_length > self.max_target_length
            for source_length, target_length in zip(
                source_lengths, target_lengths, strict=True
            )
        ]
        source_over = sum(x > self.max_source_length for x in source_lengths)
        target_over = sum(x > self.max_target_length for x in target_lengths)
        either_over = sum(overflow)

        if either_over and self.policy == "error":
            examples = [
                records[index].segment_id
                for index, is_over in enumerate(overflow)
                if is_over
            ][:10]
            raise ValueError(
                f"{either_over} records exceed token limits. Examples: {examples}. "
                "Re-segment the data or explicitly choose policy='drop'/'truncate'."
            )
        if self.policy == "drop":
            retained = [r for r, is_over in zip(records, overflow, strict=True) if not is_over]
        else:
            retained = records
        if not retained:
            raise ValueError("No records remain after applying token-length policy")

        audit = LengthAudit(
            total=len(records),
            source_quantiles=_quantiles(source_lengths),
            target_quantiles=_quantiles(target_lengths),
            source_max=max(source_lengths),
            target_max=max(target_lengths),
            source_over_limit=source_over,
            target_over_limit=target_over,
            either_over_limit=either_over,
            retained=len(retained),
            dropped=len(records) - len(retained),
            category_counts=dict(Counter(record.category for record in retained)),
        )
        return PreparedCorpus(
            records=retained,
            dataset=TranslationDataset(retained),
            audit=audit,
        )


class DynamicSeq2SeqCollator:
    """Tokenize and dynamically pad a batch at the last possible moment."""

    def __init__(
        self,
        tokenizer: Any,
        *,
        model: Any,
        max_source_length: int,
        max_target_length: int,
        truncate: bool,
        pad_to_multiple_of: int | None = 8,
    ) -> None:
        self.tokenizer = tokenizer
        self.model = model
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length
        self.truncate = truncate
        self.pad_to_multiple_of = pad_to_multiple_of

    def __call__(self, features: list[dict[str, str]]) -> dict[str, Any]:
        import torch

        sources = [item["source_text"] for item in features]
        targets = [item["target_text"] for item in features]
        source_options: dict[str, Any] = {
            "truncation": self.truncate,
            "padding": True,
            "pad_to_multiple_of": self.pad_to_multiple_of,
            "return_tensors": "pt",
        }
        target_options = dict(source_options)
        if self.truncate:
            source_options["max_length"] = self.max_source_length
            target_options["max_length"] = self.max_target_length
        model_inputs = self.tokenizer(sources, **source_options)
        target_batch = self.tokenizer(text_target=targets, **target_options)
        labels = target_batch["input_ids"]
        labels = labels.masked_fill(labels == self.tokenizer.pad_token_id, -100)
        model_inputs["labels"] = labels.to(dtype=torch.long)
        prepare_decoder_inputs = getattr(
            self.model, "prepare_decoder_input_ids_from_labels", None
        )
        if not callable(prepare_decoder_inputs):
            raise RuntimeError(
                "The seq2seq model cannot create decoder_input_ids from labels"
            )
        model_inputs["decoder_input_ids"] = prepare_decoder_inputs(
            labels=model_inputs["labels"]
        )
        return model_inputs


def write_json(path: str | Path, payload: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, default=_json_default) + "\n"
            )


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """Return a stable dataset fingerprint without loading the whole file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _json_default(value: Any) -> Any:
    """Convert common metric values without silently stringifying objects."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
