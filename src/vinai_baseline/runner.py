"""End-to-end audit, zero-shot evaluation, and fine-tuning orchestration."""

from __future__ import annotations

import importlib.metadata
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ExperimentConfig
from .data import (
    DynamicSeq2SeqCollator,
    JsonlCorpus,
    PreparedCorpus,
    TokenizerAuditor,
    sha256_file,
    write_json,
    write_jsonl,
)
from .metrics import TranslationMetricSuite
from .modeling import VinAIModelFactory


class BaselineRunner:
    """Run one fully specified VinAI experiment."""

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.reports_dir = self.output_dir / "reports"
        self.predictions_dir = self.output_dir / "predictions"
        self.checkpoints_dir = self.output_dir / "checkpoints"
        self.best_model_dir = self.output_dir / "best_model"
        self.factory = VinAIModelFactory(config)

    def _ensure_output_layout(self) -> None:
        for path in (
            self.output_dir,
            self.reports_dir,
            self.predictions_dir,
            self.checkpoints_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        write_json(self.output_dir / "resolved_config.json", self.config.to_dict())

    def _load_records(self, split: str) -> list[Any]:
        is_train = split == "train"
        path = self.config.data.train_file if is_train else self.config.data.validation_file
        limit = (
            self.config.data.max_train_samples
            if is_train
            else self.config.data.max_validation_samples
        )
        return JsonlCorpus(
            path,
            direction=self.config.direction,
            source_field=self.config.data.source_field,
            target_field=self.config.data.target_field,
            limit=limit,
        ).load()

    def _prepare_records(
        self, tokenizer: Any, records: list[Any], split: str
    ) -> PreparedCorpus:
        data = self.config.data
        prepared = TokenizerAuditor(
            tokenizer,
            max_source_length=data.max_source_length,
            max_target_length=data.max_target_length,
            batch_size=data.audit_batch_size,
            policy=data.overlength_policy,
        ).prepare(records)
        write_json(
            self.reports_dir / f"token_audit_{split}.json",
            prepared.audit.to_dict(),
        )
        return prepared

    def audit(self) -> dict[str, Any]:
        """Download only the tokenizer and report exact sequence lengths."""
        self._ensure_output_layout()
        tokenizer = self.factory.load_tokenizer()
        payload: dict[str, Any] = {
            "run_name": self.config.run_name,
            "model_name": self.config.model_name,
            "direction": self.config.direction,
        }
        if self.config.data.train_file:
            train = self._prepare_records(
                tokenizer, self._load_records("train"), "train"
            )
            payload["train"] = train.audit.to_dict()
        validation = self._prepare_records(
            tokenizer, self._load_records("validation"), "validation"
        )
        payload["validation"] = validation.audit.to_dict()
        write_json(self.reports_dir / "token_audit_summary.json", payload)
        return payload

    def _check_hardware(self) -> Any:
        try:
            import torch
        except ImportError as error:
            raise RuntimeError("PyTorch is required for training/evaluation") from error
        if self.config.training.require_cuda and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is required by this config, but PyTorch cannot see a GPU. "
                "Enable a GPU runtime or pass --allow-cpu only for a small smoke test."
            )
        if self.config.training.bf16 and torch.cuda.is_available():
            supported = getattr(torch.cuda, "is_bf16_supported", lambda: False)()
            if not supported:
                raise RuntimeError("bf16 was requested but this GPU does not support it")
        return torch

    @staticmethod
    def _warmup_steps(config: ExperimentConfig, train_size: int) -> int:
        train = config.training
        batches = math.ceil(train_size / train.per_device_train_batch_size)
        update_steps = math.ceil(batches / train.gradient_accumulation_steps)
        total_steps = math.ceil(update_steps * train.epochs)
        return round(total_steps * train.warmup_ratio)

    def _training_arguments(self, *, train_size: int | None, do_train: bool) -> Any:
        from transformers import Seq2SeqTrainingArguments

        train = self.config.training
        load_best = do_train and train.eval_strategy != "no"
        warmup_steps = self._warmup_steps(self.config, train_size or 1) if do_train else 0
        return Seq2SeqTrainingArguments(
            output_dir=str(self.checkpoints_dir),
            run_name=self.config.run_name,
            do_train=do_train,
            do_eval=True,
            do_predict=True,
            num_train_epochs=train.epochs,
            learning_rate=train.learning_rate,
            weight_decay=train.weight_decay,
            warmup_steps=warmup_steps,
            label_smoothing_factor=train.label_smoothing,
            per_device_train_batch_size=train.per_device_train_batch_size,
            per_device_eval_batch_size=train.per_device_eval_batch_size,
            gradient_accumulation_steps=train.gradient_accumulation_steps,
            gradient_checkpointing=train.gradient_checkpointing,
            fp16=train.fp16,
            bf16=train.bf16,
            tf32=train.tf32,
            eval_strategy=train.eval_strategy if do_train else "no",
            save_strategy=train.save_strategy if do_train else "no",
            eval_steps=train.eval_steps if do_train else None,
            save_steps=train.save_steps if do_train else 500,
            logging_steps=train.logging_steps,
            save_total_limit=train.save_total_limit,
            load_best_model_at_end=load_best,
            metric_for_best_model=train.metric_for_best_model if load_best else None,
            greater_is_better=train.greater_is_better if load_best else None,
            predict_with_generate=True,
            generation_max_length=self.config.generation.max_length,
            generation_num_beams=self.config.generation.num_beams,
            dataloader_num_workers=train.dataloader_num_workers,
            dataloader_pin_memory=True,
            remove_unused_columns=False,
            report_to=[],
            seed=self.config.seed,
            data_seed=self.config.seed,
            optim="adamw_torch",
            auto_find_batch_size=train.auto_find_batch_size,
            skip_memory_metrics=False,
            use_cpu=not self.config.training.require_cuda,
            use_cache=False if do_train else True,
        )

    def _trainer(
        self,
        *,
        model: Any,
        tokenizer: Any,
        train_corpus: PreparedCorpus | None,
        validation_corpus: PreparedCorpus,
    ) -> Any:
        from transformers import EarlyStoppingCallback, Seq2SeqTrainer

        metric_suite = TranslationMetricSuite(tokenizer)
        collator = DynamicSeq2SeqCollator(
            tokenizer,
            max_source_length=self.config.data.max_source_length,
            max_target_length=self.config.data.max_target_length,
            truncate=self.config.data.overlength_policy == "truncate",
        )
        callbacks = []
        do_train = train_corpus is not None
        if do_train and self.config.training.early_stopping_patience > 0:
            callbacks.append(
                EarlyStoppingCallback(
                    early_stopping_patience=(
                        self.config.training.early_stopping_patience
                    )
                )
            )
        return Seq2SeqTrainer(
            model=model,
            args=self._training_arguments(
                train_size=len(train_corpus.records) if train_corpus else None,
                do_train=do_train,
            ),
            train_dataset=train_corpus.dataset if train_corpus else None,
            eval_dataset=validation_corpus.dataset,
            data_collator=collator,
            processing_class=tokenizer,
            compute_metrics=metric_suite,
            callbacks=callbacks,
        )

    def evaluate(self) -> dict[str, Any]:
        """Run the untouched pretrained model on the frozen validation set."""
        return self._run(do_train=False)

    def train(self) -> dict[str, Any]:
        """Fine-tune using LoRA/full mode, then evaluate the best checkpoint."""
        if self.config.training.mode == "none":
            raise ValueError("Use an lora/full config for the train command")
        return self._run(do_train=True)

    def _run(self, *, do_train: bool) -> dict[str, Any]:
        self._ensure_output_layout()
        torch = self._check_hardware()
        from transformers import set_seed

        set_seed(self.config.seed)
        tokenizer = self.factory.load_tokenizer()
        validation = self._prepare_records(
            tokenizer, self._load_records("validation"), "validation"
        )
        train_corpus = None
        if do_train:
            train_corpus = self._prepare_records(
                tokenizer, self._load_records("train"), "train"
            )

        model = self.factory.load_model()
        parameter_report = self.factory.parameter_report(model)
        write_json(
            self.reports_dir / "parameter_report.json",
            parameter_report.to_dict(),
        )
        trainer = self._trainer(
            model=model,
            tokenizer=tokenizer,
            train_corpus=train_corpus,
            validation_corpus=validation,
        )

        train_metrics: dict[str, Any] = {}
        if do_train:
            result = trainer.train(
                resume_from_checkpoint=self.config.training.resume_from_checkpoint
            )
            train_metrics = dict(result.metrics)
            trainer.save_model(str(self.best_model_dir))
            tokenizer.save_pretrained(str(self.best_model_dir))
            write_json(self.reports_dir / "train_metrics.json", train_metrics)

        if hasattr(trainer.model, "config"):
            trainer.model.config.use_cache = True
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
        prediction_output = trainer.predict(
            validation.dataset,
            metric_key_prefix="validation",
        )
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            peak_vram_mb = torch.cuda.max_memory_allocated() / (1024**2)
        else:
            peak_vram_mb = 0.0

        metric_suite = TranslationMetricSuite(tokenizer)
        predictions = metric_suite.decode_predictions(prediction_output.predictions)
        rows = [
            record.to_output_mapping(prediction)
            for record, prediction in zip(
                validation.records, predictions, strict=True
            )
        ]
        write_jsonl(
            self.predictions_dir / "validation_predictions.jsonl",
            rows,
        )
        category_metrics = self._category_metrics(
            metric_suite, validation.records, predictions
        )
        write_json(
            self.reports_dir / "validation_metrics_by_category.json",
            category_metrics,
        )
        validation_metrics = dict(prediction_output.metrics)
        validation_metrics["peak_vram_mb"] = round(peak_vram_mb, 3)
        validation_metrics["evaluated_records"] = len(validation.records)
        validation_metrics["parameter_report"] = parameter_report.to_dict()
        write_json(
            self.reports_dir / "validation_metrics.json",
            validation_metrics,
        )
        manifest = self._runtime_manifest(
            train_metrics=train_metrics,
            validation_metrics=validation_metrics,
        )
        write_json(self.output_dir / "run_manifest.json", manifest)
        return manifest

    @staticmethod
    def _category_metrics(
        metric_suite: TranslationMetricSuite,
        records: list[Any],
        predictions: list[str],
    ) -> dict[str, Any]:
        """Score every category independently to expose domain regressions."""
        output: dict[str, Any] = {}
        categories = sorted({record.category or "unknown" for record in records})
        for category in categories:
            indices = [
                index
                for index, record in enumerate(records)
                if (record.category or "unknown") == category
            ]
            category_predictions = [predictions[index] for index in indices]
            category_references = [records[index].target for index in indices]
            output[category] = {
                "records": len(indices),
                **metric_suite.score_texts(
                    category_predictions,
                    category_references,
                ),
            }
        return output

    def _runtime_manifest(
        self,
        *,
        train_metrics: dict[str, Any],
        validation_metrics: dict[str, Any],
    ) -> dict[str, Any]:
        packages = {}
        for name in ("torch", "transformers", "accelerate", "peft", "sacrebleu"):
            try:
                packages[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                packages[name] = None
        gpu_name = None
        try:
            import torch

            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
        except ImportError:
            pass
        return {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "run_name": self.config.run_name,
            "direction": self.config.direction,
            "model_name": self.config.model_name,
            "model_revision": self.config.model_revision,
            "training_mode": self.config.training.mode,
            "python": sys.version,
            "platform": platform.platform(),
            "gpu": gpu_name,
            "packages": packages,
            "data_files": self._data_manifest(),
            "train_metrics": train_metrics,
            "validation_metrics": validation_metrics,
        }

    def _data_manifest(self) -> dict[str, Any]:
        """Record exact input paths and hashes for comparable experiments."""
        result: dict[str, Any] = {}
        candidates = {
            "train": self.config.data.train_file,
            "validation": self.config.data.validation_file,
        }
        for split, value in candidates.items():
            if not value:
                continue
            path = Path(value)
            result[split] = {
                "path": str(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        return result
