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
    statuses=Counter(u.status for u in document.units)
    return {"schema_version":1,"doc_id":document.doc_id,"chunks":len(document.units),"summary":{"units":len(document.units),**{status:statuses[status] for status in ("OK","RETRIED_FIXED","RETRIED_UNFIXED","SOURCE_KEPT")}},"invariants":invariants,"units":[asdict(u) for u in document.units],"runtime":{"stages_seconds":stages,"retry_skipped_budget":retry_skipped,"time_budget_per_doc":config.values["runtime"]["time_budget_per_doc"]},"versions":{"config_sha256":config.hash,"glossary_sha256":glossary_version,"code_sha256":code_version(),"seed":config.values["seed"]},"fallback":False}


def write_report(path,report):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    md=path.with_suffix(".md")
    lines=["# Document translation report","",f"Document: `{report.get('doc_id','unknown')}`",f"Fallback: {report.get('fallback',False)}","","## Summary","","```json",json.dumps(report.get("summary",{}),ensure_ascii=False,indent=2),"```","","## Invariants","","```json",json.dumps(report.get("invariants",{}),ensure_ascii=False,indent=2),"```","","## Runtime and versions","","```json",json.dumps({"runtime":report.get("runtime"),"versions":report.get("versions")},ensure_ascii=False,indent=2),"```","","## Units with checks or retries",""]
    for unit in report.get("units",[]):
        final=unit.get("final") or {}; checks=final.get("checks",[])
        if not checks and unit["status"]=="OK": continue
        lines += [f"### {unit['unit_id']} ({unit['kind']}, {unit['status']})","",f"Strategy: {final.get('strategy')}","```json",json.dumps(checks,ensure_ascii=False,indent=2),"```","Selected output:","```text",final.get("text",""),"```","Candidates:","```json",json.dumps([{k:c.get(k) for k in ("stage","strategy","checks")} for c in unit.get("translations",[])],ensure_ascii=False,indent=2),"```",""]
    lines += ["## Citation and organization variants","","```json",json.dumps(report.get("consistency",{}),ensure_ascii=False,indent=2),"```",""]
    if report.get("fallback_reason"): lines += ["Fallback reason: "+report["fallback_reason"],""]
    md.write_text("\n".join(lines),encoding="utf-8")


def log_stage(name,seconds,units,enabled):
    if enabled: print(json.dumps({"event":"inference_stage","stage":name,"seconds":round(seconds,6),"units":units}),flush=True)
