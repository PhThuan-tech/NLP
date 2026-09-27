"""Prepare document-level legal English-Vietnamese data for MT training.

The pipeline deliberately splits at document level before segmentation. It uses
only deterministic, local operations and never mutates the original CSV files.
Alignment is heuristic: every generated pair carries quality scores, and weak
pairs are written to a rejection file for inspection instead of being silently
used for training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import numpy as np
import pandas as pd
from sklearn import __version__ as sklearn_version
from sklearn.model_selection import train_test_split


EXPECTED_COLUMNS = [
    "sample_id",
    "category",
    "english_path",
    "vietnamese_path",
    "english_markdown",
    "vietnamese_markdown",
]

SEPARATOR_RE = re.compile(r"^[\s\-–—_=*]{3,}$")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
WORD_RE = re.compile(r"\S+")
TERMINAL_RE = re.compile(r"[.;:!?](?:[\"')\]]+)?$")

STRUCTURE_PATTERNS = {
    "article": re.compile(r"^(?:article|điều)\s+([0-9]+[a-zđ]?)\b", re.IGNORECASE),
    "chapter": re.compile(r"^(?:chapter|chương)\s+([ivxlcdm0-9]+)\b", re.IGNORECASE),
    "section": re.compile(r"^(?:section|mục)\s+([ivxlcdm0-9]+)\b", re.IGNORECASE),
    "part": re.compile(r"^(?:part|phần)\s+([ivxlcdm0-9]+)\b", re.IGNORECASE),
    "appendix": re.compile(r"^(?:appendix|annex|phụ\s+lục)\s*([ivxlcdm0-9]*)\b", re.IGNORECASE),
}

LIST_MARKER_RE = re.compile(
    r"^(?:\(?\d+[.)]|\(?[a-zđ][.)]|[-•])\s+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PreparationConfig:
    """Configuration recorded in the output manifest."""

    seed: int = 67
    dev_ratio: float = 0.10
    expected_en_vi_char_ratio: float = 1.12
    minimum_alignment_score: float = 0.75
    maximum_block_words: int = 550
    maximum_chunk_words: int = 400
    lookahead_weight: float = 0.20

    def validate(self) -> None:
        if not 0 < self.dev_ratio < 1:
            raise ValueError("dev_ratio must be between 0 and 1")
        if not 0 <= self.minimum_alignment_score <= 1:
            raise ValueError("minimum_alignment_score must be between 0 and 1")
        if self.maximum_block_words < 16:
            raise ValueError("maximum_block_words is unexpectedly small")
        if self.maximum_chunk_words < 16:
            raise ValueError("maximum_chunk_words is unexpectedly small")


@dataclass(frozen=True)
class TextBlock:
    index: int
    text: str
    kind: str
    anchor: str | None
    word_count: int


@dataclass(frozen=True)
class Alignment:
    en_start: int
    en_end: int
    vi_start: int
    vi_end: int
    english: str
    vietnamese: str
    score: float
    length_score: float
    number_score: float
    structure_score: float
    operation: str
    accepted: bool
    rejection_reason: str | None


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def normalize_text(text: str) -> str:
    """Apply safe, reversible-enough normalization for training and hashing."""

    value = unicodedata.normalize("NFC", str(text))
    value = value.replace("\ufeff", "").replace("\u200b", "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[\t ]+$", "", line) for line in value.split("\n")]

    normalized_lines: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        normalized_lines.append("" if blank else line)
        previous_blank = blank
    return "\n".join(normalized_lines).strip()


def normalized_hash(text: str) -> str:
    canonical = re.sub(r"\s+", " ", normalize_text(text)).strip()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_parallel_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        encoding="utf-8",
        keep_default_na=False,
        low_memory=False,
    )
    missing = sorted(set(EXPECTED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    frame = frame[EXPECTED_COLUMNS].copy()
    for column in EXPECTED_COLUMNS:
        frame[column] = frame[column].astype(str)
    empty_rows = frame[EXPECTED_COLUMNS].apply(
        lambda column: column.str.strip().eq("")
    ).any(axis=1)
    if empty_rows.any():
        bad_ids = frame.loc[empty_rows, "sample_id"].tolist()[:10]
        raise ValueError(f"Empty required fields found in samples: {bad_ids}")
    return frame


def add_hashes(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["english_hash"] = result["english_markdown"].map(normalized_hash)
    result["vietnamese_hash"] = result["vietnamese_markdown"].map(normalized_hash)
    result["parallel_hash"] = result.apply(
        lambda row: hashlib.sha256(
            f"{row['english_hash']}:{row['vietnamese_hash']}".encode("ascii")
        ).hexdigest(),
        axis=1,
    )
    return result


def deduplicate_parallel_documents(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep one representative of every exact normalized parallel pair."""

    with_hashes = add_hashes(frame)
    duplicate_mask = with_hashes.duplicated("parallel_hash", keep="first")
    duplicates = with_hashes.loc[
        duplicate_mask,
        ["sample_id", "category", "parallel_hash"],
    ].copy()
    representatives = (
        with_hashes.loc[~duplicate_mask]
        .sort_values("sample_id")
        .reset_index(drop=True)
    )
    first_id_by_hash = (
        with_hashes.loc[~duplicate_mask]
        .set_index("parallel_hash")["sample_id"]
        .to_dict()
    )
    if not duplicates.empty:
        duplicates["kept_sample_id"] = duplicates["parallel_hash"].map(first_id_by_hash)
    else:
        duplicates["kept_sample_id"] = pd.Series(dtype="object")
    return representatives, duplicates


