"""Shared MT and legal-preservation metrics for every VinAI experiment."""

from __future__ import annotations

import re
from collections import Counter
from statistics import mean
from typing import Any, Sequence

import numpy as np


NUMBER_PATTERN = re.compile(
    r"(?<!\w)(?:\d{1,4}(?:[./,-]\d{1,4})+|\d+(?:[.,]\d+)?%?)(?!\w)"
)
REFERENCE_PATTERN = re.compile(
    r"(?i)\b(article|điều|clause|khoản|point|điểm|chapter|chương|section|mục)\s+"
    r"([a-zđ]|\d+[a-zđ]?|[ivxlcdm]+)\b"
)
REFERENCE_KIND = {
    "article": "article",
    "điều": "article",
    "clause": "clause",
    "khoản": "clause",
    "point": "point",
    "điểm": "point",
    "chapter": "chapter",
    "chương": "chapter",
    "section": "section",
    "mục": "section",
}


def extract_numbers(text: str) -> Counter[str]:
    return Counter(match.group(0).replace(" ", "") for match in NUMBER_PATTERN.finditer(text))


def extract_references(text: str) -> Counter[str]:
    values = []
    for match in REFERENCE_PATTERN.finditer(text):
        kind = REFERENCE_KIND[match.group(1).lower()]
        values.append(f"{kind}:{match.group(2).lower()}")
    return Counter(values)


def preservation_metrics(
    predictions: Sequence[str], references: Sequence[str], extractor: Any, prefix: str
) -> dict[str, float]:
    expected_total = 0
    actual_total = 0
    matched_total = 0
    exact: list[float] = []
    for prediction, reference in zip(predictions, references, strict=True):
        expected = extractor(reference)
        actual = extractor(prediction)
        expected_total += sum(expected.values())
        actual_total += sum(actual.values())
        matched_total += sum((expected & actual).values())
        exact.append(float(expected == actual))
    precision = (
        matched_total / actual_total if actual_total else float(expected_total == 0)
    )
    recall = (
        matched_total / expected_total if expected_total else float(actual_total == 0)
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        f"{prefix}_precision": 100 * precision,
        f"{prefix}_recall": 100 * recall,
        f"{prefix}_f1": 100 * f1,
        f"{prefix}_exact_rate": 100 * mean(exact),
    }


class TranslationMetricSuite:
    """Decode trainer outputs and compute reproducible corpus/legal metrics."""

    def __init__(self, tokenizer: Any) -> None:
        self.tokenizer = tokenizer

    def decode_predictions(self, predictions: Any) -> list[str]:
        if isinstance(predictions, tuple):
            predictions = predictions[0]
        predictions = np.asarray(predictions).copy()
        predictions[predictions == -100] = self.tokenizer.pad_token_id
        return [
            value.strip()
            for value in self.tokenizer.batch_decode(
                predictions, skip_special_tokens=True
            )
        ]

    def decode_labels(self, labels: Any) -> list[str]:
        labels = np.asarray(labels).copy()
        labels[labels == -100] = self.tokenizer.pad_token_id
        return [
            value.strip()
            for value in self.tokenizer.batch_decode(labels, skip_special_tokens=True)
        ]

    def score_texts(
        self, predictions: Sequence[str], references: Sequence[str]
    ) -> dict[str, float]:
        if len(predictions) != len(references):
            raise ValueError("Predictions and references must have equal length")
        if not predictions:
            raise ValueError("Cannot score an empty prediction list")
        try:
            import sacrebleu
        except ImportError as error:
            raise RuntimeError(
                "sacrebleu is required; install requirements-training.txt"
            ) from error

        bleu = sacrebleu.corpus_bleu(list(predictions), [list(references)])
        chrf = sacrebleu.corpus_chrf(
            list(predictions), [list(references)], word_order=2
        )
        reference_lengths = [max(1, len(text.split())) for text in references]
        length_ratios = [
            len(prediction.split()) / reference_length
            for prediction, reference_length in zip(
                predictions, reference_lengths, strict=True
            )
        ]
        metrics: dict[str, float] = {
            "bleu": float(bleu.score),
            "chrf": float(chrf.score),
            "empty_output_rate": 100
            * sum(not prediction.strip() for prediction in predictions)
            / len(predictions),
            "length_ratio_mean": float(mean(length_ratios)),
        }
        metrics.update(
            preservation_metrics(
                predictions, references, extract_numbers, "number_preservation"
            )
        )
        metrics.update(
            preservation_metrics(
                predictions, references, extract_references, "reference_preservation"
            )
        )
        return {key: round(value, 6) for key, value in metrics.items()}

    def __call__(self, evaluation_prediction: Any) -> dict[str, float]:
        predictions = self.decode_predictions(evaluation_prediction.predictions)
        references = self.decode_labels(evaluation_prediction.label_ids)
        return self.score_texts(predictions, references)
