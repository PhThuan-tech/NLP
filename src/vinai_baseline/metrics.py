"""Shared MT and legal-preservation metrics for every VinAI experiment."""

from __future__ import annotations

import re
from collections import Counter
from statistics import mean
from typing import Any, Sequence

import numpy as np


NUMBER_PATTERN = re.compile(
    r"(?<!\w)(?:\d{1,3}(?:[ \u00a0]\d{3})+|"
    r"\d{1,4}(?:[./,-]\d{1,4})+|\d+(?:[.,]\d+)?%?)(?!\w)"
)
REFERENCE_PATTERN = re.compile(
    r"(?i)\b(article|điều|clause|khoản|point|điểm|chapter|chương|section|mục)\s+"
    r"([a-zđ]|\d+[a-zđ]?|[ivxlcdm]+)\b"
)
LEGAL_IDENTIFIER_PATTERN = re.compile(
    r"(?i)(?<!\w)\d{1,4}\s*/\s*\d{4}\s*/\s*[a-zđ0-9]+"
    r"(?:\s*[-–]\s*[a-zđ0-9]+)*(?!\w)"
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


def canonicalize_number(value: str) -> str:
    """Normalize common EN/VI legal number formatting without guessing decimals."""

    compact = re.sub(r"[ \u00a0]+", "", value)
    suffix = "%" if compact.endswith("%") else ""
    core = compact.removesuffix("%")
    if re.fullmatch(r"\d{1,4}(?:/\d{1,4})+", core):
        return f"date:{core}{suffix}"
    if re.fullmatch(r"\d{1,4}(?:-\d{1,4})+", core):
        return f"range:{core}{suffix}"
    # Comma/dot groups of exactly three digits are thousands separators in the
    # legal corpus (10,000,000 and 10.000.000 must compare equal).
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", core):
        core = re.sub(r"[.,]", "", core)
    elif core.count(",") + core.count(".") == 1:
        core = core.replace(",", ".")
        try:
            numeric = float(core)
            core = str(int(numeric)) if numeric.is_integer() else f"{numeric:g}"
        except ValueError:
            pass
    return f"{core}{suffix}"


def extract_numbers(text: str) -> Counter[str]:
    return Counter(
        canonicalize_number(match.group(0)) for match in NUMBER_PATTERN.finditer(text)
    )


def extract_references(text: str) -> Counter[str]:
    values = []
    for match in REFERENCE_PATTERN.finditer(text):
        kind = REFERENCE_KIND[match.group(1).lower()]
        values.append(f"{kind}:{match.group(2).lower()}")
    return Counter(values)


def extract_legal_identifiers(text: str) -> Counter[str]:
    return Counter(
        re.sub(r"\s+", "", match.group(0)).replace("–", "-").upper()
        for match in LEGAL_IDENTIFIER_PATTERN.finditer(text)
    )


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
        dominant_token_rates = [
            self._dominant_token_rate(prediction) for prediction in predictions
        ]
        metrics: dict[str, float] = {
            "bleu": float(bleu.score),
            "chrf": float(chrf.score),
            "empty_output_rate": 100
            * sum(not prediction.strip() for prediction in predictions)
            / len(predictions),
            "length_ratio_mean": float(mean(length_ratios)),
            "length_ratio_p50": float(np.quantile(length_ratios, 0.50)),
            "length_ratio_p95": float(np.quantile(length_ratios, 0.95)),
            "length_ratio_p99": float(np.quantile(length_ratios, 0.99)),
            "length_ratio_over_2_rate": 100
            * sum(value > 2 for value in length_ratios)
            / len(length_ratios),
            "length_ratio_over_3_rate": 100
            * sum(value > 3 for value in length_ratios)
            / len(length_ratios),
            "length_ratio_over_5_rate": 100
            * sum(value > 5 for value in length_ratios)
            / len(length_ratios),
            "repeated_trigram_rate": 100
            * sum(self._has_repeated_ngram(text, 3) for text in predictions)
            / len(predictions),
            "dominant_token_rate_p95": float(
                np.quantile(dominant_token_rates, 0.95)
            ),
            "dominant_token_over_20_rate": 100
            * sum(value > 20 for value in dominant_token_rates)
            / len(dominant_token_rates),
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
        metrics.update(
            preservation_metrics(
                predictions,
                references,
                extract_legal_identifiers,
                "legal_identifier_preservation",
            )
        )
        return {key: round(value, 6) for key, value in metrics.items()}

    @staticmethod
    def _has_repeated_ngram(text: str, size: int) -> bool:
        tokens = text.casefold().split()
        if len(tokens) < size:
            return False
        ngrams = [tuple(tokens[index : index + size]) for index in range(len(tokens) - size + 1)]
        return len(ngrams) != len(set(ngrams))

    @staticmethod
    def _dominant_token_rate(text: str) -> float:
        tokens = text.casefold().split()
        # A 1--4 word translation naturally gives each unique token >20%; that
        # is not degeneration. Apply this signal only to outputs long enough
        # for token dominance to be meaningful.
        if len(tokens) < 20:
            return 0.0
        return 100 * max(Counter(tokens).values()) / len(tokens)

    def score_source_preservation(
        self, predictions: Sequence[str], sources: Sequence[str]
    ) -> dict[str, float]:
        """Measure facts copied from the source separately from reference overlap."""

        metrics = {}
        metrics.update(
            preservation_metrics(
                predictions, sources, extract_numbers, "source_number_preservation"
            )
        )
        metrics.update(
            preservation_metrics(
                predictions,
                sources,
                extract_references,
                "source_reference_preservation",
            )
        )
        metrics.update(
            preservation_metrics(
                predictions,
                sources,
                extract_legal_identifiers,
                "source_legal_identifier_preservation",
            )
        )
        return {key: round(value, 6) for key, value in metrics.items()}

    def __call__(self, evaluation_prediction: Any) -> dict[str, float]:
        predictions = self.decode_predictions(evaluation_prediction.predictions)
        references = self.decode_labels(evaluation_prediction.label_ids)
        return self.score_texts(predictions, references)