def assign_duplicate_groups(frame: pd.DataFrame) -> pd.Series:
    """Group records sharing either source or target to keep them in one split."""

    union_find = UnionFind(len(frame))
    seen_english: dict[str, int] = {}
    seen_vietnamese: dict[str, int] = {}
    for index, row in frame.iterrows():
        for value, seen in [
            (row["english_hash"], seen_english),
            (row["vietnamese_hash"], seen_vietnamese),
        ]:
            if value in seen:
                union_find.union(index, seen[value])
            else:
                seen[value] = index
    roots = [union_find.find(index) for index in range(len(frame))]
    root_to_group = {
        root: f"group-{position:05d}"
        for position, root in enumerate(sorted(set(roots)))
    }
    return pd.Series([root_to_group[root] for root in roots], index=frame.index)


def stratified_document_split(
    frame: pd.DataFrame,
    config: PreparationConfig,
) -> pd.DataFrame:
    """Split duplicate groups with sklearn and a reproducible random state.

    `train_test_split` operates on groups rather than rows so documents sharing
    either language side can never be assigned to different splits.
    """

    result = frame.copy()
    result["duplicate_group"] = assign_duplicate_groups(result)
    group_table = (
        result.groupby("duplicate_group", as_index=False)
        .agg(
            category=("category", lambda values: Counter(values).most_common(1)[0][0]),
            document_count=("sample_id", "size"),
        )
        .sort_values("duplicate_group")
    )

    category_group_counts = group_table["category"].value_counts()
    too_small = category_group_counts[category_group_counts < 2]
    if not too_small.empty:
        details = ", ".join(
            f"{category}={count}" for category, count in too_small.items()
        )
        raise ValueError(
            "Stratified train/dev split requires at least two duplicate groups "
            f"per category; found {details}"
        )

    group_count = len(group_table)
    category_count = group_table["category"].nunique()
    dev_group_count = math.ceil(group_count * config.dev_ratio)
    train_group_count = group_count - dev_group_count
    if dev_group_count < category_count or train_group_count < category_count:
        raise ValueError(
            "dev_ratio cannot preserve every category in both splits: "
            f"groups={group_count}, categories={category_count}, "
            f"train_groups={train_group_count}, dev_groups={dev_group_count}"
        )

    _, dev_group_table = train_test_split(
        group_table,
        test_size=config.dev_ratio,
        random_state=config.seed,
        shuffle=True,
        stratify=group_table["category"],
    )
    dev_groups = set(dev_group_table["duplicate_group"])

    result["split"] = np.where(
        result["duplicate_group"].isin(dev_groups), "dev", "train"
    )
    return result


def structure_kind(text: str) -> tuple[str, str | None]:
    stripped = text.strip()
    for kind, pattern in STRUCTURE_PATTERNS.items():
        match = pattern.match(stripped)
        if match:
            value = (match.group(1) or "").lower()
            return kind, f"{kind}:{value}"
    if LIST_MARKER_RE.match(stripped):
        return "list_item", None
    letters = [character for character in stripped if character.isalpha()]
    if len(letters) >= 5 and all(character.isupper() for character in letters):
        return "heading", None
    return "paragraph", None


