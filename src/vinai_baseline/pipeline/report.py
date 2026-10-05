"""Document reports on disk; structured runtime logs contain no document text."""
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path


def code_version():
    root=Path(__file__).resolve().parents[1]; digest=hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode()); digest.update(path.read_bytes())
    return digest.hexdigest()


def build_report(document,config,glossary_version,stages,invariants,*,retry_skipped=False):
    from .promotion import behavior_hash
    from .validator import penalty
    statuses=Counter(u.status for u in document.units)
    units=[]
    for unit in document.units:
        value=asdict(unit)
        for candidate,serialized in zip(unit.translations,value["translations"],strict=True):
            serialized["penalty"]=penalty(candidate,config.values["validator"]["weights"])
        if unit.final is not None: value["final"]["penalty"]=penalty(unit.final,config.values["validator"]["weights"])
        units.append(value)
    return {"schema_version":1,"doc_id":document.doc_id,"chunks":len(document.units),"summary":{"units":len(document.units),**{status:statuses[status] for status in ("OK","RETRIED_FIXED","RETRIED_UNFIXED","SOURCE_KEPT")}},"invariants":invariants,"units":units,"runtime":{"stages_seconds":stages,"retry_skipped_budget":retry_skipped,"time_budget_per_doc":config.values["runtime"]["time_budget_per_doc"]},"versions":{"config_sha256":config.hash,"behavior_sha256":behavior_hash(config),"glossary_sha256":glossary_version,"code_sha256":code_version(),"seed":config.values["seed"],"model_identity":config.values["translator"]["model_identity"]},"fallback":False}


def write_report(path,report):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    md=path.with_suffix(".md")
    lines=["# Document translation report","",f"Document: `{report.get('doc_id','unknown')}`",f"Fallback: {report.get('fallback',False)}","","## Summary","","```json",json.dumps(report.get("summary",{}),ensure_ascii=False,indent=2),"```","","## Invariants","","```json",json.dumps(report.get("invariants",{}),ensure_ascii=False,indent=2),"```","","## Runtime and versions","","```json",json.dumps({"runtime":report.get("runtime"),"versions":report.get("versions")},ensure_ascii=False,indent=2),"```","","## Units with checks or retries",""]
    for unit in report.get("units",[]):
        final=unit.get("final") or {}; checks=final.get("checks",[])
        if not checks and unit["status"]=="OK" and not unit.get("glossary_hits"): continue
        first=(unit.get("translations") or [{}])[0]
        lines += [f"### {unit['unit_id']} ({unit['kind']}, {unit['status']})","",f"Strategy: {final.get('strategy')}",f"Penalty first → selected: {first.get('penalty')} → {final.get('penalty')}","```json",json.dumps(checks,ensure_ascii=False,indent=2),"```","Domain and glossary:","```json",json.dumps({"domain":unit.get("domain"),"scores":unit.get("context",{}).get("domain_scores"),"hits":unit.get("glossary_hits",[])},ensure_ascii=False,indent=2),"```","Selected output:","```text",final.get("text",""),"```","Candidates:","```json",json.dumps([{k:c.get(k) for k in ("stage","strategy","penalty","checks")} for c in unit.get("translations",[])],ensure_ascii=False,indent=2),"```",""]
    lines += ["## Citation and organization variants","","```json",json.dumps(report.get("consistency",{}),ensure_ascii=False,indent=2),"```",""]
    if report.get("fallback_reason"): lines += ["Fallback reason: "+report["fallback_reason"],""]
    md.write_text("\n".join(lines),encoding="utf-8")


def log_stage(name,seconds,units,enabled):
    if enabled: print(json.dumps({"event":"inference_stage","stage":name,"seconds":round(seconds,6),"units":units}),flush=True)
