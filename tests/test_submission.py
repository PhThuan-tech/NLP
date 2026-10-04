import unittest
from pathlib import Path

from src.vinai_baseline.config import ExperimentConfig
from src.vinai_baseline.service import detect_direction, direction_from_request


class SubmissionContractTests(unittest.TestCase):
    def test_submission_configs_are_valid_and_revision_pinned(self):
        expected = {
            "en2vi": ("1e47495b5dac16097b1d9e7b4133c27e1f40504f", 2, 1.1),
            "vi2en": ("4eb2219d447d4352861e71e371a6b6abcb0509c8", 4, 1.1),
        }
        for direction, (revision, beams, length_penalty) in expected.items():
            with self.subTest(direction=direction):
                config = ExperimentConfig.from_json(
                    Path("submission/configs") / f"{direction}.json"
                )
                self.assertEqual(config.direction, direction)
                self.assertEqual(config.model_revision, revision)
                self.assertEqual(config.generation.num_beams, beams)
                self.assertEqual(config.generation.length_penalty, length_penalty)
                self.assertTrue(config.training.require_cuda)

    def test_detects_english_legal_document(self):
        text = "Article 2. The rights and obligations under this Law shall apply."
        self.assertEqual(detect_direction(text), "en2vi")

    def test_detects_vietnamese_legal_document(self):
        text = "Điều 2. Quyền và nghĩa vụ của người dân được quy định theo pháp luật."
        self.assertEqual(detect_direction(text), "vi2en")

    def test_explicit_route_wins_over_detection(self):
        text = "Điều 2. Nội dung này được viết bằng tiếng Việt."
        self.assertEqual(
            direction_from_request("/translate/en2vi", None, text), "en2vi"
        )

    def test_header_and_query_direction_are_supported(self):
        self.assertEqual(
            direction_from_request("/translate", "vi→en", "123"), "vi2en"
        )
        self.assertEqual(
            direction_from_request("/translate?direction=en-vi", None, "123"),
            "en2vi",
        )

    def test_short_inputs_have_safe_fallbacks(self):
        self.assertEqual(detect_direction("Điều 1"), "vi2en")
        self.assertEqual(detect_direction("Contract"), "en2vi")
        with self.assertRaisesRegex(ValueError, "no language-bearing"):
            detect_direction("12345 -- ###")

    def test_wrapper_has_exact_three_argument_contract(self):
        wrapper = Path("submission/translate.sh").read_text(encoding="utf-8")
        self.assertIn("[[ $# -ne 3 ]]", wrapper)
        self.assertIn("--data-binary", wrapper)
        self.assertIn("input_words_per_second", wrapper)


if __name__ == "__main__":
    unittest.main()