def split_logical_blocks(text: str) -> list[TextBlock]:
    """Join soft-wrapped lines while preserving legal structural boundaries."""

    normalized = normalize_text(text)
    raw_lines = normalized.split("\n")
    assembled: list[tuple[str, str, str | None]] = []
    buffer: list[str] = []
    buffer_kind = "paragraph"
    buffer_anchor: str | None = None

    def flush() -> None:
        nonlocal buffer, buffer_kind, buffer_anchor
        if buffer:
            joined = re.sub(r"[\t ]+", " ", " ".join(buffer)).strip()
            if joined and not SEPARATOR_RE.fullmatch(joined):
                assembled.append((joined, buffer_kind, buffer_anchor))
        buffer = []
        buffer_kind = "paragraph"
        buffer_anchor = None

    for raw_line in raw_lines:
        line = re.sub(r"[\t ]+", " ", raw_line).strip()
        if not line:
            flush()
            continue
        if SEPARATOR_RE.fullmatch(line):
            flush()
            continue

        kind, anchor = structure_kind(line)
        if kind in STRUCTURE_PATTERNS:
            flush()
            assembled.append((line, kind, anchor))
            continue

        if kind == "heading":
            if buffer and buffer_kind != "heading":
                flush()
            buffer_kind = "heading"
            buffer.append(line)
            continue

        if buffer and buffer_kind == "heading":
            flush()

        if kind == "list_item":
            flush()
            buffer_kind = kind
            buffer.append(line)
        else:
            buffer_kind = "paragraph"
            buffer.append(line)

        if TERMINAL_RE.search(line):
            flush()

    flush()
    return [
        TextBlock(
            index=index,
            text=value,
            kind=kind,
            anchor=anchor,
            word_count=len(WORD_RE.findall(value)),
        )
        for index, (value, kind, anchor) in enumerate(assembled)
    ]


def normalized_numbers(text: str) -> set[str]:
    values: set[str] = set()
    for match in NUMBER_RE.findall(text):
        canonical = match.replace(",", ".")
        try:
            numeric = float(canonical)
            values.add(str(int(numeric)) if numeric.is_integer() else f"{numeric:g}")
        except ValueError:
            values.add(canonical)
    return values


def score_alignment(
    english: str,
    vietnamese: str,
    en_kinds: Sequence[str],
    vi_kinds: Sequence[str],
    expected_ratio: float,
) -> tuple[float, float, float, float]:
    observed_ratio = (len(english) + 1) / (len(vietnamese) + 1)
    ratio_error = abs(math.log(max(observed_ratio, 1e-8) / expected_ratio))
    length_score = math.exp(-ratio_error)

    en_numbers = normalized_numbers(english)
    vi_numbers = normalized_numbers(vietnamese)
    if not en_numbers and not vi_numbers:
        number_score = 1.0
    elif not en_numbers or not vi_numbers:
        number_score = 0.0
    else:
        number_score = len(en_numbers & vi_numbers) / len(en_numbers | vi_numbers)

    en_structures = {kind for kind in en_kinds if kind not in {"paragraph", "heading"}}
    vi_structures = {kind for kind in vi_kinds if kind not in {"paragraph", "heading"}}
    if en_structures == vi_structures:
        structure_score = 1.0
    elif en_structures and vi_structures and en_structures & vi_structures:
        structure_score = 0.75
    elif not en_structures and not vi_structures:
        structure_score = 1.0
    else:
        structure_score = 0.25

    total = 0.50 * length_score + 0.32 * number_score + 0.18 * structure_score
    return total, length_score, number_score, structure_score


def _candidate_alignment(
    en_blocks: Sequence[TextBlock],
    vi_blocks: Sequence[TextBlock],
    en_start: int,
    vi_start: int,
    en_take: int,
    vi_take: int,
    config: PreparationConfig,
) -> Alignment | None:
    if en_start + en_take > len(en_blocks) or vi_start + vi_take > len(vi_blocks):
        return None
    selected_en = en_blocks[en_start : en_start + en_take]
    selected_vi = vi_blocks[vi_start : vi_start + vi_take]
    english = "\n".join(block.text for block in selected_en)
    vietnamese = "\n".join(block.text for block in selected_vi)
    score, length_score, number_score, structure_score = score_alignment(
        english,
        vietnamese,
        [block.kind for block in selected_en],
        [block.kind for block in selected_vi],
        config.expected_en_vi_char_ratio,
    )
    group_penalty = 0.025 * ((en_take - 1) + (vi_take - 1))
    score = max(0.0, score - group_penalty)
    word_limit_exceeded = (
        sum(block.word_count for block in selected_en) > config.maximum_block_words
        or sum(block.word_count for block in selected_vi) > config.maximum_block_words
    )
    accepted = score >= config.minimum_alignment_score and not word_limit_exceeded
    reason = None
    if word_limit_exceeded:
        reason = "maximum_block_words_exceeded"
    elif score < config.minimum_alignment_score:
        reason = "low_alignment_score"
    return Alignment(
        en_start=en_start,
        en_end=en_start + en_take,
        vi_start=vi_start,
        vi_end=vi_start + vi_take,
        english=english,
        vietnamese=vietnamese,
        score=score,
        length_score=length_score,
        number_score=number_score,
        structure_score=structure_score,
        operation=f"{en_take}-{vi_take}",
        accepted=accepted,
        rejection_reason=reason,
    )


