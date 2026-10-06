"""Generate and validate document-level competition prediction archives."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import time
from typing import Callable, Sequence
import zipfile

from .config import ExperimentConfig
from .pipeline.chunker import split_unit
from .pipeline.md_parser import mask_inline, parse_document
from .pipeline.promotion import file_hash, model_identity
from .pipeline.reassembler import coverage, escape_generated, reassemble
from .pipeline.report import code_version
from .pipeline.types import Candidate, TranslationUnit

DIRECTIONS = {"en-vi": "en2vi", "vi-en": "vi2en"}
CSV_COLUMNS = ["sample_id", "direction", "translation"]


@dataclass(frozen=True)
class TestDocument:
    sample_id: str
    direction: str
    source: str
    reference: str | None = None


def digest_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_csv(handle) -> tuple[list[str], list[dict]]:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            break
        except OverflowError:
            limit //= 10
    reader = csv.DictReader(handle, strict=True)
    columns = reader.fieldnames or []
    if len(columns) != len(set(columns)):
        raise ValueError("Duplicate CSV column names")
    rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("CSV rows have missing/extra fields; use standards-compliant quoting")
    return columns, rows


def load_test(path: Path, phase: str, source_column: str | None = None,
              *, expected_documents: int = 50) -> list[TestDocument]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        columns, rows = read_csv(handle)
    if "sample_id" not in columns or len(rows) != expected_documents:
        raise ValueError(f"Expected sample_id and exactly {expected_documents} source documents; found {len(rows)}")
    ids = [row["sample_id"] for row in rows]
    if any(not value.strip() for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Source sample_id must be nonempty, unchanged and unique")
    documents = []
    if phase == "public":
        if not {"english_markdown", "vietnamese_markdown"}.issubset(columns):
            raise ValueError("Public input requires english_markdown and vietnamese_markdown")
        for row in rows:
            documents.extend([
                TestDocument(row["sample_id"], "en-vi", row["english_markdown"], row["vietnamese_markdown"]),
                TestDocument(row["sample_id"], "vi-en", row["vietnamese_markdown"], row["english_markdown"]),
            ])
    elif phase == "private":
        if "direction" not in columns:
            raise ValueError("Private input requires its supplied direction column")
        if source_column is None:
            choices = [name for name in ("source", "source_markdown", "text", "markdown", "input") if name in columns]
            if len(choices) != 1:
                raise ValueError("Specify --source-column for this private-input schema")
            source_column = choices[0]
        if source_column not in columns:
            raise ValueError(f"Source column does not exist: {source_column}")
        for row in rows:
            if row["direction"] not in DIRECTIONS:
                raise ValueError(f"Invalid supplied direction: {row['direction']!r}; expected en-vi or vi-en")
            documents.append(TestDocument(row["sample_id"], row["direction"], row[source_column]))
    else:
        raise ValueError("phase must be public or private")
    if any(not document.source.strip() for document in documents):
        raise ValueError("The original test source contains an empty document")
    return documents


def validate_rows(rows: Sequence[dict], documents: Sequence[TestDocument]) -> dict:
    expected = {(d.sample_id, d.direction) for d in documents}
    if len(expected) != len(documents):
        raise ValueError("Duplicate required source ID/direction")
    actual = []
    for row in rows:
        if set(row) != set(CSV_COLUMNS):
            raise ValueError("Output must contain exactly sample_id,direction,translation")
        if row["direction"] not in DIRECTIONS:
            raise ValueError("Invalid prediction direction; use en-vi or vi-en")
        if not isinstance(row["translation"], str) or not row["translation"].strip():
            raise ValueError("Empty or non-text translation")
        if "\x00" in row["translation"]:
            raise ValueError("Translation contains a NUL byte")
        actual.append((row["sample_id"], row["direction"]))
    if len(actual) != len(set(actual)):
        raise ValueError("Duplicate prediction ID/direction")
    if set(actual) != expected or len(rows) != len(documents):
        raise ValueError(f"Prediction keys differ from phase input: missing={len(expected-set(actual))}, extra={len(set(actual)-expected)}")
    return {"status": "passed", "rows": len(rows), "unique_id_directions": len(expected),
            "directions": {d: sum(row["direction"] == d for row in rows) for d in DIRECTIONS}}


def validate_archive(path: Path, documents: Sequence[TestDocument]) -> dict:
    with zipfile.ZipFile(path) as archive:
        if archive.namelist() != ["results.csv"]:
            raise ValueError("The prediction ZIP must contain only results.csv at its root")
        if archive.testzip() is not None:
            raise ValueError("Corrupted prediction ZIP")
        text = archive.read("results.csv").decode("utf-8-sig")
    columns, rows = read_csv(io.StringIO(text, newline=""))
    if columns == ["sample_id", "direction", "prediction"]:
        rows = [{"sample_id": r["sample_id"], "direction": r["direction"], "translation": r["prediction"]} for r in rows]
    elif columns != CSV_COLUMNS:
        raise ValueError("Invalid results.csv header (extra index/metadata columns are forbidden)")
    return {**validate_rows(rows, documents), "zip_sha256": file_hash(path)}


def write_submission(rows: Sequence[dict], documents: Sequence[TestDocument], output: Path) -> dict:
    validate_rows(rows, documents)
    output.mkdir(parents=True, exist_ok=True)
    csv_path, zip_path = output / "results.csv", output / "submission.zip"
    if csv_path.exists() or zip_path.exists():
        raise FileExistsError("results.csv/submission.zip already exist; use a new output directory")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    payload = stream.getvalue().encode("utf-8")
    # The final filenames appear only after the archive has passed a read-back check.
    temporary = output / "submission.zip.tmp"
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("results.csv", payload)
    report = validate_archive(temporary, documents)
    csv_path.write_bytes(payload)
    temporary.replace(zip_path)
    (output / "submission.zip.sha256").write_text(report["zip_sha256"] + "  submission.zip\n", encoding="utf-8")
    return report


def official_metrics(rows: Sequence[dict], documents: Sequence[TestDocument]) -> dict:
    """Score complete documents, per direction, with equal-weight macro averaging."""
    validate_rows(rows, documents)
    if any(d.reference is None for d in documents):
        return {"status": "not_scored_no_private_references"}
    import sacrebleu
    lookup = {(row["sample_id"], row["direction"]): row["translation"] for row in rows}
    result = {}
    for direction in DIRECTIONS:
        subset = [d for d in documents if d.direction == direction]
        if not subset:
            continue
        hypotheses = [lookup[d.sample_id, d.direction] for d in subset]
        references = [d.reference for d in subset]
        bleu = sacrebleu.metrics.BLEU(tokenize="13a", smooth_method="exp")
        chrf = sacrebleu.metrics.CHRF(char_order=6, word_order=0, beta=2)
        result[direction] = {"documents": len(subset), "BLEU": bleu.corpus_score(hypotheses, [references]).score,
                             "chrF": chrf.corpus_score(hypotheses, [references]).score,
                             "signatures": {"BLEU": str(bleu.get_signature()), "chrF": str(chrf.get_signature())}}
    return {"status": "scored_full_documents", "sacrebleu_version": sacrebleu.__version__, "per_direction": result,
            "macro_average": {metric: sum(value[metric] for value in result.values()) / len(result) for metric in ("BLEU", "chrF")}}


def parse_legal_document(source: str, doc_id: str):
    document = parse_document(source, doc_id=doc_id)
    # Public legal headers use indentation for layout. Preserve that indentation
    # and translate the prose, rather than interpreting it as executable code.
    for block in document.blocks:
        if block["kind"] != "indented_code":
            continue
        raw = source[block["start"]:block["end"]].rstrip("\r\n")
        left, right = len(raw) - len(raw.lstrip(" \t")), len(raw.rstrip(" \t"))
        if right <= left:
            continue
        text = raw[left:right]
        masked, placeholders = mask_inline(text)
        document.units.append(TranslationUnit("", doc_id, 0, "indented_prose", raw[:left], text,
                                               masked, block["start"]+left, block["start"]+right, placeholders))
    document.units.sort(key=lambda u: u.start)
    for i, unit in enumerate(document.units):
        unit.order_index, unit.unit_id = i, f"{doc_id}:{i:05d}"
    if reassemble(document, identity=True) != source:
        raise ValueError("Source document round-trip failed")
    return document


def translate_document(source: str, doc_id: str, tokenizer, generate_many: Callable,
                       *, source_budget: int = 448, hard_budget: int = 1024) -> tuple[str, dict]:
    """Translate text spans; all original Markdown and inline syntax stays local."""
    started = time.perf_counter()
    document = parse_legal_document(source, doc_id)
    inputs, recipes = [], []
    for unit in document.units:
        originals = {p.token: p.original for p in unit.placeholders}
        pattern = "(" + "|".join(re.escape(t) for t in originals) + ")" if originals else None
        parts = re.split(pattern, unit.src_masked) if pattern else [unit.src_masked]
        recipe = []
        for part in parts:
            if part in originals:
                recipe.append(("literal", originals[part])); continue
            if not any(c.isalpha() for c in part):
                recipe.append(("literal", part)); continue
            left, right = len(part)-len(part.lstrip()), len(part.rstrip())
            recipe.append(("literal", part[:left]))
            pieces = split_unit(part[left:right], tokenizer, budget=source_budget, hard_budget=hard_budget)
            for piece in pieces:
                recipe.append(("literal", piece.separator_before))
                recipe.append(("prediction", len(inputs)))
                inputs.append(piece.text)
            recipe.append(("literal", part[right:]))
        recipes.append(recipe)
    outputs = generate_many(inputs) if inputs else []
    if len(outputs) != len(inputs):
        raise ValueError("Model output count differs from source text span count")
    selected, repaired, diagnostics = [], 0, []
    for text, values in zip(inputs, outputs, strict=True):
        if len(values) != 1:
            raise ValueError("Submission generation must return exactly one candidate per span")
        candidate = values[0]
        if candidate.reached_token_cap or not candidate.text.strip():
            smaller = split_unit(text, tokenizer, budget=max(1, source_budget//2), hard_budget=hard_budget)
            if len(smaller) < 2:
                raise RuntimeError(f"Empty/capped indivisible span in {doc_id}; no prediction archive was produced")
            retried = generate_many([p.text for p in smaller])
            if len(retried) != len(smaller) or any(len(v)!=1 or not v[0].text.strip() or v[0].reached_token_cap for v in retried):
                raise RuntimeError(f"Split retry still empty/capped in {doc_id}; inspect that document")
            candidate = Candidate("".join(p.separator_before+v[0].text for p,v in zip(smaller,retried,strict=True)),
                                  strategy="split_after_cap", provenance={"pieces": [asdict(v[0]) for v in retried]})
            repaired += 1
        diagnostics.append({"source_tokens": len(tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"]),
                            "candidate": asdict(candidate)})
        selected.append(escape_generated(re.sub(r"[\r\n]+", " ", candidate.text.strip()), []))
    for unit, recipe in zip(document.units, recipes, strict=True):
        text = "".join(value if kind=="literal" else selected[value] for kind,value in recipe)
        unit.final = Candidate(text, strategy="source_offset_layout", restored=True)
    output = reassemble(document)
    invariants = coverage(document)
    if not output.strip() or not invariants["round_trip"] or invariants["final_units"] != invariants["source_units"]:
        raise RuntimeError("Document coverage/empty-output check failed")
    return output, {"units": len(document.units), "translated_spans": len(inputs), "split_after_cap": repaired,
                    "invariants": invariants, "layout": "source_offset; inline spans translated independently",
                    "static_blocks": [b for b in document.blocks if b["kind"] in {"code", "html", "front_matter"}],
                    "runtime_seconds": time.perf_counter()-started, "generation": diagnostics}


def checked_snapshot(path: Path, config: ExperimentConfig) -> dict:
    path = path.resolve()
    manifest = json.loads((path / "offline_model_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("repo_id") != config.model_name or manifest.get("revision") != config.model_revision:
        raise ValueError("Wrong offline base model/revision")
    if not manifest.get("files"):
        raise ValueError("Offline base manifest contains no checksums")
    for relative, metadata in manifest["files"].items():
        actual = (path / relative).resolve()
        if not actual.is_relative_to(path) or not actual.is_file() or actual.stat().st_size != metadata["bytes"]:
            raise ValueError(f"Unsafe/missing/incomplete offline model file: {relative}")
        if file_hash(actual) != metadata["sha256"]:
            raise ValueError(f"Offline model checksum mismatch: {relative}")
    return manifest


class FrozenGenerator:
    """Existing deterministic generation wrapper, with fixed official decoding."""
    def __init__(self, tokenizer, model, config, identity, device, batch_size):
        from types import SimpleNamespace
        from .pipeline.translator import ModelTranslator
        settings = {"seed": config.seed, "features": {"new_decoding": False, "dynamic_length": False, "cache": True},
                    "runtime": {"cublas_workspace_config": ":4096:8"}, "chunker": {"hard_budget": 1024},
                    "translator": {"candidate_decoding": {}, "model_identity": identity, "batch_size": batch_size},
                    "glossary": {"version": "not_used"}}
        self.tokenizer, self.batch_size = tokenizer, batch_size
        self.translator = ModelTranslator(tokenizer, model, config, SimpleNamespace(values=settings, hash=digest_json(settings)), device)

    def __call__(self, texts):
        from .inference import token_length
        order = sorted(range(len(texts)), key=lambda i: token_length(self.tokenizer, texts[i]))
        results = [None] * len(texts)
        batches = (len(order)+self.batch_size-1)//self.batch_size
        for start in range(0, len(order), self.batch_size):
            indices = order[start:start+self.batch_size]
            outputs = self.translator.generate_many([texts[i] for i in indices])
            for i, value in zip(indices, outputs, strict=True): results[i] = value
            batch = start//self.batch_size+1
            if batch == 1 or batch % 20 == 0 or batch == batches:
                print(f"GENERATE {batch}/{batches} batches", flush=True)
        return results


def build(args):
    import gc
    import importlib.metadata
    import os
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                      TOKENIZERS_PARALLELISM="false", CUBLAS_WORKSPACE_CONFIG=":4096:8")
    import torch
    from .inference import load_inference_model
    documents = load_test(args.input, args.phase, args.source_column, expected_documents=50 if args.phase=="public" else 100)
    if args.batch_size < 1 or not 32 <= args.maximum_source_tokens <= 512:
        raise ValueError("batch-size must be positive; source budget must be in [32,512]")
    if not torch.cuda.is_available() and not args.allow_cpu:
        raise RuntimeError("GPU is required for full test generation; --allow-cpu is for a small explicit smoke")
    if args.smoke_documents is not None and args.smoke_documents < 1:
        raise ValueError("smoke-documents must be positive")
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise FileExistsError("Use a new output directory or --resume for the exact same run")
    if (output/"submission.zip").exists() or (output/"results.csv").exists():
        raise FileExistsError("This run already produced its submission; do not overwrite")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    models, identities = {}, {}
    for direction in DIRECTIONS:
        if not any(d.direction == direction for d in documents): continue
        internal = DIRECTIONS[direction]
        config_path, adapter = getattr(args, internal+"_config"), getattr(args, internal+"_model")
        if adapter is None: raise ValueError(f"--{internal}-model is required for this phase")
        config = ExperimentConfig.from_json(config_path)
        if config.direction != internal: raise ValueError("Model/config direction mismatch")
        base = None
        if (adapter/"adapter_config.json").is_file():
            variable = f"VINAI_{internal.upper()}_MODEL_DIR"
            if not os.environ.get(variable): raise ValueError(f"Set {variable} to the offline base snapshot")
            print(f"Verifying {internal} offline base checksums...", flush=True)
            base = checked_snapshot(Path(os.environ[variable]), config)
        identity = {"model": model_identity(config, adapter), "base_snapshot": base,
                    "generation": asdict(config.generation), "seed": config.seed, "config_sha256": file_hash(config_path)}
        models[direction] = config, adapter
        identities[direction] = identity
    provenance = {"schema_version": 1, "phase": args.phase, "input_sha256": file_hash(args.input), "source_column": args.source_column,
                  "code_sha256": code_version(), "models": identities, "batch_size": args.batch_size,
                  "source_budget": args.maximum_source_tokens, "smoke_documents": args.smoke_documents,
                  "layout": "source_offset_inline_spans_v1", "device": str(device),
                  "packages": {p: importlib.metadata.version(p) for p in ("torch", "transformers", "peft", "sacrebleu")}}
    signature = digest_json(provenance)
    manifest_path = output/"run_manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old.get("request_sha256") != signature: raise ValueError("Cannot resume with different input/model/config/code/packages/settings")
    elif output.exists() and any(output.iterdir()):
        raise ValueError("Resume output has no matching run manifest")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"request_sha256": signature, **provenance}, indent=2), encoding="utf-8")
    records, reports = {}, {}
    for direction, (config, adapter) in models.items():
        needed = [d for d in documents if d.direction == direction]
        if args.smoke_documents is not None: needed = needed[:args.smoke_documents]
        generator = tokenizer = model = None
        try:
            for index, document in enumerate(needed, 1):
                key = digest_json([document.sample_id, document.direction])
                saved = output/"documents"/(key+".json")
                request = digest_json([signature, document.sample_id, document.direction, document.source])
                if saved.exists():
                    artifact = json.loads(saved.read_text(encoding="utf-8"))
                    if artifact.get("request_sha256") != request or artifact.get("translation_sha256") != hashlib.sha256(artifact["row"]["translation"].encode()).hexdigest():
                        raise ValueError("Cached document provenance/content does not match")
                    validate_rows([artifact["row"]], [document])
                    row, report = artifact["row"], artifact["report"]
                    print(f"RESUME {direction} {index}/{len(needed)} {document.sample_id}", flush=True)
                else:
                    if generator is None:
                        tokenizer, model = load_inference_model(config, saved_model_dir=adapter)
                        dtype = torch.float16 if device.type=="cuda" and config.training.fp16 else torch.bfloat16 if device.type=="cuda" and config.training.bf16 else torch.float32
                        model.to(device=device, dtype=dtype)
                        generator = FrozenGenerator(tokenizer, model, config, identities[direction], device, args.batch_size)
                    print(f"DOCUMENT {direction} {index}/{len(needed)} {document.sample_id}", flush=True)
                    translated, report = translate_document(document.source, document.sample_id, tokenizer, generator, source_budget=args.maximum_source_tokens)
                    row = {"sample_id": document.sample_id, "direction": document.direction, "translation": translated}
                    validate_rows([row], [document])
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    artifact = {"request_sha256": request, "translation_sha256": hashlib.sha256(translated.encode()).hexdigest(), "row": row, "report": report}
                    temporary = saved.with_suffix(".json.tmp")
                    temporary.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
                    temporary.replace(saved)
                    print(f"SAVED {direction} {index}/{len(needed)} | {report['runtime_seconds']:.1f}s", flush=True)
                records[document.sample_id, direction] = row
                reports[document.sample_id, direction] = report
        finally:
            del generator, tokenizer, model
            gc.collect()
            if torch.cuda.is_available(): torch.cuda.empty_cache()
    if args.smoke_documents is not None:
        summary = {"status": "smoke_only_no_submission", "documents": len(records), "reports": list(reports.values())}
        (output/"smoke_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print("SMOKE passed; no results.csv/submission.zip was created", flush=True)
        return summary
    rows = [records[d.sample_id, d.direction] for d in documents]
    validation = validate_rows(rows, documents)
    metrics = official_metrics(rows, documents)
    (output/"evaluation_report.json").write_text(json.dumps({"validation": validation, "metrics": metrics,
        "note": "Full original test documents; public scores are final reporting, not tuning evidence",
        "request_sha256": signature}, ensure_ascii=False, indent=2), encoding="utf-8")
    archive_report = write_submission(rows, documents, output)
    print(json.dumps({"submission": str(output/"submission.zip"), **archive_report, "metrics": metrics}, ensure_ascii=False), flush=True)
    return archive_report
