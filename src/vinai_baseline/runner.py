"""End-to-end audit, zero-shot evaluation, and fine-tuning orchestration."""

from __future__ import annotations

import importlib.metadata
import json
import math
import platform
import sys
import time
from copy import deepcopy
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

    @staticmethod
    def _status(message: str) -> None:
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"[{timestamp}] {message}", flush=True)

    def _ensure_output_layout(self) -> None:
        for path in (
            self.output_dir,
            self.reports_dir,
            self.predictions_dir,
            self.checkpoints_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        write_json(self.output_dir / "resolved_config.json", self.config.to_dict())

    @staticmethod
    def _resume_comparable_config(payload: dict[str, Any]) -> dict[str, Any]:
        """Remove the one field that is expected to change when resuming."""
        normalized = deepcopy(payload)
        normalized.get("training", {}).pop("resume_from_checkpoint", None)
        return normalized

    def _resolve_resume_checkpoint(self) -> Path | None:
        requested = self.config.training.resume_from_checkpoint
        if not requested:
            return None
        if requested == "last":
            candidates = []
            if self.checkpoints_dir.is_dir():
                for path in self.checkpoints_dir.glob("checkpoint-*"):
                    try:
                        step = int(path.name.removeprefix("checkpoint-"))
                    except ValueError:
                        continue
                    candidates.append((step, path))
            if not candidates:
                raise FileNotFoundError(
                    f"No checkpoint-* directory found in {self.checkpoints_dir}"
                )
            checkpoint = max(candidates)[1]
        else:
            checkpoint = Path(requested)
            if not checkpoint.is_absolute():
                checkpoint = self.output_dir / checkpoint
        checkpoint = checkpoint.resolve()
        checkpoint_root = self.checkpoints_dir.resolve()
        if checkpoint_root not in checkpoint.parents:
            raise ValueError(
                f"Resume checkpoint must be inside {checkpoint_root}, got {checkpoint}"
            )
        if not (checkpoint / "trainer_state.json").is_file():
            raise FileNotFoundError(
                f"Invalid checkpoint (trainer_state.json is missing): {checkpoint}"
            )
        self.config.training.resume_from_checkpoint = str(checkpoint)
        return checkpoint

    def _validate_saved_config(self) -> None:
        saved_path = self.output_dir / "resolved_config.json"
        if not saved_path.is_file():
            raise FileNotFoundError(
                f"Cannot verify existing run because {saved_path} is missing"
            )
        saved = json.loads(saved_path.read_text(encoding="utf-8"))
        if self._resume_comparable_config(saved) != self._resume_comparable_config(
            self.config.to_dict()
        ):
            raise ValueError(
                "The current config differs from the config stored in this run. "
                "Use a new run ID for changed data, model, seed, or hyperparameters."
            )

    def _validate_audit_output_state(self) -> None:
        """Do not let a repeated audit rewrite the identity of an existing run."""
        has_run_state = (
            (self.output_dir / "run_manifest.json").exists()
            or self.best_model_dir.exists()
            or (
                self.checkpoints_dir.is_dir()
                and any(self.checkpoints_dir.glob("checkpoint-*"))
            )
        )
        if has_run_state:
            self._validate_saved_config()

    def _validate_output_state(self, *, do_train: bool) -> None:
        """Protect completed runs and verify that a resume targets the same run."""
        completed = self.output_dir / "run_manifest.json"
        if completed.exists():
            raise FileExistsError(
                f"Run is already complete: {self.output_dir}. Use a new RUN_ID "
                "instead of overwriting or resuming a completed run."
            )
        checkpoint = self._resolve_resume_checkpoint()
        if checkpoint is not None:
            if not do_train:
                raise ValueError("--resume-from-checkpoint is valid only for training")
            self._validate_saved_config()
            self._status(f"Resume checkpoint verified: {checkpoint}")
            return

        checkpoints = (
            list(self.checkpoints_dir.glob("checkpoint-*"))
            if self.checkpoints_dir.is_dir()
            else []
        )
        if checkpoints or self.best_model_dir.exists():
            raise FileExistsError(
                f"Output directory already contains a run: {self.output_dir}. "
                "Use a new RUN_ID, or resume explicitly with "
                "--resume-from-checkpoint last."
            )

    def _validate_dataset_contract(self) -> None:
        """Fail before model download when dataset identity or bytes differ."""
        data = self.config.data
        if not data.manifest_file:
            return
        manifest_path = Path(data.manifest_file)
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Dataset manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        actual_id = manifest.get("dataset_id")
        if actual_id != data.dataset_id:
            raise ValueError(
                f"Dataset ID mismatch: config={data.dataset_id!r}, "
                f"manifest={actual_id!r}"
            )
        expected_files = manifest.get("files")
        if not isinstance(expected_files, dict):
            raise ValueError(f"Dataset manifest has no file checksums: {manifest_path}")

        candidates = {
            "train": data.train_file if self.config.training.mode != "none" else "",
            "validation": data.validation_file,
        }
        for split, value in candidates.items():
            if not value:
                continue
            path = Path(value)
            if not path.is_file():
                raise FileNotFoundError(f"Dataset {split} file not found: {path}")
            if path.resolve().parent != manifest_path.resolve().parent:
                raise ValueError(
                    f"Dataset {split} file is outside the frozen dataset directory: {path}"
                )
            entry = expected_files.get(path.name)
            if not isinstance(entry, dict) or not entry.get("sha256"):
                raise ValueError(f"No checksum for {path.name} in {manifest_path}")
            actual_hash = sha256_file(path)
            if actual_hash.lower() != str(entry["sha256"]).lower():
                raise ValueError(
                    f"Dataset checksum mismatch for {path}. "
                    "Do not mix artifacts from different preprocessing runs."
                )
        self._status(
            f"Dataset contract verified: {data.dataset_id} "
            f"(split seed={manifest.get('split_contract', {}).get('seed', 'unknown')})"
        )

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
        started = time.perf_counter()
        self._validate_dataset_contract()
        self._validate_audit_output_state()
        self._ensure_output_layout()
        self._status(f"Starting token audit: {self.config.run_name}")
        self._status(f"Loading tokenizer: {self.config.model_name}")
        tokenizer = self.factory.load_tokenizer()
        payload: dict[str, Any] = {
            "run_name": self.config.run_name,
            "model_name": self.config.model_name,
            "direction": self.config.direction,
        }
        if self.config.data.train_file:
            self._status("Auditing tokenizer lengths on the training split...")
            train = self._prepare_records(
                tokenizer, self._load_records("train"), "train"
            )
            payload["train"] = train.audit.to_dict()
            self._status(
                f"Training audit complete: retained {train.audit.retained}/{train.audit.total} records"
            )
        self._status("Auditing tokenizer lengths on the validation split...")
        validation = self._prepare_records(
            tokenizer, self._load_records("validation"), "validation"
        )
        payload["validation"] = validation.audit.to_dict()
        write_json(self.reports_dir / "token_audit_summary.json", payload)
        self._status(
            "Token audit completed in "
            f"{time.perf_counter() - started:.1f}s; retained "
            f"{validation.audit.retained}/{validation.audit.total} validation records"
        )
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

    @staticmethod
    def _training_plan(
        config: ExperimentConfig, train_size: int, validation_size: int
    ) -> dict[str, Any]:
        train = config.training
        micro_batches = math.ceil(train_size / train.per_device_train_batch_size)
        updates_per_epoch = math.ceil(
            micro_batches / train.gradient_accumulation_steps
        )
        total_updates = math.ceil(updates_per_epoch * train.epochs)
        if train.eval_strategy == "epoch":
            evaluation_runs = math.ceil(train.epochs)
        elif train.eval_strategy == "steps":
            evaluation_runs = total_updates // train.eval_steps
        else:
            evaluation_runs = 0
        return {
            "training_records": train_size,
            "validation_records": validation_size,
            "epochs": train.epochs,
            "micro_batches_per_epoch": micro_batches,
            "optimizer_updates_per_epoch": updates_per_epoch,
            "planned_optimizer_updates": total_updates,
            "effective_batch_size_one_gpu": (
                train.per_device_train_batch_size
                * train.gradient_accumulation_steps
            ),
            "evaluation_runs_during_training": evaluation_runs,
            "planned_generated_validation_records_during_training": (
                evaluation_runs * validation_size
            ),
            "warmup_steps": BaselineRunner._warmup_steps(config, train_size),
        }

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
            disable_tqdm=False,
            logging_first_step=True,
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

    def verify_saved_model(self) -> dict[str, Any]:
        """Reload a saved full model/LoRA adapter and generate one translation."""
        if self.config.training.mode == "none":
            raise ValueError("There is no saved model in zero-shot mode")
        self._validate_dataset_contract()
        torch = self._check_hardware()
        if not self.best_model_dir.is_dir():
            raise FileNotFoundError(
                f"Saved model not found: {self.best_model_dir}. Run train first."
            )
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, set_seed

        set_seed(self.config.seed)
        self._status(f"Reloading saved {self.config.training.mode} model...")
        tokenizer = AutoTokenizer.from_pretrained(
            self.best_model_dir,
            trust_remote_code=self.config.trust_remote_code,
            use_fast=True,
        )
        if self.config.training.mode == "lora":
            try:
                from peft import PeftModel
            except ImportError as error:
                raise RuntimeError("PEFT is required to reload a LoRA adapter") from error
            base_model = AutoModelForSeq2SeqLM.from_pretrained(
                self.config.model_name,
                revision=self.config.model_revision,
                trust_remote_code=self.config.trust_remote_code,
                low_cpu_mem_usage=True,
            )
            model = PeftModel.from_pretrained(base_model, self.best_model_dir)
        else:
            model = AutoModelForSeq2SeqLM.from_pretrained(
                self.best_model_dir,
                trust_remote_code=self.config.trust_remote_code,
                low_cpu_mem_usage=True,
            )

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
        record = self._load_records("validation")[0]
        inputs = tokenizer(
            record.source,
            return_tensors="pt",
            max_length=self.config.data.max_source_length,
            truncation=True,
        )
        inputs = {name: value.to(device) for name, value in inputs.items()}
        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_length=self.config.generation.max_length,
                num_beams=self.config.generation.num_beams,
                length_penalty=self.config.generation.length_penalty,
                no_repeat_ngram_size=self.config.generation.no_repeat_ngram_size,
                early_stopping=self.config.generation.early_stopping,
            )
        prediction = tokenizer.batch_decode(
            output_ids, skip_special_tokens=True
        )[0].strip()
        if not prediction:
            raise RuntimeError("Reloaded model generated an empty translation")
        report = {
            "status": "passed",
            "training_mode": self.config.training.mode,
            "seed": self.config.seed,
            "saved_model_dir": str(self.best_model_dir.resolve()),
            "segment_id": record.segment_id,
            "source": record.source,
            "prediction": prediction,
            "reference": record.target,
        }
        write_json(self.reports_dir / "reload_smoke.json", report)
        self._status("Saved model reload smoke test passed")
        return report

    def _run(self, *, do_train: bool) -> dict[str, Any]:
        started = time.perf_counter()
        self._validate_dataset_contract()
        self._validate_output_state(do_train=do_train)
        self._ensure_output_layout()
        action = "fine-tuning" if do_train else "zero-shot evaluation"
        self._status(f"Starting {action}: {self.config.run_name}")
        torch = self._check_hardware()
        from transformers import set_seed

        set_seed(self.config.seed)
        self._status(f"Loading tokenizer: {self.config.model_name}")
        tokenizer = self.factory.load_tokenizer()
        self._status("Loading and auditing the validation split...")
        validation = self._prepare_records(
            tokenizer, self._load_records("validation"), "validation"
        )
        self._status(
            f"Validation ready: retained {validation.audit.retained}/"
            f"{validation.audit.total} records"
        )
        train_corpus = None
        if do_train:
            self._status("Loading and auditing the training split...")
            train_corpus = self._prepare_records(
                tokenizer, self._load_records("train"), "train"
            )
            self._status(
                f"Training data ready: retained {train_corpus.audit.retained}/"
                f"{train_corpus.audit.total} records"
            )
            plan = self._training_plan(
                self.config, len(train_corpus.records), len(validation.records)
            )
            write_json(self.reports_dir / "training_plan.json", plan)
            self._status(
                "Training plan: "
                f"{plan['planned_optimizer_updates']} optimizer updates, "
                f"effective batch {plan['effective_batch_size_one_gpu']}, "
                f"{plan['evaluation_runs_during_training']} validation runs. "
                "Trainer's progress bar shows elapsed time and ETA."
            )

        self._status("Loading model weights; the first download may take several minutes...")
        model = self.factory.load_model()
        self._status("Model loaded; initializing Trainer...")
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
            self._status(
                f"Starting training on {len(train_corpus.records)} records. "
                "The progress bar reports steps, loss, and epoch."
            )
            result = trainer.train(
                resume_from_checkpoint=self.config.training.resume_from_checkpoint
            )
            train_metrics = dict(result.metrics)
            self._status(
                f"Training completed in {train_metrics.get('train_runtime', 0):.1f}s; "
                "saving the best model..."
            )
            trainer.save_model(str(self.best_model_dir))
            tokenizer.save_pretrained(str(self.best_model_dir))
            write_json(self.reports_dir / "train_metrics.json", train_metrics)

        if hasattr(trainer.model, "config"):
            trainer.model.config.use_cache = True
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
        self._status(
            f"Generating translations for {len(validation.records)} validation records. "
            "The progress bar reports completed batches."
        )
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
        self._status(
            f"Completed {action} in {time.perf_counter() - started:.1f}s. "
            f"Results: {self.output_dir.resolve()}"
        )
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
            "training_seed": self.config.seed,
            "dataset_id": self.config.data.dataset_id or None,
            "python": sys.version,
            "platform": platform.platform(),
            "gpu": gpu_name,
            "packages": packages,
            "generation_config": self.config.generation.__dict__,
            "metric_code_sha256": sha256_file(Path(__file__).with_name("metrics.py")),
            "data_files": self._data_manifest(),
            "train_metrics": train_metrics,
            "validation_metrics": validation_metrics,
        }

    def _data_manifest(self) -> dict[str, Any]:
        """Record exact input paths and hashes for comparable experiments."""
        result: dict[str, Any] = {}
        if self.config.data.manifest_file:
            manifest_path = Path(self.config.data.manifest_file)
            result["dataset_contract"] = {
                "dataset_id": self.config.data.dataset_id,
                "path": str(manifest_path),
                "sha256": sha256_file(manifest_path),
            }
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
