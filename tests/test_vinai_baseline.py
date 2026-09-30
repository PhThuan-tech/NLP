import ast
import contextlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from src.vinai_baseline.config import ExperimentConfig
from src.vinai_baseline.compare_runs import comparable_rows
from src.vinai_baseline.create_configs import create_configs
from src.vinai_baseline.data import (
    DynamicSeq2SeqCollator,
    JsonlCorpus,
    TokenizerAuditor,
    TranslationRecord,
    write_json,
)
from src.vinai_baseline.metrics import (
    TranslationMetricSuite,
    canonicalize_number,
    extract_legal_identifiers,
    extract_numbers,
    extract_references,
    preservation_metrics,
)
from src.vinai_baseline.inference import (
    assemble_document,
    markdown_structure_report,
    split_markdown_document,
)
from src.vinai_baseline.runner import BaselineRunner


class FakeTokenizer:
    """Small deterministic tokenizer used without downloading model weights."""

    def __call__(self, texts=None, *, text_target=None, **_kwargs):
        values = text_target if text_target is not None else texts
        return {"input_ids": [[0, *range(len(value.split())), 2] for value in values]}


class FakeTensorTokenizer:
    pad_token_id = 0

    def __init__(self):
        self.calls = []

    def __call__(self, texts=None, *, text_target=None, **kwargs):
        import torch

        self.calls.append(kwargs)
        values = text_target if text_target is not None else texts
        lengths = [len(value.split()) + 2 for value in values]
        width = max(lengths)
        rows = [list(range(1, length + 1)) + [0] * (width - length) for length in lengths]
        return {"input_ids": torch.tensor(rows, dtype=torch.long)}


class FakeSeq2SeqModel:
    def prepare_decoder_input_ids_from_labels(self, labels):
        import torch

        start = torch.full_like(labels[:, :1], 2)
        shifted = labels[:, :-1].masked_fill(labels[:, :-1] == -100, 0)
        return torch.cat([start, shifted], dim=1)


def record(segment_id: str, source: str, target: str) -> TranslationRecord:
    return TranslationRecord(
        segment_id=segment_id,
        source=source,
        target=target,
        direction="en2vi",
        category="test",
    )


class ConfigTests(unittest.TestCase):
    def test_v3_config_generator_preserves_seed_and_uses_error_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "configs"
            report = create_configs(
                project_root=Path.cwd(),
                dataset_dir=Path("artifacts/processed_clean_seed67_v2"),
                output_dir=output,
            )
            generated = ExperimentConfig.from_json(output / "en2vi_lora.json")
            self.assertEqual(report["split_seed"], 67)
            self.assertEqual(generated.seed, 67)
            self.assertEqual(generated.training.learning_rate, 5e-5)
            self.assertEqual(generated.training.checkpoint_eval_samples, 256)
            self.assertEqual(generated.data.overlength_policy, "error")

    def test_all_repository_configs_are_valid(self):
        for path in Path("configs/vinai").glob("*.json"):
            with self.subTest(path=path):
                ExperimentConfig.from_json(path)

    def test_repository_configs_reference_current_dataset(self):
        expected_root = Path("artifacts/processed_clean_seed67_v2")
        for path in Path("configs/vinai").glob("*.json"):
            with self.subTest(path=path):
                config = ExperimentConfig.from_json(path)
                data_files = [Path(config.data.validation_file)]
                if config.data.train_file:
                    data_files.append(Path(config.data.train_file))
                for data_file in data_files:
                    self.assertEqual(data_file.parent, expected_root)
                    self.assertTrue(data_file.is_file(), data_file)
                self.assertEqual(config.seed, 67)
                self.assertEqual(config.data.dataset_id, "legal_envi_clean_seed67_v2")
                if config.training.mode != "none":
                    self.assertEqual(config.training.eval_strategy, "epoch")
                    self.assertEqual(config.training.save_strategy, "epoch")
                    self.assertEqual(config.training.checkpoint_eval_samples, 128)
                    self.assertEqual(config.training.per_device_eval_batch_size, 16)
                if config.training.mode == "lora":
                    self.assertEqual(config.training.per_device_train_batch_size, 4)
                    self.assertEqual(config.training.gradient_accumulation_steps, 4)

    def test_frozen_dataset_contract_matches_both_directions(self):
        for name in ("en2vi_lora.json", "vi2en_lora.json"):
            with self.subTest(name=name):
                config = ExperimentConfig.from_json(Path("configs/vinai") / name)
                BaselineRunner(config)._validate_dataset_contract()

    def test_public_test_cannot_be_training_data(self):
        raw = json.loads(Path("configs/vinai/en2vi_lora.json").read_text("utf-8"))
        raw["data"]["train_file"] = "segments_public_test_en2vi.jsonl"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Public test"):
                ExperimentConfig.from_json(path)

    def test_sample_limits_must_be_positive(self):
        config = ExperimentConfig.from_json("configs/vinai/en2vi_lora.json")
        with self.assertRaisesRegex(ValueError, "max_train_samples"):
            config.apply_overrides(max_train_samples=0)


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

    def test_frozen_v2_has_no_identity_duplicate_or_train_dev_text_leakage(self):
        root = Path("artifacts/processed_clean_seed67_v2")

        def identities(path: Path):
            pairs = set()
            sources = set()
            targets = set()
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                source = " ".join(row["source"].casefold().split())
                target = " ".join(row["target"].casefold().split())
                self.assertNotEqual(source, target, row["segment_id"])
                self.assertNotIn((source, target), pairs, row["segment_id"])
                pairs.add((source, target))
                sources.add(source)
                targets.add(target)
            return sources, targets

        train_sources, train_targets = identities(root / "segments_train_en2vi.jsonl")
        dev_sources, dev_targets = identities(root / "segments_dev_en2vi.jsonl")
        self.assertTrue(train_sources.isdisjoint(dev_sources))
        self.assertTrue(train_targets.isdisjoint(dev_targets))


