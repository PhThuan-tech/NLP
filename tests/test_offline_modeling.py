"""Offline VinAI model resolution tests without loading model weights."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from src.vinai_baseline.modeling import VinAIModelFactory, validate_local_model_dir


class OfflineModelResolutionTests(unittest.TestCase):
    def _model_directory(self, root: Path) -> Path:
        model = root / "vinai-translate-en2vi-v2"
        model.mkdir()
        for name in (
            "config.json",
            "generation_config.json",
            "sentencepiece.bpe.model",
            "model.safetensors",
        ):
            (model / name).write_bytes(b"test")
        return model

    def test_local_model_directory_requires_complete_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                validate_local_model_dir(directory)

    def test_offline_factory_resolves_direction_specific_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = self._model_directory(Path(directory))
            config = SimpleNamespace(
                direction="en2vi", model_name="vinai/vinai-translate-en2vi-v2"
            )
            environment = {
                "HF_HUB_OFFLINE": "1",
                "VINAI_EN2VI_MODEL_DIR": str(model),
            }
            with patch.dict(os.environ, environment, clear=False):
                self.assertEqual(
                    VinAIModelFactory(config).base_model_source(), str(model.resolve())
                )

    def test_offline_factory_rejects_missing_direction_model(self) -> None:
        config = SimpleNamespace(
            direction="vi2en", model_name="vinai/vinai-translate-vi2en-v2"
        )
        with patch.dict(
            os.environ,
            {"HF_HUB_OFFLINE": "1", "VINAI_VI2EN_MODEL_DIR": ""},
            clear=False,
        ):
            with self.assertRaises(FileNotFoundError):
                VinAIModelFactory(config).base_model_source()

    def test_lora_identity_is_restored_after_peft_wraps_local_model(self) -> None:
        class FakeLoraConfig:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
                self.base_model_name_or_path = None
                self.revision = None

        def fake_get_peft_model(model, peft_config):
            peft_config.base_model_name_or_path = "/kaggle/input/local-model"
            return SimpleNamespace(peft_config={"default": peft_config})

        fake_peft = ModuleType("peft")
        fake_peft.LoraConfig = FakeLoraConfig
        fake_peft.TaskType = SimpleNamespace(SEQ_2_SEQ_LM="seq2seq")
        fake_peft.get_peft_model = fake_get_peft_model
        config = SimpleNamespace(
            model_name="vinai/vinai-translate-en2vi-v2",
            model_revision="pinned-revision",
            lora=SimpleNamespace(
                rank=16, alpha=32, dropout=0.05,
                target_modules=["q_proj", "v_proj"], bias="none",
            ),
        )
        with patch.dict(sys.modules, {"peft": fake_peft}):
            wrapped = VinAIModelFactory(config)._apply_lora(SimpleNamespace())
        saved = wrapped.peft_config["default"]
        self.assertEqual(saved.base_model_name_or_path, config.model_name)
        self.assertEqual(saved.revision, config.model_revision)


if __name__ == "__main__":
    unittest.main()
