"""Require evaluation evidence for the exact immutable deployment artifacts."""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from .report import code_version


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): digest.update(block)
    return digest.hexdigest()


def model_identity(experiment,adapter):
    adapter=Path(adapter)
    weights=[adapter/"adapter_model.safetensors"] if (adapter/"adapter_model.safetensors").is_file() else sorted(adapter.glob("model*.safetensors"))
    if not weights: raise FileNotFoundError("No immutable adapter/merged weights found")
    return {"base":experiment.model_name,"revision":experiment.model_revision,"weights":{p.name:file_hash(p) for p in weights}}


def behavior_hash(config):
    values=json.loads(json.dumps(config.values))
    for section in ("promotion","evaluation","calibration"): values.pop(section,None)
    values["features"].pop("enabled",None)
    for key in ("reports_directory","structured_logs"): values["runtime"].pop(key,None)
    values["translator"].pop("model_identity",None)
    for key in ("version","file"): values["glossary"].pop(key,None)
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()


def verify_promotion(config,experiment,adapter):
    promotion=config.values["promotion"]
    if not promotion["approved"] or not promotion["evidence"]: raise ValueError("Pipeline promotion requires completed evaluation evidence")
    report=json.loads(config.resource(promotion["evidence"]).read_text(encoding="utf-8"))
    expected={"model_identity":model_identity(experiment,adapter),"generation":asdict(experiment.generation),"behavior_sha256":behavior_hash(config),"code_sha256":code_version(),"glossary_sha256":file_hash(config.resource(config.values["glossary"]["file"]))}
    if report.get("status")!="passed" or any(report.get(k)!=v for k,v in expected.items()): raise ValueError("Promotion evidence does not match current model/code/config/glossary")
    if config.values["runtime"]["time_budget_per_doc"] is None: raise ValueError("Submission time budget has not been declared")
    return report