def _unmatched_alignment(
    blocks: Sequence[TextBlock],
    start: int,
    end: int,
    other_index: int,
    language: str,
) -> Alignment:
    text = "\n".join(block.text for block in blocks[start:end])
    if language == "en":
        return Alignment(
            start, end, other_index, other_index, text, "", 0.0, 0.0, 0.0,
            0.0, "unmatched-en", False, "unmatched_english_block",
        )
    return Alignment(
        other_index, other_index, start, end, "", text, 0.0, 0.0, 0.0,
        0.0, "unmatched-vi", False, "unmatched_vietnamese_block",
    )


def _monotonic_anchor_pairs(
    en_blocks: Sequence[TextBlock],
    vi_blocks: Sequence[TextBlock],
) -> list[tuple[int, int]]:
    """Match equal legal anchors without violating document order."""

    vi_positions: dict[str, list[int]] = defaultdict(list)
    for index, block in enumerate(vi_blocks):
        if block.anchor:
            vi_positions[block.anchor].append(index)

    pairs: list[tuple[int, int]] = []
    last_vi = -1
    for en_index, block in enumerate(en_blocks):
        if not block.anchor:
            continue
        candidates = [
            position
            for position in vi_positions.get(block.anchor, [])
            if position > last_vi
        ]
        if candidates:
            vi_index = candidates[0]
            pairs.append((en_index, vi_index))
            last_vi = vi_index
    return pairs


def _align_region_dp(
    en_blocks: Sequence[TextBlock],
    vi_blocks: Sequence[TextBlock],
    en_offset: int,
    vi_offset: int,
    config: PreparationConfig,
) -> list[Alignment]:
    """Banded Gale-Church-style DP for a region between reliable anchors."""

    en_count = len(en_blocks)
    vi_count = len(vi_blocks)
    if not en_count:
        return [
            Alignment(
                en_offset,
                en_offset,
                vi_offset + index,
                vi_offset + index + 1,
                "",
                vi_blocks[index].text,
                0.0,
                0.0,
                0.0,
                0.0,
                "unmatched-vi",
                False,
                "unmatched_vietnamese_block",
            )
            for index in range(vi_count)
        ]
    if not vi_count:
        return [
            Alignment(
                en_offset + index,
                en_offset + index + 1,
                vi_offset,
                vi_offset,
                en_blocks[index].text,
                "",
                0.0,
                0.0,
                0.0,
                0.0,
                "unmatched-en",
                False,
                "unmatched_english_block",
            )
            for index in range(en_count)
        ]

    # Exact DP is most useful inside articles, where regions are small. Large
    # annexes may contain thousands of unanchored rows; a bounded-lookahead
    # linear aligner keeps preprocessing time predictable for those regions.
    if en_count * vi_count > 400 or max(en_count, vi_count) > 24:
        return _align_region_linear(
            en_blocks, vi_blocks, en_offset, vi_offset, config
        )

    moves = [(1, 1), (1, 2), (2, 1), (2, 2)]
    skip_cost = 0.43
    # The band follows the proportional diagonal, so it does not need to grow
    # with the absolute EN/VI block-count difference. Capping it prevents large
    # appendices without anchors from turning preparation into quadratic work.
    band = max(16, min(64, int(math.sqrt(max(en_count, vi_count))) * 2))
    costs: dict[tuple[int, int], float] = {(0, 0): 0.0}
    back: dict[tuple[int, int], tuple[int, int, Alignment]] = {}

    for en_index in range(en_count + 1):
        expected_vi = round(en_index * vi_count / en_count)
        vi_lower = max(0, expected_vi - band)
        vi_upper = min(vi_count, expected_vi + band)
        for vi_index in range(vi_lower, vi_upper + 1):
            current = costs.get((en_index, vi_index))
            if current is None:
                continue

            def relax(
                next_en: int,
                next_vi: int,
                transition_cost: float,
                alignment: Alignment,
            ) -> None:
                candidate_cost = current + transition_cost
                state = (next_en, next_vi)
                if candidate_cost < costs.get(state, math.inf):
                    costs[state] = candidate_cost
                    back[state] = (en_index, vi_index, alignment)

            if en_index < en_count:
                unmatched = _unmatched_alignment(
                    en_blocks, en_index, en_index + 1, vi_offset + vi_index, "en"
                )
                unmatched = Alignment(
                    unmatched.en_start + en_offset,
                    unmatched.en_end + en_offset,
                    unmatched.vi_start,
                    unmatched.vi_end,
                    unmatched.english,
                    unmatched.vietnamese,
                    unmatched.score,
                    unmatched.length_score,
                    unmatched.number_score,
                    unmatched.structure_score,
                    unmatched.operation,
                    unmatched.accepted,
                    unmatched.rejection_reason,
                )
                relax(en_index + 1, vi_index, skip_cost, unmatched)

            if vi_index < vi_count:
                unmatched = _unmatched_alignment(
                    vi_blocks, vi_index, vi_index + 1, en_offset + en_index, "vi"
                )
                unmatched = Alignment(
                    unmatched.en_start,
                    unmatched.en_end,
                    unmatched.vi_start + vi_offset,
                    unmatched.vi_end + vi_offset,
                    unmatched.english,
                    unmatched.vietnamese,
                    unmatched.score,
                    unmatched.length_score,
                    unmatched.number_score,
                    unmatched.structure_score,
                    unmatched.operation,
                    unmatched.accepted,
                    unmatched.rejection_reason,
                )
                relax(en_index, vi_index + 1, skip_cost, unmatched)

            for en_take, vi_take in moves:
                local = _candidate_alignment(
                    en_blocks,
                    vi_blocks,
                    en_index,
                    vi_index,
                    en_take,
                    vi_take,
                    config,
                )
                if local is None:
                    continue
                global_alignment = Alignment(
                    local.en_start + en_offset,
                    local.en_end + en_offset,
                    local.vi_start + vi_offset,
                    local.vi_end + vi_offset,
                    local.english,
                    local.vietnamese,
                    local.score,
                    local.length_score,
                    local.number_score,
                    local.structure_score,
                    local.operation,
                    local.accepted,
                    local.rejection_reason,
                )
                transition_cost = 1.0 - local.score
                relax(
                    en_index + en_take,
                    vi_index + vi_take,
                    transition_cost,
                    global_alignment,
                )

    end_state = (en_count, vi_count)
    if end_state not in costs:
        # This is only expected for extremely imbalanced regions outside the band.
        return [
            Alignment(
                en_offset, en_offset + en_count, vi_offset, vi_offset,
                "\n".join(block.text for block in en_blocks), "", 0.0, 0.0,
                0.0, 0.0, "unmatched-en", False,
                "alignment_region_outside_band",
            ),
            Alignment(
                en_offset, en_offset, vi_offset, vi_offset + vi_count, "",
                "\n".join(block.text for block in vi_blocks), 0.0, 0.0, 0.0,
                0.0, "unmatched-vi", False,
                "alignment_region_outside_band",
            ),
        ]

    reversed_path: list[Alignment] = []
    state = end_state
    while state != (0, 0):
        previous_en, previous_vi, alignment = back[state]
        reversed_path.append(alignment)
        state = (previous_en, previous_vi)
    return list(reversed(reversed_path))