class TokenAuditTests(unittest.TestCase):
    def test_collator_decoder_inputs_match_target_length_for_label_smoothing(self):
        tokenizer = FakeTensorTokenizer()
        collator = DynamicSeq2SeqCollator(
            tokenizer,
            model=FakeSeq2SeqModel(),
            max_source_length=512,
            max_target_length=512,
            truncate=False,
            pad_to_multiple_of=None,
        )
        batch = collator(
            [
                {"source_text": "short source", "target_text": "a much longer target sequence"},
                {"source_text": "another source", "target_text": "short target"},
            ]
        )
        self.assertEqual(batch["labels"].shape, batch["decoder_input_ids"].shape)
        self.assertNotEqual(batch["input_ids"].shape[1], batch["labels"].shape[1])
        self.assertTrue(all("max_length" not in call for call in tokenizer.calls))

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
    def test_short_output_is_not_flagged_as_dominant_token_degeneration(self):
        self.assertEqual(TranslationMetricSuite._dominant_token_rate("very short output"), 0.0)

    def test_legal_document_identifiers_are_canonicalized(self):
        source = "Law No. 63 / 2025 / QH15 and Decree 15/2020/NĐ-CP"
        target = "Luật số 63/2025/qh15 và Nghị định 15/2020/NĐ–CP"
        self.assertEqual(extract_legal_identifiers(source), extract_legal_identifiers(target))

    def test_english_and_vietnamese_thousands_separators_compare_equal(self):
        self.assertEqual(canonicalize_number("10,000,000"), "10000000")
        self.assertEqual(canonicalize_number("10.000.000"), "10000000")
        self.assertEqual(
            extract_numbers("VND 10,000,000"),
            extract_numbers("10.000.000 đồng"),
        )

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


