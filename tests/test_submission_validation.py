import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.validate_submission import MODEL_SPECS, validate_model


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def write_safetensors(path: Path, shape: list[int]) -> None:
    header = json.dumps(
        {"weight": {"dtype": "F32", "shape": shape, "data_offsets": [0, 4]}},
        separators=(",", ":"),
    ).encode("utf-8")
    path.write_bytes(struct.pack("<Q", len(header)) + header + b"\0\0\0\0")


class SubmissionValidationTests(unittest.TestCase):
    def make_model(self, root: Path, direction: str) -> Path:
        model = root / direction
        model.mkdir()
        write_json(model / "config.json", {"model_type": "m2m_100"})
        write_json(model / "tokenizer_config.json", {})
        write_safetensors(model / "model.safetensors", [2, 3])
        files = {}
        for path in model.iterdir():
            files[path.name] = {
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        spec = MODEL_SPECS[direction]
        write_json(
            model / "merge_manifest.json",
            {
                "direction": direction,
                "base_model": spec["base_model"],
                "base_model_revision": spec["revision"],
                "files": files,
            },
        )
        return model

    def test_valid_merged_model_counts_parameters_and_checks_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            model = self.make_model(Path(directory), "en2vi")
            report = validate_model("en2vi", model)
            self.assertEqual(report["parameter_count"], 6)
            self.assertEqual(report["manifest_files_checked"], 3)

    def test_wrong_direction_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            model = self.make_model(Path(directory), "en2vi")
            manifest = json.loads((model / "merge_manifest.json").read_text())
            manifest["direction"] = "vi2en"
            write_json(model / "merge_manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "Wrong en2vi merge identity"):
                validate_model("en2vi", model)


if __name__ == "__main__":
    unittest.main()