def _align_region_linear(
    en_blocks: Sequence[TextBlock],
    vi_blocks: Sequence[TextBlock],
    en_offset: int,
    vi_offset: int,
    config: PreparationConfig,
) -> list[Alignment]:
    """Linear fallback with local lookahead, grouping and explicit skip moves."""

    result: list[Alignment] = []
    en_index = 0
    vi_index = 0
    moves = [(1, 1), (1, 2), (2, 1), (2, 2)]

    def to_global(local: Alignment) -> Alignment:
        return Alignment(
            local.en_start + en_offset,
            local.en_end + en_offset,
            local.vi_start + vi_offset,
            local.vi_end + vi_offset,
            local.english,
            local.vietnamese,
            local.score,
            local.length_score,
            local.number_score,
            local.structure_score,
            local.operation,
            local.accepted,
            local.rejection_reason,
        )

    while en_index < len(en_blocks) and vi_index < len(vi_blocks):
        ranked: list[tuple[float, Alignment]] = []
        for en_take, vi_take in moves:
            candidate = _candidate_alignment(
                en_blocks,
                vi_blocks,
                en_index,
                vi_index,
                en_take,
                vi_take,
                config,
            )
            if candidate is None:
                continue
            next_en = en_index + en_take
            next_vi = vi_index + vi_take
            lookahead = 0.5
            if next_en < len(en_blocks) and next_vi < len(vi_blocks):
                next_candidate = _candidate_alignment(
                    en_blocks, vi_blocks, next_en, next_vi, 1, 1, config
                )
                if next_candidate is not None:
                    lookahead = next_candidate.score
            ranked.append(
                (candidate.score + config.lookahead_weight * lookahead, candidate)
            )
        chosen = max(ranked, key=lambda item: item[0])[1]

        # If the current match is weak, test whether skipping one block gives a
        # substantially better 1-1 continuation. The skipped block is audited.
        if chosen.score < config.minimum_alignment_score:
            skip_en_score = -1.0
            skip_vi_score = -1.0
            if en_index + 1 < len(en_blocks):
                probe = _candidate_alignment(
                    en_blocks, vi_blocks, en_index + 1, vi_index, 1, 1, config
                )
                if probe is not None:
                    skip_en_score = probe.score
            if vi_index + 1 < len(vi_blocks):
                probe = _candidate_alignment(
                    en_blocks, vi_blocks, en_index, vi_index + 1, 1, 1, config
                )
                if probe is not None:
                    skip_vi_score = probe.score
            improvement_required = 0.12
            if skip_en_score > chosen.score + improvement_required and skip_en_score >= skip_vi_score:
                local = _unmatched_alignment(
                    en_blocks, en_index, en_index + 1, vi_index, "en"
                )
                result.append(to_global(local))
                en_index += 1
                continue
            if skip_vi_score > chosen.score + improvement_required:
                local = _unmatched_alignment(
                    vi_blocks, vi_index, vi_index + 1, en_index, "vi"
                )
                result.append(to_global(local))
                vi_index += 1
                continue

        result.append(to_global(chosen))
        en_index = chosen.en_end
        vi_index = chosen.vi_end

    while en_index < len(en_blocks):
        local = _unmatched_alignment(
            en_blocks, en_index, en_index + 1, vi_index, "en"
        )
        result.append(to_global(local))
        en_index += 1
    while vi_index < len(vi_blocks):
        local = _unmatched_alignment(
            vi_blocks, vi_index, vi_index + 1, en_index, "vi"
        )
        result.append(to_global(local))
        vi_index += 1
    return result