class ComparisonTests(unittest.TestCase):
    def test_rejects_runs_with_different_dev_fingerprints(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index, fingerprint in enumerate(("same", "different")):
                run_dir = root / str(index)
                run_dir.mkdir()
                write_json(
                    run_dir / "run_manifest.json",
                    {
                        "dataset_id": "dataset-v1",
                        "direction": "en2vi",
                        "data_files": {"validation": {"sha256": fingerprint}},
                        "validation_metrics": {"validation_chrf": 50 + index},
                    },
                )
                paths.append(run_dir)
            with self.assertRaisesRegex(ValueError, "not directly comparable"):
                comparable_rows(paths)

    def test_rejects_runs_with_different_generation_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for beams in (1, 2):
                run_dir = root / str(beams)
                run_dir.mkdir()
                write_json(
                    run_dir / "run_manifest.json",
                    {
                        "dataset_id": "dataset-v1",
                        "direction": "en2vi",
                        "generation_config": {"num_beams": beams},
                        "metric_code_sha256": "same-metric",
                        "data_files": {"validation": {"sha256": "same-dev"}},
                        "validation_metrics": {"evaluated_records": 10},
                    },
                )
                paths.append(run_dir)
            with self.assertRaisesRegex(ValueError, "generation config"):
                comparable_rows(paths)

    def test_rejects_runs_with_different_model_revisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for revision in ("revision-a", "revision-b"):
                run_dir = root / revision
                run_dir.mkdir()
                write_json(
                    run_dir / "run_manifest.json",
                    {
                        "dataset_id": "dataset-v1",
                        "direction": "en2vi",
                        "model_name": "same-model",
                        "model_revision": revision,
                        "data_files": {"validation": {"sha256": "same-dev"}},
                        "validation_metrics": {"evaluated_records": 10},
                    },
                )
                paths.append(run_dir)
            with self.assertRaisesRegex(ValueError, "base model/revision"):
                comparable_rows(paths)


class OutputSafetyTests(unittest.TestCase):
    def test_checkpoint_subset_is_category_proportional_and_document_capped(self):
        config = ExperimentConfig.from_json("configs/vinai/en2vi_lora.json")
        config.training.checkpoint_eval_samples = 20
        config.training.checkpoint_max_per_document = 6
        records = []
        for category, total in (("A", 70), ("B", 30)):
            for index in range(total):
                records.append(
                    TranslationRecord(
                        segment_id=f"{category}-{index:03d}",
                        sample_id=f"{category}/doc-{index // 5}",
                        source=f"source {index}",
                        target=f"target {index}",
                        direction="en2vi",
                        category=category,
                    )
                )
        dataset, report = BaselineRunner(config)._checkpoint_validation_dataset(
            SimpleNamespace(records=records)
        )
        self.assertEqual(len(dataset), 20)
        self.assertEqual(report["category_counts"], {"A": 14, "B": 6})
        self.assertFalse(report["document_cap_relaxed"])
        self.assertEqual(len(report["segment_ids"]), 20)

    def test_checkpoint_validation_subset_is_fixed_by_seed(self):
        config = ExperimentConfig.from_json("configs/vinai/en2vi_lora.json")
        records = [
            record(f"segment-{index:04d}", f"source {index}", f"target {index}")
            for index in range(200)
        ]
        validation = SimpleNamespace(records=records)
        first_dataset, first_report = BaselineRunner(
            config
        )._checkpoint_validation_dataset(validation)
        second_dataset, second_report = BaselineRunner(
            config
        )._checkpoint_validation_dataset(validation)
        self.assertEqual(len(first_dataset), 128)
        self.assertEqual(first_report, second_report)
        self.assertEqual(
            [item.segment_id for item in first_dataset.records],
            [item.segment_id for item in second_dataset.records],
        )

    def test_colab_training_uses_compact_logs_instead_of_tqdm(self):
        runner_source = Path("src/vinai_baseline/runner.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("disable_tqdm=True", runner_source)
        self.assertIn("CompactProgressCallback", runner_source)

    def test_epoch_strategy_has_three_validation_runs(self):
        config = ExperimentConfig.from_json("configs/vinai/en2vi_lora.json")
        plan = BaselineRunner._training_plan(config, 18_316, 1_877)
        self.assertEqual(plan["effective_batch_size_one_gpu"], 16)
        self.assertEqual(plan["planned_optimizer_updates"], 3_435)
        self.assertEqual(plan["evaluation_runs_during_training"], 3)
        self.assertEqual(plan["checkpoint_validation_records"], 128)
        self.assertEqual(
            plan["planned_generated_validation_records_during_training"], 384
        )
        self.assertEqual(plan["planned_final_validation_records"], 1_877)

    def test_completed_output_requires_a_new_run_id(self):
        config = ExperimentConfig.from_json("configs/vinai/en2vi_lora.json")
        with tempfile.TemporaryDirectory() as directory:
            config.output_dir = directory
            write_json(Path(directory) / "run_manifest.json", {"complete": True})
            with self.assertRaisesRegex(FileExistsError, "new RUN_ID"):
                BaselineRunner(config)._validate_output_state(do_train=True)

    def test_last_checkpoint_is_resolved_and_verified(self):
        config = ExperimentConfig.from_json("configs/vinai/en2vi_lora.json")
        with tempfile.TemporaryDirectory() as directory:
            config.output_dir = directory
            config.training.resume_from_checkpoint = None
            runner = BaselineRunner(config)
            runner._ensure_output_layout()
            checkpoint = runner.checkpoints_dir / "checkpoint-10"
            checkpoint.mkdir()
            write_json(checkpoint / "trainer_state.json", {"global_step": 10})
            config.training.resume_from_checkpoint = "last"
            runner._validate_output_state(do_train=True)
            self.assertEqual(
                Path(config.training.resume_from_checkpoint).resolve(),
                checkpoint.resolve(),
            )

    def test_audit_cannot_rewrite_config_of_interrupted_run(self):
        config = ExperimentConfig.from_json("configs/vinai/en2vi_lora.json")
        with tempfile.TemporaryDirectory() as directory:
            config.output_dir = directory
            runner = BaselineRunner(config)
            runner._ensure_output_layout()
            checkpoint = runner.checkpoints_dir / "checkpoint-10"
            checkpoint.mkdir()
            write_json(checkpoint / "trainer_state.json", {"global_step": 10})
            config.seed = 68
            with self.assertRaisesRegex(ValueError, "new run ID"):
                runner._validate_audit_output_state()


class DocumentInferenceTests(unittest.TestCase):
    def test_document_chunking_respects_tokens_and_preserves_separators(self):
        tokenizer = FakeTokenizer()
        source = (
            "Article 1. This is a short legal paragraph.\n\n"
            "Article 2. This paragraph is deliberately longer and must be split "
            "at a safe sentence boundary. Another sentence follows here."
        )
        chunks = split_markdown_document(source, tokenizer, maximum_tokens=32)
        self.assertTrue(all(chunk.source_tokens <= 32 for chunk in chunks))
        predictions = [f"Bản dịch {index}" for index in range(len(chunks))]
        assembled = assemble_document(chunks, predictions)
        self.assertIn("\n\n", assembled)
        self.assertEqual(assembled.count("Bản dịch"), len(chunks))
    def test_document_chunking_preserves_leading_blank_lines(self):
        tokenizer = FakeTokenizer()
        chunks = split_markdown_document(
            "\n\n# Heading\n\nBody", tokenizer, maximum_tokens=32
        )
        assembled = assemble_document(chunks, ["# Tiêu đề", "Nội dung"])
        self.assertTrue(assembled.startswith("\n\n# Tiêu đề"))
        self.assertEqual(assembled, "\n\n# Tiêu đề\n\nNội dung\n")

    def test_markdown_structure_report_flags_marker_changes(self):
        source = "# Heading\n\n- One\n- Two\n\n[Link](https://example.com)"
        output = "# Tiêu đề\n\nMột\nHai\n\n[Liên kết](https://example.com)"
        report = markdown_structure_report(source, output)
        self.assertFalse(report["structure_counts_match"])
        self.assertEqual(
            report["mismatches"]["unordered_list_items"],
            {"source": 2, "output": 0},
        )


class KaggleNotebookTests(unittest.TestCase):
    @staticmethod
    def _input_cell() -> str:
        notebook = json.loads(
            Path("notebooks/03_vinai_kaggle.ipynb").read_text(encoding="utf-8")
        )
        return next(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
            and "INPUT_NAME_HINT" in "".join(cell.get("source", []))
        )

    @staticmethod
    def _make_minimal_project(root: Path) -> None:
        (root / "src/vinai_baseline").mkdir(parents=True)
        (root / "configs/vinai").mkdir(parents=True)
        (root / "requirements-training.txt").write_text("", encoding="utf-8")
        (root / "src/vinai_baseline/cli.py").write_text("", encoding="utf-8")
        (root / "configs/vinai/dummy.json").write_text("{}", encoding="utf-8")

    def _execute_input_cell(self, input_root: Path, working_root: Path) -> dict:
        source = self._input_cell().replace(
            'Path("/kaggle/input")', f'Path(r"{input_root}")'
        ).replace(
            'dir="/kaggle/working"', f'dir=r"{working_root}"'
        )
        namespace = {"os": os}
        original = Path.cwd()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(source, "kaggle-input-cell", "exec"), namespace)
        finally:
            os.chdir(original)
        return namespace

    def test_kaggle_notebook_supports_extracted_input_and_v3_freeze(self):
        path = Path("notebooks/03_vinai_kaggle.ipynb")
        notebook = json.loads(path.read_text(encoding="utf-8"))
        code = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )
        self.assertIn("direct_candidates", code)
        self.assertIn("zip_candidates", code)
        self.assertIn("RUN_V3_SEMANTIC_AUDIT", code)
        self.assertIn("--reuse-semantic-scores", code)
        self.assertIn('DATASET_PROFILE = "v2"', code)
        self.assertIn('"v2": "legal_envi_clean_seed67_v2"', code)
        self.assertIn('get("seed") != 67', code)
        self.assertIn('get("semantic_audit_only")', code)
        for index, cell in enumerate(notebook["cells"]):
            if cell.get("cell_type") == "code":
                ast.parse("".join(cell.get("source", [])), filename=f"cell-{index}")

    def test_kaggle_input_cell_accepts_auto_extracted_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input/dataset/project"
            source.mkdir(parents=True)
            self._make_minimal_project(source)
            working = root / "working"
            working.mkdir()
            result = self._execute_input_cell(root / "input", working)
            project = Path(result["PROJECT_DIR"])
            self.assertEqual(result["input_mode"], "Kaggle Dataset đã giải nén")
            self.assertTrue((project / "src/vinai_baseline/cli.py").is_file())

    def test_kaggle_input_cell_accepts_zip_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            self._make_minimal_project(source)
            input_root = root / "input"
            input_root.mkdir()
            with zipfile.ZipFile(input_root / "NLP_v3_parent.zip", "w") as archive:
                for path in source.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(source).as_posix())
            working = root / "working"
            working.mkdir()
            result = self._execute_input_cell(input_root, working)
            project = Path(result["PROJECT_DIR"])
            self.assertTrue(str(result["input_mode"]).startswith("ZIP:"))
            self.assertTrue((project / "src/vinai_baseline/cli.py").is_file())


if __name__ == "__main__":
    unittest.main()
