"""VinAI tokenizer/model construction and optional PEFT wrapping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import ExperimentConfig


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

    def load_tokenizer(self) -> Any:
        try:
            from transformers import AutoTokenizer
        except ImportError as error:
            raise RuntimeError(
                "transformers is required; install requirements-training.txt"
            ) from error
        return AutoTokenizer.from_pretrained(
            self.config.model_name,
            revision=self.config.model_revision,
            trust_remote_code=self.config.trust_remote_code,
            use_fast=True,
        )

    def load_model(self) -> Any:
        try:
            from transformers import AutoModelForSeq2SeqLM
        except ImportError as error:
            raise RuntimeError(
                "transformers is required; install requirements-training.txt"
            ) from error

        model = AutoModelForSeq2SeqLM.from_pretrained(
            self.config.model_name,
            revision=self.config.model_revision,
            trust_remote_code=self.config.trust_remote_code,
            low_cpu_mem_usage=True,
        )
        generation = self.config.generation
        model.generation_config.num_beams = generation.num_beams
        model.generation_config.max_length = generation.max_length
        model.generation_config.length_penalty = generation.length_penalty
        model.generation_config.no_repeat_ngram_size = (
            generation.no_repeat_ngram_size
        )
        model.generation_config.early_stopping = generation.early_stopping

        if self.config.training.gradient_checkpointing:
            model.gradient_checkpointing_enable()
            model.config.use_cache = False
        if self.config.training.mode == "lora":
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
        return get_peft_model(model, peft_config)

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
