"""Offline document translation with deterministic token-aware chunking."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .config import ExperimentConfig
from .modeling import VinAIModelFactory, offline_mode


BLANK_LINES_RE = re.compile(r"(\n[\t ]*\n+)")
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?;:])\s+")


@dataclass(frozen=True)
class DocumentChunk:
    index: int
    source: str
    separator_before: str
    separator_after: str
    source_tokens: int


def token_length(tokenizer: Any, text: str) -> int:
    return len(
        tokenizer(
            text,
            add_special_tokens=True,
            truncation=False,
            padding=False,
            verbose=False,
        )["input_ids"]
    )


def _greedy_pack(
    units: Sequence[str], tokenizer: Any, maximum_tokens: int
) -> list[str]:
    packed: list[str] = []
    current = ""
    for unit in units:
        candidate = unit if not current else f"{current} {unit}"
        if token_length(tokenizer, candidate) <= maximum_tokens:
            current = candidate
            continue
        if current:
            packed.append(current)
            current = ""
        if token_length(tokenizer, unit) <= maximum_tokens:
            current = unit
            continue
        # Last-resort word packing keeps every source token exactly once while
        # avoiding tokenizer truncation. This is intentionally deterministic.
        words = unit.split()
        word_chunk = ""
        for word in words:
            candidate = word if not word_chunk else f"{word_chunk} {word}"
            if token_length(tokenizer, candidate) <= maximum_tokens:
                word_chunk = candidate
            else:
                if not word_chunk:
                    raise ValueError(
                        "A single source token exceeds the document token budget"
                    )
                packed.append(word_chunk)
                word_chunk = word
        if word_chunk:
            current = word_chunk
    if current:
        packed.append(current)
    return packed


def split_markdown_document(
    text: str, tokenizer: Any, maximum_tokens: int
) -> list[DocumentChunk]:
    """Split Markdown on blank lines, then sentence/word boundaries if required."""

    if maximum_tokens < 32:
        raise ValueError("maximum_tokens must be at least 32")
    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
    pieces = BLANK_LINES_RE.split(normalized)
    chunks: list[DocumentChunk] = []
    pending_separator = ""
    for piece in pieces:
        if not piece:
            continue
        if BLANK_LINES_RE.fullmatch(piece):
            if chunks:
                last = chunks[-1]
                chunks[-1] = DocumentChunk(
                    index=last.index,
                    source=last.source,
                    separator_before=last.separator_before,
                    separator_after=last.separator_after + piece,
                    source_tokens=last.source_tokens,
                )
            else:
                pending_separator += piece
            continue
        if not piece.strip():
            continue
        paragraph = piece
        if token_length(tokenizer, paragraph) <= maximum_tokens:
            subchunks = [paragraph]
        else:
            sentences = [
                sentence.strip()
                for sentence in SENTENCE_BOUNDARY_RE.split(paragraph)
                if sentence.strip()
            ]
            subchunks = _greedy_pack(sentences, tokenizer, maximum_tokens)
        for sub_index, subchunk in enumerate(subchunks):
            chunks.append(
                DocumentChunk(
                    index=len(chunks),
                    source=subchunk,
                    separator_before=(pending_separator if sub_index == 0 else ""),
                    separator_after=" " if sub_index < len(subchunks) - 1 else "",
                    source_tokens=token_length(tokenizer, subchunk),
                )
            )
        pending_separator = ""
    if not chunks:
        raise ValueError("The input document is empty")
    return chunks


def load_inference_model(
    config: ExperimentConfig,
    *,
    saved_model_dir: str | Path | None = None,
    merge_lora: bool = False,
) -> tuple[Any, Any]:
    """Load zero-shot, LoRA adapter, or full model for offline inference."""

    factory = VinAIModelFactory(config)
    saved = Path(saved_model_dir) if saved_model_dir else None
    if config.training.mode == "none":
        tokenizer = factory.load_tokenizer()
        model = factory.load_model(apply_lora=False, for_inference=True)
    elif saved is None or not saved.is_dir():
        raise FileNotFoundError(
            "saved_model_dir is required for LoRA/full document inference"
        )
    elif config.training.mode == "lora":
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        tokenizer = factory.load_tokenizer(saved)
        if (saved / "adapter_config.json").is_file():
            adapter_metadata = json.loads((saved / "adapter_config.json").read_text(encoding="utf-8"))
            if adapter_metadata.get("base_model_name_or_path") != config.model_name:
                raise ValueError("Adapter base model/direction does not match the selected config")
            if adapter_metadata.get("revision") not in (None, config.model_revision):
                raise ValueError("Adapter base-model revision does not match config")
            try:
                from peft import PeftModel
            except ImportError as error:
                raise RuntimeError("PEFT is required for LoRA inference") from error
            base_model = factory.load_model(apply_lora=False, for_inference=True)
            model = PeftModel.from_pretrained(base_model, saved)
            if merge_lora:
                model = model.merge_and_unload(safe_merge=True)
        elif (saved / "config.json").is_file():
            if merge_lora:
                raise ValueError(
                    "saved_model_dir is already a merged/full model; remove --merge-lora"
                )
            manifest_path = saved / "merge_manifest.json"
            if manifest_path.is_file():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                expected = (
                    config.model_name,
                    config.model_revision,
                    config.direction,
                )
                actual = (
                    manifest.get("base_model"),
                    manifest.get("base_model_revision"),
                    manifest.get("direction"),
                )
                if actual != expected:
                    raise ValueError(
                        "Merged model manifest does not match config "
                        f"(expected {expected}, got {actual})"
                    )
            model = AutoModelForSeq2SeqLM.from_pretrained(
                saved,
                trust_remote_code=config.trust_remote_code,
                low_cpu_mem_usage=True,
                local_files_only=offline_mode(),
            )
        else:
            raise FileNotFoundError(
                f"No LoRA adapter or merged model config found in {saved}"
            )
    else:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        tokenizer = factory.load_tokenizer(saved)
        model = AutoModelForSeq2SeqLM.from_pretrained(
            saved,
            trust_remote_code=config.trust_remote_code,
            low_cpu_mem_usage=True,
            local_files_only=offline_mode(),
        )
    from .language import configure_model
    configure_model(model, tokenizer, config.direction)
    model.config.use_cache = True
    return tokenizer, model


def _batches(values: Sequence[int], batch_size: int) -> Iterable[Sequence[int]]:
    for start in range(0, len(values), batch_size):
        yield values[start : start + batch_size]


def translate_chunks(
    chunks: Sequence[DocumentChunk],
    *,
    tokenizer: Any,
    model: Any,
    config: ExperimentConfig,
    batch_size: int,
    device: Any,
    fail_on_empty: bool = True,
    log_progress: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    """Translate length-bucketed chunks and restore their original order."""

    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    import torch

    order = sorted(range(len(chunks)), key=lambda index: chunks[index].source_tokens)
    predictions = [""] * len(chunks)
    generation = config.generation
    started = time.perf_counter()
    model.to(device)
    model.eval()
    total_batches = (len(order) + batch_size - 1) // batch_size
    for batch_index, indices in enumerate(_batches(order, batch_size), start=1):
        texts = [chunks[index].source for index in indices]
        inputs = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=False,
            pad_to_multiple_of=8,
        )
        inputs = {name: value.to(device) for name, value in inputs.items()}
        generation_kwargs = {
            "num_beams": generation.num_beams,
            "length_penalty": generation.length_penalty,
            "repetition_penalty": generation.repetition_penalty,
            "no_repeat_ngram_size": generation.no_repeat_ngram_size,
            "early_stopping": generation.early_stopping,
            "renormalize_logits": generation.renormalize_logits,
        }
        if generation.max_new_tokens is not None:
            generation_kwargs["max_new_tokens"] = generation.max_new_tokens
        else:
            generation_kwargs["max_length"] = generation.max_length
        with torch.inference_mode():
            output_ids = model.generate(**inputs, **generation_kwargs)
        decoded = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
        for index, prediction in zip(indices, decoded, strict=True):
            predictions[index] = prediction.strip()
        if log_progress:
            elapsed = time.perf_counter() - started
            eta = elapsed / batch_index * (total_batches - batch_index)
            print(f"GENERATE {batch_index}/{total_batches} batches | elapsed {elapsed:.0f}s | ETA {eta:.0f}s", flush=True)
    if fail_on_empty and any(not prediction for prediction in predictions):
        empty = [index for index, value in enumerate(predictions) if not value]
        raise RuntimeError(f"Empty translations for chunks: {empty[:10]}")
    report = {
        "direction": config.direction,
        "training_mode": config.training.mode,
        "chunks": len(chunks),
        "batch_size": batch_size,
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "maximum_source_tokens": max(chunk.source_tokens for chunk in chunks),
        "generation": asdict(generation),
    }
    return predictions, report


def assemble_document(
    chunks: Sequence[DocumentChunk], predictions: Sequence[str]
) -> str:
    if len(chunks) != len(predictions):
        raise ValueError("Chunk/prediction counts differ")
    assembled = "".join(
        chunk.separator_before + prediction + chunk.separator_after
        for chunk, prediction in zip(chunks, predictions, strict=True)
    )
    return assembled.rstrip("\n") + "\n"


MARKDOWN_PATTERNS = {
    "headings": re.compile(r"(?m)^\s{0,3}#{1,6}\s+"),
    "unordered_list_items": re.compile(r"(?m)^\s{0,3}[-+*]\s+"),
    "ordered_list_items": re.compile(r"(?m)^\s{0,3}\d+[.)]\s+"),
    "blockquotes": re.compile(r"(?m)^\s{0,3}>\s?"),
    "fenced_code_markers": re.compile(r"(?m)^\s{0,3}(?:```|~~~)"),
    "markdown_links": re.compile(r"\[[^\]\n]+\]\([^\)\n]+\)"),
    "tables": re.compile(r"(?m)^\s*\|.*\|\s*$"),
}


def markdown_structure_report(source: str, output: str) -> dict[str, Any]:
    """Compare high-signal Markdown marker counts without changing the translation."""

    source_counts = {
        name: len(pattern.findall(source))
        for name, pattern in MARKDOWN_PATTERNS.items()
    }
    output_counts = {
        name: len(pattern.findall(output))
        for name, pattern in MARKDOWN_PATTERNS.items()
    }
    mismatches = {
        name: {"source": source_counts[name], "output": output_counts[name]}
        for name in source_counts
        if source_counts[name] != output_counts[name]
    }
    return {
        "source_counts": source_counts,
        "output_counts": output_counts,
        "structure_counts_match": not mismatches,
        "mismatches": mismatches,
    }
