import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.vinai_baseline.config import ExperimentConfig
from src.vinai_baseline.data import (
    JsonlCorpus,
    TokenizerAuditor,
    TranslationRecord,
    write_json,
)
from src.vinai_baseline.metrics import (
    extract_numbers,
    extract_references,
    preservation_metrics,
)


class FakeTokenizer:
    """Small deterministic tokenizer used without downloading model weights."""

    def __call__(self, texts=None, *, text_target=None, **_kwargs):
        values = text_target if text_target is not None else texts
        return {"input_ids": [[0, *range(len(value.split())), 2] for value in values]}


def record(segment_id: str, source: str, target: str) -> TranslationRecord:
    return TranslationRecord(
        segment_id=segment_id,
        source=source,
        target=target,
        direction="en2vi",
        category="test",
    )


class ConfigTests(unittest.TestCase):
    def test_all_repository_configs_are_valid(self):
        for path in Path("configs/vinai").glob("*.json"):
            with self.subTest(path=path):
                ExperimentConfig.from_json(path)

    def test_repository_configs_reference_current_dataset(self):
        expected_root = Path("artifacts/processed_sklearn_seed67")
        for path in Path("configs/vinai").glob("*.json"):
            with self.subTest(path=path):
                config = ExperimentConfig.from_json(path)
                data_files = [Path(config.data.validation_file)]
                if config.data.train_file:
                    data_files.append(Path(config.data.train_file))
                for data_file in data_files:
                    self.assertEqual(data_file.parent, expected_root)
                    self.assertTrue(data_file.is_file(), data_file)

    def test_public_test_cannot_be_training_data(self):
        raw = json.loads(Path("configs/vinai/en2vi_lora.json").read_text("utf-8"))
        raw["data"]["train_file"] = "segments_public_test_en2vi.jsonl"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Public test"):
                ExperimentConfig.from_json(path)


class CorpusTests(unittest.TestCase):
    def test_jsonl_schema_and_duplicate_id_validation(self):
        rows = [
            {
                "segment_id": "same",
                "direction": "en2vi",
                "source": "Article 1",
                "target": "Điều 1",
            },
            {
                "segment_id": "same",
                "direction": "en2vi",
                "source": "Article 2",
                "target": "Điều 2",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "segments_train_en2vi.jsonl"
            path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate segment_id"):
                JsonlCorpus(path, direction="en2vi").load()


class TokenAuditTests(unittest.TestCase):
    def test_drop_policy_reports_and_removes_overlength_pair(self):
        values = [
            record("short", "one two", "một hai"),
            record("long", "one two three four five", "một hai"),
        ]
        prepared = TokenizerAuditor(
            FakeTokenizer(),
            max_source_length=5,
            max_target_length=5,
            batch_size=2,
            policy="drop",
        ).prepare(values)
        self.assertEqual([item.segment_id for item in prepared.records], ["short"])
        self.assertEqual(prepared.audit.either_over_limit, 1)
        self.assertEqual(prepared.audit.dropped, 1)

    def test_error_policy_never_truncates_silently(self):
        with self.assertRaisesRegex(ValueError, "exceed token limits"):
            TokenizerAuditor(
                FakeTokenizer(),
                max_source_length=4,
                max_target_length=10,
                batch_size=1,
                policy="error",
            ).prepare([record("long", "one two three", "một")])


class LegalMetricTests(unittest.TestCase):
    def test_vietnamese_legal_references_are_canonicalized(self):
        self.assertEqual(
            extract_references("Điều 15, khoản 2, điểm đ Chương IV"),
            {"article:15": 1, "clause:2": 1, "point:đ": 1, "chapter:iv": 1},
        )

    def test_number_preservation_detects_missing_value(self):
        metrics = preservation_metrics(
            ["Ngày 12/03/2024"],
            ["Ngày 12/03/2024, mức 20%"],
            extract_numbers,
            "number",
        )
        self.assertEqual(metrics["number_precision"], 100.0)
        self.assertEqual(metrics["number_recall"], 50.0)
        self.assertLess(metrics["number_f1"], 100.0)

    def test_numpy_metric_values_can_be_serialized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.json"
            write_json(path, {"score": np.float32(1.25)})
            self.assertEqual(json.loads(path.read_text("utf-8"))["score"], 1.25)


if __name__ == "__main__":
    unittest.main()