def align_blocks(
    en_blocks: Sequence[TextBlock],
    vi_blocks: Sequence[TextBlock],
    config: PreparationConfig,
) -> list[Alignment]:
    """Align blocks with hard legal anchors and DP inside anchor regions."""

    alignments: list[Alignment] = []
    anchor_pairs = _monotonic_anchor_pairs(en_blocks, vi_blocks)
    previous_en = 0
    previous_vi = 0

    for en_anchor, vi_anchor in anchor_pairs:
        alignments.extend(
            _align_region_dp(
                en_blocks[previous_en:en_anchor],
                vi_blocks[previous_vi:vi_anchor],
                previous_en,
                previous_vi,
                config,
            )
        )
        anchor_alignment = _candidate_alignment(
            en_blocks, vi_blocks, en_anchor, vi_anchor, 1, 1, config
        )
        assert anchor_alignment is not None
        alignments.append(anchor_alignment)
        previous_en = en_anchor + 1
        previous_vi = vi_anchor + 1

    alignments.extend(
        _align_region_dp(
            en_blocks[previous_en:],
            vi_blocks[previous_vi:],
            previous_en,
            previous_vi,
            config,
        )
    )
    return alignments


def pack_alignments(
    alignments: Sequence[Alignment],
    maximum_words: int,
) -> Iterator[dict[str, object]]:
    """Pack adjacent accepted blocks without crossing a rejected alignment."""

    buffer: list[Alignment] = []
    en_words = 0
    vi_words = 0

    def emit() -> dict[str, object] | None:
        nonlocal buffer, en_words, vi_words
        if not buffer:
            return None
        result = {
            "english": "\n\n".join(item.english for item in buffer),
            "vietnamese": "\n\n".join(item.vietnamese for item in buffer),
            "alignment_score_mean": float(np.mean([item.score for item in buffer])),
            "alignment_score_min": float(min(item.score for item in buffer)),
            "en_block_start": buffer[0].en_start,
            "en_block_end": buffer[-1].en_end,
            "vi_block_start": buffer[0].vi_start,
            "vi_block_end": buffer[-1].vi_end,
            "alignment_operations": [item.operation for item in buffer],
        }
        buffer = []
        en_words = 0
        vi_words = 0
        return result

    for alignment in alignments:
        if not alignment.accepted:
            pending = emit()
            if pending is not None:
                yield pending
            continue
        current_en_words = len(WORD_RE.findall(alignment.english))
        current_vi_words = len(WORD_RE.findall(alignment.vietnamese))
        would_overflow = buffer and (
            en_words + current_en_words > maximum_words
            or vi_words + current_vi_words > maximum_words
        )
        if would_overflow:
            pending = emit()
            if pending is not None:
                yield pending
        buffer.append(alignment)
        en_words += current_en_words
        vi_words += current_vi_words

    pending = emit()
    if pending is not None:
        yield pending


def document_record(row: pd.Series) -> dict[str, object]:
    return {
        "sample_id": row["sample_id"],
        "category": row["category"],
        "english_path": row["english_path"],
        "vietnamese_path": row["vietnamese_path"],
        "english_markdown": normalize_text(row["english_markdown"]),
        "vietnamese_markdown": normalize_text(row["vietnamese_markdown"]),
        "english_hash": row["english_hash"],
        "vietnamese_hash": row["vietnamese_hash"],
        "duplicate_group": row.get("duplicate_group"),
    }


