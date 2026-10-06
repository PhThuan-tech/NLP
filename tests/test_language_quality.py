import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.vinai_baseline.language import configure_model, configure_tokenizer
from src.vinai_baseline.quality import quality_report
from src.vinai_baseline.preflight_cli import require_zero_shot_gate


class Tokenizer:
    unk_token_id = 3
    src_lang = tgt_lang = "en_XX"

    def convert_tokens_to_ids(self, token):
        return {"en_XX": 10, "vi_VN": 11}.get(token, self.unk_token_id)

    def __call__(self, text=None, text_target=None, **kwargs):
        lang = self.src_lang if text_target is None else self.tgt_lang
        return {"input_ids": [5, 2, self.convert_tokens_to_ids(lang)]}


class LanguageQualityTests(unittest.TestCase):
    def test_resume_rejects_legacy_run_without_language_marker(self):
        from src.vinai_baseline.config import ExperimentConfig
        from src.vinai_baseline.runner import BaselineRunner
        config = ExperimentConfig.from_json("configs/generated_v3/en2vi_lora.json")
        with tempfile.TemporaryDirectory() as tmp:
            config.output_dir = tmp
            checkpoint = Path(tmp) / "checkpoints/checkpoint-10"
            checkpoint.mkdir(parents=True)
            (checkpoint / "trainer_state.json").write_text("{}", encoding="utf-8")
            (Path(tmp) / "resolved_config.json").write_text(json.dumps(config.to_dict()), encoding="utf-8")
            config.training.resume_from_checkpoint = "last"
            with self.assertRaisesRegex(ValueError, "language-control"):
                BaselineRunner(config)._validate_output_state(do_train=True)

    def test_both_directions_and_model_start(self):
        for direction, source, target in [("en2vi", 10, 11), ("vi2en", 11, 10)]:
            tokenizer = configure_tokenizer(Tokenizer(), direction)
            self.assertEqual(tokenizer("x")["input_ids"][-1], source)
            self.assertEqual(tokenizer(text_target="y")["input_ids"][-1], target)
            model = SimpleNamespace(config=SimpleNamespace(vocab_size=20), generation_config=SimpleNamespace())
            configure_model(model, tokenizer, direction)
            self.assertEqual(model.generation_config.decoder_start_token_id, target)
            self.assertIsNone(model.generation_config.forced_bos_token_id)

    def test_broken_target_mode_fails_before_training(self):
        class Broken(Tokenizer):
            def __call__(self, *args, **kwargs):
                return {"input_ids": [5, 2, 10]}
        with self.assertRaisesRegex(ValueError, "expected source/target"):
            configure_tokenizer(Broken(), "en2vi")

    def test_degeneration_empty_wrong_language_and_excessive_length_fail(self):
        reference = "Bộ xây dựng quy định các điều kiện thực hiện chính sách nhà ở tại Việt Nam."
        for prediction in ["B " * 20, "1 1 1 " * 20, "",
                           "nhà ở Việt Nam " * 40,
                           "This is a long English sentence that does not contain Vietnamese accents whatsoever."]:
            with self.subTest(prediction=prediction):
                self.assertEqual(quality_report([prediction], [reference], "en2vi")["status"], "failed")

    def test_under_translation_is_reported_but_does_not_block_new_training(self):
        reference = "Bộ xây dựng quy định các điều kiện thực hiện chính sách nhà ở tại Việt Nam."
        report = quality_report(["Nhà ở"], [reference], "en2vi")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["failed_records"], 0)
        self.assertEqual(report["warning_records"], 1)
        self.assertEqual(report["warnings"][0]["reasons"], ["under_translation"])

    def test_nonempty_severe_under_translation_warns_but_empty_still_fails(self):
        reference = "nội dung " * 120
        short = quality_report(["Một mục."], [reference], "en2vi")
        empty = quality_report([""], [reference], "en2vi")
        self.assertEqual(short["status"], "passed")
        self.assertEqual(short["warnings"][0]["reasons"], ["severe_under_translation"])
        self.assertEqual(empty["status"], "failed")
        self.assertIn("empty_output", empty["failures"][0]["reasons"])

    def test_short_legal_clause_is_not_a_dominance_false_positive(self):
        text = "2. Bãi bỏ Điều 15 và Điều 22. Điều 18. Điều khoản thi hành"
        report = quality_report([text], [text], "en2vi")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["failed_records"], 0)

    def test_legitimate_repeated_legal_phrases_and_short_output_pass(self):
        text = "Quy định tại Điều 1. Quy định tại Điều 2. Quy định tại Điều 3."
        self.assertEqual(quality_report([text, "Xin chào"], [text, "Xin chào"], "en2vi")["status"], "passed")
        english = "The Ministry of Construction regulates housing development in this province."
        self.assertEqual(quality_report([english], [english], "vi2en")["status"], "passed")

    def test_long_legal_article_enumeration_is_not_token_collapse(self):
        text = "; ".join(f"Điều {number}" for number in range(1, 31))
        report = quality_report([text], [text], "en2vi")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["failed_records"], 0)

    def test_nonlegal_dominant_token_still_fails(self):
        text = " ".join(f"spam item{number}" for number in range(30))
        report = quality_report([text], [text], "vi2en")
        self.assertEqual(report["status"], "failed")
        self.assertIn("dominant_token", report["failures"][0]["reasons"])

    def test_gate_rejects_adapter_failed_and_stale_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gate.json"
            good = {"kind": "zero_shot", "identity": {"revision": "new"}, "requested_samples": 256,
                    "quality": {"status": "passed", "evaluated_records": 256}}
            with patch("src.vinai_baseline.preflight_cli.identity", return_value={"revision": "new"}):
                path.write_text(json.dumps(good), encoding="utf-8")
                require_zero_shot_gate(None, path)
                for field, value in [("kind", "adapter"), ("identity", {"revision": "old"}),
                                     ("requested_samples", 16),
                                     ("quality", {"status": "failed", "evaluated_records": 256})]:
                    path.write_text(json.dumps({**good, field: value}), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        require_zero_shot_gate(None, path)
