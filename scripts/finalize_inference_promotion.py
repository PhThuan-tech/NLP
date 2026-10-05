"""Finalize a reviewed full-dev result after an exact-model deployment GPU smoke."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.vinai_baseline.config import ExperimentConfig
from src.vinai_baseline.pipeline.config import PipelineConfig
from src.vinai_baseline.pipeline.promotion import behavior_hash, file_hash, model_identity
from src.vinai_baseline.pipeline.report import code_version


def finalize(evaluation_dir,config,experiment,model_dir,deployment_report,output,placeholder_report=None):
    evidence=json.loads((evaluation_dir/"promotion_evidence.json").read_text(encoding="utf-8"))
    summaries=json.loads((evaluation_dir/"ablation.json").read_text(encoding="utf-8"))
    subset=json.loads((evaluation_dir/"subset.json").read_text(encoding="utf-8"))
    review=json.loads((evaluation_dir/"manual_review.json").read_text(encoding="utf-8"))
    expected={"model_identity":model_identity(experiment,model_dir),"generation":asdict(experiment.generation),"behavior_sha256":behavior_hash(config),"code_sha256":code_version(),"glossary_sha256":file_hash(config.resource(config.values["glossary"]["file"])),"dev_sha256":config.values["evaluation"]["fixed_dev_sha256"]}
    if any(evidence.get(k)!=v for k,v in expected.items()): raise ValueError("Evaluation artifacts differ from current model/config/code/glossary/dev")
    if [r["name"] for r in summaries]!=[f"R{i}" for i in range(6)]: raise ValueError("Complete R0–R5 results are required")
    if subset.get("limit") or any(r["records"]!=len(subset["record_ids"]) or r.get("code_changed_during_run") for r in summaries): raise ValueError("Partial or inconsistent evaluation cannot be promoted")
    if evidence["records"]!=len(subset["record_ids"]): raise ValueError("Not all fixed-dev records were evaluated")
    # Review IDs must match the deterministic 30-unit sample, with explicit verdicts.
    import random
    indices=random.Random(config.values["seed"]).sample(range(len(subset["record_ids"])),min(len(subset["record_ids"]),config.values["evaluation"]["manual_review_records"]))
    expected_ids={subset["record_ids"][i] for i in indices}
    if {r["segment_id"] for r in review["units"]}!=expected_ids or len(review["units"])!=len(expected_ids) or any(r["verdict"]!="approved" for r in review["units"]): raise ValueError("Every fixed manual-review sample requires user approval")
    base,final=summaries[0],summaries[-1]; budget=config.values["runtime"]["time_budget_per_doc"]
    if final["round_trip_rate"]!=100 or final["structure_preservation_rate"]!=100 or final.get("unit_coverage_rate")!=100 or final.get("source_kept",0) or final.get("fallback_documents",0): raise ValueError("Structural/source-coverage gate failed")
    if final["metrics"]["chrF++"]<base["metrics"]["chrF++"]-config.values["evaluation"]["allowed_chrf_drop"] or final["metrics"]["BLEU"]<base["metrics"]["BLEU"]-config.values["evaluation"]["allowed_bleu_drop"]: raise ValueError("Full-dev metric regression")
    if budget is None or final["max_document_seconds"]>budget: raise ValueError("Declared document runtime budget is required and must be met")
    if config.values["features"]["inline_placeholders"]:
        if placeholder_report is None:
            raise ValueError("Real fixed-dev placeholder survival evidence remains required")
        survival=json.loads(placeholder_report.read_text(encoding="utf-8"))
        if survival.get("status")!="measured" or any(survival.get(k)!=expected[k] for k in ("model_identity","generation","code_sha256","behavior_sha256","dev_sha256")):
            raise ValueError("Placeholder survival evidence is incomplete or uses different artifacts")
        chosen=[r for r in survival.get("results",[]) if r.get("format")==config.values["parser"]["placeholder_format"]]
        if len(chosen)!=1 or chosen[0].get("samples",0)<config.values["evaluation"]["placeholder_samples"] or survival.get("selected")!=chosen[0]["format"]:
            raise ValueError("The selected placeholder format needs the required real-dev sample count")
    smoke=json.loads(deployment_report.read_text(encoding="utf-8"))
    if not smoke.get("environment",{}).get("device","").startswith("cuda") or smoke.get("fallback") or not smoke.get("invariants",{}).get("structure_preserved") or not smoke.get("invariants",{}).get("unit_coverage") or smoke.get("summary",{}).get("units",0)<1 or smoke.get("summary",{}).get("SOURCE_KEPT",0): raise ValueError("A passing real deployment GPU document smoke is required")
    versions=smoke.get("versions",{})
    for key in ("model_identity","code_sha256","glossary_sha256","behavior_sha256"):
        if versions.get(key)!=expected[key]: raise ValueError("Deployment smoke uses different artifacts")
    if smoke.get("generation")!=expected["generation"]:
        raise ValueError("Deployment smoke uses different generation parameters")
    if smoke.get("runtime",{}).get("stages_seconds",{}).get("total",float("inf"))>budget:
        raise ValueError("Deployment smoke exceeds the declared document runtime budget")
    output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()): raise FileExistsError("Use an empty promotion output directory")
    evidence.update(status="passed",reasons=[],manual_review_sha256=file_hash(evaluation_dir/"manual_review.json"),deployment_report_sha256=file_hash(deployment_report),placeholder_report_sha256=file_hash(placeholder_report) if placeholder_report else None)
    evidence_path=output/"promotion_approved.json"; evidence_path.write_text(json.dumps(evidence,indent=2),encoding="utf-8")
    approved=config.copy(); approved.values["features"]["enabled"]=True; approved.values["evaluation"]["experimental"]=False; approved.values["promotion"]={"approved":True,"evidence":str(evidence_path.resolve())}
    approved.values["glossary"]["file"]=str(config.resource(config.values["glossary"]["file"]))
    approved.validate(); (output/"approved_pipeline.json").write_text(json.dumps(approved.values,indent=2),encoding="utf-8")
    return evidence


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ("evaluation-dir","pipeline-config","experiment-config","model-dir","deployment-report","output"): parser.add_argument("--"+flag,type=Path,required=True)
    parser.add_argument("--placeholder-report",type=Path,help="Required when inline placeholders are enabled; actual fixed-dev model survival report")
    args=parser.parse_args()
    result=finalize(args.evaluation_dir,PipelineConfig.load(args.pipeline_config,environment=False),ExperimentConfig.from_json(args.experiment_config),args.model_dir,args.deployment_report,args.output,args.placeholder_report)
    print(json.dumps({"status":result["status"],"output":str(args.output)}))


if __name__=="__main__": main()