def segment_document(
    row: pd.Series,
    config: PreparationConfig,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    en_blocks = split_logical_blocks(row["english_markdown"])
    vi_blocks = split_logical_blocks(row["vietnamese_markdown"])
    alignments = align_blocks(en_blocks, vi_blocks, config)
    packed = list(pack_alignments(alignments, config.maximum_chunk_words))
    records: list[dict[str, object]] = []
    for chunk_index, item in enumerate(packed):
        common = {
            "segment_id": f"{row['sample_id']}::segment-{chunk_index:04d}",
            "sample_id": row["sample_id"],
            "category": row["category"],
            "chunk_index": chunk_index,
            **item,
        }
        records.append(common)

    rejected = []
    for alignment_index, alignment in enumerate(alignments):
        if alignment.accepted:
            continue
        rejected.append(
            {
                "sample_id": row["sample_id"],
                "category": row["category"],
                "alignment_index": alignment_index,
                **asdict(alignment),
            }
        )

    accepted_alignments = [item for item in alignments if item.accepted]
    stats = {
        "sample_id": row["sample_id"],
        "category": row["category"],
        "en_blocks": len(en_blocks),
        "vi_blocks": len(vi_blocks),
        "alignments": len(alignments),
        "accepted_alignments": len(accepted_alignments),
        "rejected_alignments": len(alignments) - len(accepted_alignments),
        "segments": len(records),
        "mean_accepted_score": (
            float(np.mean([item.score for item in accepted_alignments]))
            if accepted_alignments
            else 0.0
        ),
    }
    return records, rejected, stats


def directional_record(record: dict[str, object], direction: str) -> dict[str, object]:
    if direction == "en2vi":
        source, target = record["english"], record["vietnamese"]
        source_lang, target_lang = "en", "vi"
    elif direction == "vi2en":
        source, target = record["vietnamese"], record["english"]
        source_lang, target_lang = "vi", "en"
    else:
        raise ValueError(f"Unsupported direction: {direction}")
    return {
        "segment_id": f"{record['segment_id']}::{direction}",
        "sample_id": record["sample_id"],
        "category": record["category"],
        "chunk_index": record["chunk_index"],
        "direction": direction,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "source": source,
        "target": target,
        "alignment_score_mean": record["alignment_score_mean"],
        "alignment_score_min": record["alignment_score_min"],
        "source_word_count": len(WORD_RE.findall(str(source))),
        "target_word_count": len(WORD_RE.findall(str(target))),
        "en_block_start": record["en_block_start"],
        "en_block_end": record["en_block_end"],
        "vi_block_start": record["vi_block_start"],
        "vi_block_end": record["vi_block_end"],
    }


def write_jsonl(path: Path, records: Iterable[dict[str, object]]) -> int:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    temp_path.replace(path)
    return count


def write_json(path: Path, value: object) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)


