"""VinAI tokenizer/model construction and optional PEFT wrapping."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ExperimentConfig
from .language import LANGUAGES, configure_tokenizer, configure_model


LOCAL_MODEL_ENV = {
    "en2vi": "VINAI_EN2VI_MODEL_DIR",
    "vi2en": "VINAI_VI2EN_MODEL_DIR",
}


def offline_mode() -> bool:
    return os.environ.get("HF_HUB_OFFLINE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def validate_local_model_dir(path: str | Path) -> Path:
    directory = Path(path).expanduser().resolve()
    required = ("config.json", "generation_config.json", "sentencepiece.bpe.model")
    missing = [name for name in required if not (directory / name).is_file()]
    weights = [
        name
        for name in ("model.safetensors", "pytorch_model.bin")
        if (directory / name).is_file()
    ]
    if missing or not weights:
        detail = [*missing, *([] if weights else ["model.safetensors"])]
        raise FileNotFoundError(
            f"Incomplete local VinAI model at {directory}; missing: {detail}"
        )
    return directory


@dataclass(frozen=True)
class ParameterReport:
    total: int
    trainable: int
    trainable_percent: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "total": self.total,
            "trainable": self.trainable,
            "trainable_percent": self.trainable_percent,
        }


class VinAIModelFactory:
    """Create direction-specific VinAI Translate components."""

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    def base_model_source(self) -> str:
        variable = LOCAL_MODEL_ENV[self.config.direction]
        configured = os.environ.get(variable, "").strip()
        if configured:
            return str(validate_local_model_dir(configured))
        if offline_mode():
            raise FileNotFoundError(
                f"Offline mode requires {variable} to point to the extracted "
                f"{self.config.model_name} snapshot"
            )
        return self.config.model_name

    def load_tokenizer(self, saved_model_dir=None) -> Any:
        try:
            from transformers import AutoTokenizer
        except ImportError as error:
            raise RuntimeError(
                "transformers is required; install requirements-training.txt"
            ) from error
        source = str(saved_model_dir) if saved_model_dir else self.base_model_source()
        tokenizer = AutoTokenizer.from_pretrained(
            source,
            revision=(
                None
                if saved_model_dir or source != self.config.model_name
                else self.config.model_revision
            ),
            trust_remote_code=self.config.trust_remote_code,
            use_fast=True,
            src_lang=LANGUAGES[self.config.direction][0],
            tgt_lang=LANGUAGES[self.config.direction][1],
            local_files_only=offline_mode(),
        )
        return configure_tokenizer(tokenizer, self.config.direction)

    def load_model(
        self, *, apply_lora: bool = True, for_inference: bool = False
    ) -> Any:
        try:
            from transformers import AutoModelForSeq2SeqLM
        except ImportError as error:
            raise RuntimeError(
                "transformers is required; install requirements-training.txt"
            ) from error

        source = self.base_model_source()
        model = AutoModelForSeq2SeqLM.from_pretrained(
            source,
            revision=(
                None if source != self.config.model_name else self.config.model_revision
            ),
            trust_remote_code=self.config.trust_remote_code,
            low_cpu_mem_usage=True,
            local_files_only=offline_mode(),
        )
        configure_model(model, self.load_tokenizer(), self.config.direction)
        generation = self.config.generation
        model.generation_config.num_beams = generation.num_beams
        model.generation_config.length_penalty = generation.length_penalty
        model.generation_config.repetition_penalty = generation.repetition_penalty
        model.generation_config.no_repeat_ngram_size = (
            generation.no_repeat_ngram_size
        )
        model.generation_config.early_stopping = generation.early_stopping
        model.generation_config.renormalize_logits = generation.renormalize_logits
        if generation.max_new_tokens is not None:
            model.generation_config.max_length = None
            model.generation_config.max_new_tokens = generation.max_new_tokens
        else:
            model.generation_config.max_length = generation.max_length
            model.generation_config.max_new_tokens = None

        if self.config.training.gradient_checkpointing and not for_inference:
            model.gradient_checkpointing_enable()
            model.config.use_cache = False
        elif for_inference:
            model.config.use_cache = True
        if self.config.training.mode == "lora" and apply_lora:
            model = self._apply_lora(model)
        return model

    def _apply_lora(self, model: Any) -> Any:
        try:
            from peft import LoraConfig as PeftLoraConfig
            from peft import TaskType, get_peft_model
        except ImportError as error:
            raise RuntimeError(
                "PEFT is required for LoRA; install requirements-training.txt"
            ) from error

        settings = self.config.lora
        peft_config = PeftLoraConfig(
            task_type=TaskType.SEQ_2_SEQ_LM,
            inference_mode=False,
            r=settings.rank,
            lora_alpha=settings.alpha,
            lora_dropout=settings.dropout,
            target_modules=settings.target_modules,
            bias=settings.bias,
        )
        # Keep adapters portable: record the canonical Hub identity even when
        # the base weights were loaded from a Kaggle Input directory.
        peft_config.base_model_name_or_path = self.config.model_name
        peft_config.revision = self.config.model_revision
        peft_model = get_peft_model(model, peft_config)
        # Recent PEFT releases overwrite the supplied identity with the
        # model's local `_name_or_path` while wrapping it. Restore the pinned
        # identity on the live config so save_pretrained writes a portable
        # adapter_config.json and offline reload validation remains strict.
        for adapter_config in peft_model.peft_config.values():
            adapter_config.base_model_name_or_path = self.config.model_name
            adapter_config.revision = self.config.model_revision
        return peft_model

    @staticmethod
    def parameter_report(model: Any) -> ParameterReport:
        total = sum(parameter.numel() for parameter in model.parameters())
        trainable = sum(
            parameter.numel()
            for parameter in model.parameters()
            if parameter.requires_grad
        )
        percent = 100 * trainable / total if total else 0.0
        return ParameterReport(
            total=total,
            trainable=trainable,
            trainable_percent=round(percent, 6),
        )
