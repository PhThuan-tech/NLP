"""Typed experiment configuration and validation.

The runtime is intentionally configured through JSON so the exact same files can
be validated on Windows and executed on Google Colab without a YAML dependency.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


Direction = Literal["en2vi", "vi2en"]
TrainingMode = Literal["none", "lora", "full"]
OverlengthPolicy = Literal["error", "drop", "truncate"]


VINAI_MODELS: dict[str, str] = {
    "en2vi": "vinai/vinai-translate-en2vi-v2",
    "vi2en": "vinai/vinai-translate-vi2en-v2",
}


@dataclass
class DataConfig:
    train_file: str
    validation_file: str
    dataset_id: str = ""
    manifest_file: str = ""
    source_field: str = "source"
    target_field: str = "target"
    max_source_length: int = 512
    max_target_length: int = 512
    overlength_policy: OverlengthPolicy = "drop"
    audit_batch_size: int = 128
    max_train_samples: int | None = None
    max_validation_samples: int | None = None

    def validate(self, direction: Direction, require_train: bool) -> None:
        if bool(self.dataset_id) != bool(self.manifest_file):
            raise ValueError(
                "data.dataset_id and data.manifest_file must be provided together"
            )
        if require_train and not self.train_file:
            raise ValueError("data.train_file is required for training")
        if not self.validation_file:
            raise ValueError("data.validation_file is required")
        if self.max_source_length < 8 or self.max_target_length < 8:
            raise ValueError("Maximum sequence lengths must be at least 8 tokens")
        if self.audit_batch_size < 1:
            raise ValueError("data.audit_batch_size must be positive")
        for name, value in (
            ("max_train_samples", self.max_train_samples),
            ("max_validation_samples", self.max_validation_samples),
        ):
            if value is not None and value < 1:
                raise ValueError(f"data.{name} must be positive when provided")
        if self.overlength_policy not in {"error", "drop", "truncate"}:
            raise ValueError(f"Unsupported overlength policy: {self.overlength_policy}")

        for split, value in (
            ("train", self.train_file),
            ("validation", self.validation_file),
        ):
            if not value or (split == "train" and not require_train):
                continue
            lower = Path(value).name.lower()
            if "public_test" in lower and split == "train":
                raise ValueError("Public test must never be used as the training file")
            if direction not in lower:
                raise ValueError(
                    f"The {split} filename does not match direction {direction}: {value}"
                )


@dataclass
class GenerationConfig:
    num_beams: int = 2
    max_length: int = 512
    max_new_tokens: int | None = None
    length_penalty: float = 1.0
    repetition_penalty: float = 1.0
    no_repeat_ngram_size: int = 3
    early_stopping: bool = True
    renormalize_logits: bool = True

    def validate(self) -> None:
        if self.num_beams < 1:
            raise ValueError("generation.num_beams must be positive")
        if self.max_length < 8:
            raise ValueError("generation.max_length must be at least 8")
        if self.max_new_tokens is not None and self.max_new_tokens < 8:
            raise ValueError("generation.max_new_tokens must be at least 8")
        if self.length_penalty <= 0:
            raise ValueError("generation.length_penalty must be positive")
        if self.repetition_penalty <= 0:
            raise ValueError("generation.repetition_penalty must be positive")
        if self.no_repeat_ngram_size < 0:
            raise ValueError("generation.no_repeat_ngram_size cannot be negative")


@dataclass
class LoraConfig:
    rank: int = 16
    alpha: int = 32
    dropout: float = 0.05
    target_modules: list[str] = field(default_factory=lambda: ["q_proj", "v_proj"])
    bias: str = "none"

    def validate(self) -> None:
        if self.rank < 1 or self.alpha < 1:
            raise ValueError("LoRA rank and alpha must be positive")
        if not 0 <= self.dropout < 1:
            raise ValueError("LoRA dropout must be in [0, 1)")
        if not self.target_modules:
            raise ValueError("At least one LoRA target module is required")


@dataclass
class TrainingConfig:
    mode: TrainingMode = "lora"
    epochs: float = 3.0
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.05
    label_smoothing: float = 0.1
    per_device_train_batch_size: int = 1
    per_device_eval_batch_size: int = 2
    gradient_accumulation_steps: int = 16
    gradient_checkpointing: bool = True
    fp16: bool = True
    bf16: bool = False
    tf32: bool = False
    eval_strategy: str = "steps"
    save_strategy: str = "steps"
    eval_steps: int = 250
    save_steps: int = 250
    logging_steps: int = 25
    save_total_limit: int = 2
    dataloader_num_workers: int = 2
    checkpoint_eval_samples: int | None = None
    checkpoint_max_per_document: int | None = 6
    early_stopping_patience: int = 2
    metric_for_best_model: str = "chrf"
    greater_is_better: bool = True
    require_cuda: bool = True
    auto_find_batch_size: bool = False
    resume_from_checkpoint: str | None = None

    def validate(self) -> None:
        if self.mode not in {"none", "lora", "full"}:
            raise ValueError(f"Unsupported training mode: {self.mode}")
        if self.mode != "none" and self.epochs <= 0:
            raise ValueError("training.epochs must be positive")
        if self.learning_rate <= 0:
            raise ValueError("training.learning_rate must be positive")
        if self.per_device_train_batch_size < 1:
            raise ValueError("Training batch size must be positive")
        if self.per_device_eval_batch_size < 1:
            raise ValueError("Evaluation batch size must be positive")
        if self.gradient_accumulation_steps < 1:
            raise ValueError("Gradient accumulation steps must be positive")
        if not 0 <= self.warmup_ratio < 1:
            raise ValueError("training.warmup_ratio must be in [0, 1)")
        if not 0 <= self.label_smoothing < 1:
            raise ValueError("training.label_smoothing must be in [0, 1)")
        if self.fp16 and self.bf16:
            raise ValueError("Choose only one of fp16 and bf16")
        if self.eval_strategy not in {"no", "steps", "epoch"}:
            raise ValueError(f"Unsupported eval_strategy: {self.eval_strategy}")
        if self.save_strategy not in {"no", "steps", "epoch"}:
            raise ValueError(f"Unsupported save_strategy: {self.save_strategy}")
        if self.eval_strategy != self.save_strategy:
            raise ValueError(
                "eval_strategy and save_strategy must match when loading the best model"
            )
        if self.eval_strategy == "steps":
            if self.eval_steps < 1 or self.save_steps < 1:
                raise ValueError("eval_steps and save_steps must be positive")
            if self.save_steps % self.eval_steps:
                raise ValueError("save_steps must be a multiple of eval_steps")
        if self.early_stopping_patience > 0 and self.mode != "none":
            if self.eval_strategy == "no":
                raise ValueError("Early stopping requires evaluation")
        if self.dataloader_num_workers < 0:
            raise ValueError("dataloader_num_workers cannot be negative")
        if (
            self.checkpoint_eval_samples is not None
            and self.checkpoint_eval_samples < 1
        ):
            raise ValueError("training.checkpoint_eval_samples must be positive")
        if (
            self.checkpoint_max_per_document is not None
            and self.checkpoint_max_per_document < 1
        ):
            raise ValueError(
                "training.checkpoint_max_per_document must be positive"
            )


@dataclass
class ExperimentConfig:
    run_name: str
    direction: Direction
    model_name: str
    output_dir: str
    seed: int
    data: DataConfig
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    lora: LoraConfig = field(default_factory=LoraConfig)
    model_revision: str = "main"
    trust_remote_code: bool = False

    @classmethod
    def from_json(cls, path: str | Path) -> "ExperimentConfig":
        config_path = Path(path)
        raw_text = os.path.expandvars(config_path.read_text(encoding="utf-8"))
        raw: dict[str, Any] = json.loads(raw_text)
        config = cls(
            run_name=raw["run_name"],
            direction=raw["direction"],
            model_name=raw["model_name"],
            output_dir=raw["output_dir"],
            seed=int(raw.get("seed", 67)),
            data=DataConfig(**raw["data"]),
            generation=GenerationConfig(**raw.get("generation", {})),
            training=TrainingConfig(**raw.get("training", {})),
            lora=LoraConfig(**raw.get("lora", {})),
            model_revision=raw.get("model_revision", "main"),
            trust_remote_code=bool(raw.get("trust_remote_code", False)),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.direction not in VINAI_MODELS:
            raise ValueError(f"Unsupported direction: {self.direction}")
        expected = VINAI_MODELS[self.direction]
        if self.model_name != expected:
            raise ValueError(
                f"Direction {self.direction} expects {expected}, got {self.model_name}"
            )
        if not self.run_name.strip():
            raise ValueError("run_name cannot be empty")
        if not self.output_dir:
            raise ValueError("output_dir cannot be empty")
        if self.seed < 0:
            raise ValueError("seed cannot be negative")
        self.data.validate(
            direction=self.direction,
            require_train=self.training.mode != "none",
        )
        self.generation.validate()
        self.training.validate()
        self.lora.validate()

    def apply_overrides(
        self,
        *,
        output_dir: str | None = None,
        train_file: str | None = None,
        validation_file: str | None = None,
        max_train_samples: int | None = None,
        max_validation_samples: int | None = None,
        resume_from_checkpoint: str | None = None,
        allow_cpu: bool = False,
    ) -> None:
        if output_dir:
            self.output_dir = output_dir
        if train_file:
            self.data.train_file = train_file
        if validation_file:
            self.data.validation_file = validation_file
        if max_train_samples is not None:
            self.data.max_train_samples = max_train_samples
        if max_validation_samples is not None:
            self.data.max_validation_samples = max_validation_samples
        if resume_from_checkpoint:
            self.training.resume_from_checkpoint = resume_from_checkpoint
        if allow_cpu:
            self.training.require_cuda = False
            self.training.fp16 = False
            self.training.bf16 = False
        self.validate()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