def ensure_output_paths(output_dir: Path, overwrite: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    known_outputs = [
        "manifest.json",
        "quality_report.json",
        "document_splits.csv",
        "duplicate_documents.csv",
        "alignment_by_document.csv",
        "alignment_by_category.csv",
        "rejected_alignments.jsonl",
        "documents_train.jsonl",
        "documents_dev.jsonl",
        "documents_public_test.jsonl",
        "segments_train_en2vi.jsonl",
        "segments_train_vi2en.jsonl",
        "segments_dev_en2vi.jsonl",
        "segments_dev_vi2en.jsonl",
        "segments_public_test_en2vi.jsonl",
        "segments_public_test_vi2en.jsonl",
    ]
    existing = [name for name in known_outputs if (output_dir / name).exists()]
    if existing and not overwrite:
        raise FileExistsError(
            f"Output files already exist in {output_dir}: {existing[:5]}. "
            "Use --overwrite to replace known generated files."
        )


def prepare_dataset(
    train_csv: Path,
    public_test_csv: Path,
    output_dir: Path,
    config: PreparationConfig | None = None,
    overwrite: bool = False,
) -> dict[str, object]:
    config = config or PreparationConfig()
    config.validate()
    ensure_output_paths(output_dir, overwrite)

    raw_train = load_parallel_csv(train_csv)
    raw_public_test = load_parallel_csv(public_test_csv)
    train_unique, duplicates = deduplicate_parallel_documents(raw_train)
    split_train = stratified_document_split(train_unique, config)
    public_test = add_hashes(raw_public_test)
    public_test["duplicate_group"] = None
    public_test["split"] = "public_test"

    split_columns = [
        "sample_id",
        "category",
        "split",
        "duplicate_group",
        "english_hash",
        "vietnamese_hash",
    ]
    split_train[split_columns].to_csv(
        output_dir / "document_splits.csv", index=False, encoding="utf-8"
    )
    duplicates.to_csv(
        output_dir / "duplicate_documents.csv", index=False, encoding="utf-8"
    )

    counts: dict[str, int] = {}
    all_rejected: list[dict[str, object]] = []
    all_stats: list[dict[str, object]] = []

    for split_name, frame in [
        ("train", split_train.loc[split_train["split"] == "train"]),
        ("dev", split_train.loc[split_train["split"] == "dev"]),
        ("public_test", public_test),
    ]:
        frame = frame.sort_values("sample_id").reset_index(drop=True)
        counts[f"documents_{split_name}"] = write_jsonl(
            output_dir / f"documents_{split_name}.jsonl",
            (document_record(row) for _, row in frame.iterrows()),
        )

        split_segments: list[dict[str, object]] = []
        for _, row in frame.iterrows():
            records, rejected, stats = segment_document(row, config)
            split_segments.extend(records)
            all_rejected.extend({"split": split_name, **item} for item in rejected)
            all_stats.append({"split": split_name, **stats})

        for direction in ["en2vi", "vi2en"]:
            key = f"segments_{split_name}_{direction}"
            counts[key] = write_jsonl(
                output_dir / f"{key}.jsonl",
                (directional_record(record, direction) for record in split_segments),
            )

    counts["rejected_alignments"] = write_jsonl(
        output_dir / "rejected_alignments.jsonl", all_rejected
    )

    stats_frame = pd.DataFrame(all_stats)
    stats_frame.to_csv(
        output_dir / "alignment_by_document.csv", index=False, encoding="utf-8"
    )
    category_stats = (
        stats_frame.groupby(["split", "category"], as_index=False)
        .agg(
            documents=("sample_id", "size"),
            en_blocks=("en_blocks", "sum"),
            vi_blocks=("vi_blocks", "sum"),
            accepted_alignments=("accepted_alignments", "sum"),
            rejected_alignments=("rejected_alignments", "sum"),
            segments=("segments", "sum"),
            mean_alignment_score=("mean_accepted_score", "mean"),
        )
    )
    category_stats["acceptance_rate"] = (
        category_stats["accepted_alignments"]
        / (
            category_stats["accepted_alignments"]
            + category_stats["rejected_alignments"]
        ).replace(0, np.nan)
    )
    category_stats.to_csv(
        output_dir / "alignment_by_category.csv", index=False, encoding="utf-8"
    )

    public_en_overlap = int(
        public_test["english_hash"].isin(set(split_train["english_hash"])).sum()
    )
    public_vi_overlap = int(
        public_test["vietnamese_hash"].isin(set(split_train["vietnamese_hash"])).sum()
    )
    split_category_counts = (
        split_train.groupby(["split", "category"])
        .size()
        .unstack(fill_value=0)
        .to_dict(orient="index")
    )
    quality_report = {
        "raw_train_documents": len(raw_train),
        "unique_train_documents": len(train_unique),
        "removed_exact_parallel_duplicates": len(duplicates),
        "raw_public_test_documents": len(raw_public_test),
        "public_test_exact_english_overlap_with_train": public_en_overlap,
        "public_test_exact_vietnamese_overlap_with_train": public_vi_overlap,
        "split_category_counts": split_category_counts,
        "counts": counts,
        "alignment_score_summary": stats_frame.groupby("split")[
            "mean_accepted_score"
        ].describe().to_dict(orient="index"),
    }
    write_json(output_dir / "quality_report.json", quality_report)

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "sklearn_version": sklearn_version,
        "train_csv": str(train_csv.resolve()),
        "public_test_csv": str(public_test_csv.resolve()),
        "output_dir": str(output_dir.resolve()),
        "config": asdict(config),
        "counts": counts,
        "notes": [
            "Split uses sklearn train_test_split with stratify=category and random_state=seed at duplicate-group level before segmentation.",
            "Alignment is heuristic; inspect rejection and alignment reports before training.",
            "Word counts are whitespace approximations, not pretrained-model token counts.",
        ],
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--train-csv", type=Path)
    parser.add_argument("--public-test-csv", type=Path)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("artifacts/processed")
    )
    parser.add_argument("--seed", type=int, default=67)
    parser.add_argument("--dev-ratio", type=float, default=0.10)
    parser.add_argument("--minimum-alignment-score", type=float, default=0.75)
    parser.add_argument("--maximum-block-words", type=int, default=550)
    parser.add_argument("--maximum-chunk-words", type=int, default=400)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    project_root = args.project_root.resolve()
    train_csv = args.train_csv or project_root / "data/train/en-vi-train.csv"
    public_test_csv = (
        args.public_test_csv
        or project_root / "data/test/en-vi-public_test.csv"
    )
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    config = PreparationConfig(
        seed=args.seed,
        dev_ratio=args.dev_ratio,
        minimum_alignment_score=args.minimum_alignment_score,
        maximum_block_words=args.maximum_block_words,
        maximum_chunk_words=args.maximum_chunk_words,
    )
    manifest = prepare_dataset(
        train_csv=train_csv,
        public_test_csv=public_test_csv,
        output_dir=output_dir,
        config=config,
        overwrite=args.overwrite,
    )
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))
    print(f"Prepared data written to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
