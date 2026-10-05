"""Read-only fixed-dev generation, cause probes, A/B, ablation and promotion checks."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random
import time
import zipfile
from ..config import ExperimentConfig
from ..inference import load_inference_model, split_markdown_document, translate_chunks, assemble_document, markdown_structure_report
from .config import PipelineConfig
from .md_parser import parse_document, placeholder_errors
from .reassembler import reassemble
from .runtime import LegalTranslationPipeline
from .translator import ModelTranslator
from .types import Candidate, TranslationUnit
from .validator import validate, TAXONOMY
from .report import write_report, code_version
from .promotion import file_hash, model_identity, behavior_hash, verify_promotion


def prepare(archive,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()): raise FileExistsError("Preparation output must be empty; original archive is never overwritten")
    with zipfile.ZipFile(archive) as z:
        metadata=json.loads(z.read("resolved_config.json"))
        for item in z.infolist():
            path=Path(item.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in item.filename: raise ValueError("Unsafe archive path")
            keep=(path.parts and path.parts[0]=="best_model" and path.suffix in {".json",".model",".safetensors"}) or item.filename in {"resolved_config.json","run_manifest.json","predictions/validation_predictions.jsonl"}
            if keep and not item.is_dir():
                dest=output/path; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(z.read(item))
        if not (output/"best_model/adapter_model.safetensors").is_file(): raise FileNotFoundError("Archive lacks a LoRA adapter")
    print(json.dumps({"direction":metadata["direction"],"adapter":str(output/"best_model"),"adapter_sha256":file_hash(output/"best_model/adapter_model.safetensors")}))


def score(predictions,references,rows):
    import sacrebleu
    bleu=sacrebleu.metrics.BLEU(); chrf=sacrebleu.metrics.CHRF(word_order=2)
    # Same strip convention as the existing training metric suite.
    preds=[p.strip() for p in predictions]; refs=[r.strip() for r in references]
    output={"BLEU":bleu.corpus_score(preds,[refs]).score,"chrF++":chrf.corpus_score(preds,[refs]).score,"signatures":{"BLEU":str(bleu.get_signature()),"chrF++":str(chrf.get_signature())},"sacrebleu_version":sacrebleu.__version__}
    groups=defaultdict(list)
    for i,row in enumerate(rows): groups[row["sample_id"]].append(i)
    documents={}
    for doc,indices in groups.items():
        indices.sort(key=lambda i:rows[i]["chunk_index"])
        documents[doc]={"BLEU":bleu.corpus_score(["\n\n".join(preds[i] for i in indices)],[["\n\n".join(refs[i] for i in indices)]]).score,"chrF++":chrf.corpus_score(["\n\n".join(preds[i] for i in indices)],[["\n\n".join(refs[i] for i in indices)]]).score,"segments":len(indices),"layout":"synthetic double-newline, not original Markdown documents"}
    output["documents"]=documents; return output


def whole_unit(row):
    return TranslationUnit(row["segment_id"],row["sample_id"],row["chunk_index"],"paragraph","",row["source"],row["source"],0,len(row["source"]))


def taxonomy(row,candidate,config,report=None):
    unit=whole_unit(row); validate(unit,candidate,config.values["validator"],direction="vi2en",placeholders=[])
    labels={TAXONOMY[c["check"]] for c in candidate.checks if c["check"] in TAXONOMY}
    if not markdown_structure_report(row["source"],candidate.text)["structure_counts_match"]: labels.add("E5")
    if report:
        for u in report.get("units",[]):
            for c in (u.get("final") or {}).get("checks",[]):
                if c["check"] in TAXONOMY: labels.add(TAXONOMY[c["check"]])
    return sorted(labels)


def variants(config,mode):
    if mode in {"ab","causes"}:
        return [("A0",{}),("A1",{"no_repeat_ngram_size":0})] if mode=="causes" else [("A0",{}),("A1",{"no_repeat_ngram_size":0}),("A2",{"_dynamic_length":True}),("A3",{"no_repeat_ngram_size":0,"_dynamic_length":True}),*[(f"A4_lp{lp}",{"no_repeat_ngram_size":0,"_dynamic_length":True,"length_penalty":lp}) for lp in config.values["evaluation"]["length_penalties"]]]
    return [(f"R{i}",{"parser":i>=1,"chunker":i>=2,"new_decoding":i>=3,"dynamic_length":i>=3,"glossary":i>=4,"retry":i>=5}) for i in range(6)]


def run(args):
    import torch
    execution_code_hash=code_version()
    if args.limit is not None and args.limit<1: raise ValueError("--limit must be positive")
    if args.output.exists() and any(args.output.iterdir()): raise FileExistsError("Use an empty evaluation output directory to avoid mixing runs")
    rows=[json.loads(line) for line in args.dev.read_text(encoding="utf-8").splitlines()]
    if len({r["segment_id"] for r in rows})!=len(rows): raise ValueError("Repeated dev IDs")
    config=PipelineConfig.load(args.pipeline_config,environment=False); config.values["evaluation"]["experimental"]=True
    os_environment=config.values["runtime"]["cublas_workspace_config"]
    import os
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG",os_environment)
    experiment=ExperimentConfig.from_json(args.experiment_config)
    if experiment.direction!="vi2en" or any(r["direction"]!="vi2en" for r in rows): raise ValueError("This fixed-dev experiment targets VI2EN only")
    dev_hash=file_hash(args.dev)
    if dev_hash!=config.values["evaluation"]["fixed_dev_sha256"]: raise ValueError("The fixed frozen dev hash does not match the evaluation config")
    config.values["translator"]["model_identity"]=model_identity(experiment,args.adapter)
    if not torch.cuda.is_available() and not args.allow_cpu: raise RuntimeError("Use Kaggle GPU; --allow-cpu is for an explicitly requested CPU smoke only")
    if args.mode=="placeholder" and not any(any(p.role!="single" for p in u.placeholders) for r in rows for u in parse_document(r["source"]).units):
        args.output.mkdir(parents=True,exist_ok=True)
        return placeholder_run(rows,config,experiment,None,None,None,args.output)
    tokenizer,model=load_inference_model(experiment,saved_model_dir=args.adapter)
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type=="cuda" and experiment.training.fp16: model.to(device=device,dtype=torch.float16)
    model.to(device); model.eval()
    args.output.mkdir(parents=True,exist_ok=True)
    if args.limit: rows=rows[:args.limit]
    snapshot=None
    if args.baseline_snapshot:
        snapshot={r["segment_id"]:r for r in [json.loads(l) for l in args.baseline_snapshot.read_text(encoding="utf-8").splitlines()]}
        if any(r["segment_id"] not in snapshot for r in rows): raise ValueError("Snapshot IDs differ from dev")
        if any(snapshot[r["segment_id"]]["source"]!=r["source"] or snapshot[r["segment_id"]]["target"]!=r["target"] for r in rows): raise ValueError("Snapshot source/reference texts differ from fixed dev")
    if args.mode in {"ab","causes"}:
        if snapshot is None: raise ValueError("Run fixed snapshot audit first and supply --baseline-snapshot")
        errors=[]; clean=[]
        for row in rows:
            text=snapshot[row["segment_id"]]["prediction"]
            labels=taxonomy(row,Candidate(text),config)
            (errors if set(labels)&{"E2","E3","E4"} else clean).append(row)
        if args.mode=="causes":
            import re
            suspect=[r for r in errors if re.search(config.values["validator"]["dangling_pattern"],snapshot[r["segment_id"]]["prediction"],re.I)]
            suspect.sort(key=lambda r: (not snapshot[r["segment_id"]]["prediction"].rstrip().endswith("/ND"),r["segment_id"]))
            rows=suspect[:config.values["evaluation"]["cause_probe_minimum"]]
        else:
            rng=random.Random(config.values["seed"])
            rows=errors+rng.sample(clean,min(len(clean),config.values["evaluation"]["random_clean_records"]))
    if not rows: raise ValueError("No eligible evaluation samples; no result may be invented")
    subset={"dev_sha256":dev_hash,"record_ids":[r["segment_id"] for r in rows],"limit":args.limit,"seed":config.values["seed"]}
    (args.output/"subset.json").write_text(json.dumps(subset,indent=2),encoding="utf-8")
    if args.mode=="placeholder": return placeholder_run(rows,config,experiment,tokenizer,model,device,args.output)
    summaries=[]; full_outputs={}; full_reports={}
    for name,changes in variants(config,args.mode):
        selected=config.copy(); selected.values["features"]["enabled"]=True
        if args.mode in {"ab","causes"}: selected.values["features"].update(new_decoding=False,dynamic_length=False)
        if args.mode=="ablation":
            selected.values["features"].update(changes)
            if name in {"R3","R4","R5"}:
                if not args.selection: raise ValueError("R3–R5 need the selected A/B JSON; no speculative decoding allowed")
                decision=json.loads(args.selection.read_text(encoding="utf-8"))
                validate_selection(decision,config,experiment,dev_hash,execution_code_hash,allow_partial=bool(args.limit))
                new=decision["overrides"].copy(); selected.values["features"]["dynamic_length"]=new.pop("_dynamic_length",False)
                selected.values["translator"]["candidate_decoding"]=new
        translator=ModelTranslator(tokenizer,model,experiment,selected,device)
        def legacy(text):
            chunks=split_markdown_document(text,tokenizer,maximum_tokens=selected.values["legacy"]["maximum_source_tokens"])
            pred,report=translate_chunks(chunks,tokenizer=tokenizer,model=model,config=experiment,batch_size=selected.values["legacy"]["batch_size"],device=device,fail_on_empty=False)
            return assemble_document(chunks,pred),report
        predictions=[]; detail=[]; counts=Counter(); started=time.perf_counter(); reports=[]; document_times=Counter()
        if args.mode in {"ab","causes"}:
            generated=translator.generate_many([r["source"] for r in rows],overrides=changes,strategy=name)
            for row,values in zip(rows,generated,strict=True):
                candidate=values[0]; predictions.append(candidate.text); labels=taxonomy(row,candidate,selected); counts.update(labels)
                detail.append({"segment_id":row["segment_id"],"source":row["source"],"target":row["target"],"candidate":asdict(candidate),"taxonomy":labels})
        else:
            pipeline=LegalTranslationPipeline(translator,selected)
            for index,row in enumerate(rows):
                record_started=time.perf_counter()
                output,report=pipeline.translate(row["source"],direction="vi2en",legacy=legacy,doc_id=row["segment_id"])
                document_times[row["sample_id"]]+=time.perf_counter()-record_started
                candidate=Candidate(output,restored=True); labels=taxonomy(row,candidate,selected,report)
                counts.update(labels); predictions.append(output); reports.append(report)
                detail.append({"segment_id":row["segment_id"],"prediction":output,"taxonomy":labels,"report":report})
                report["doc_id"]=row["segment_id"]
                report.setdefault("invariants",{})["legacy_marker_check"]=markdown_structure_report(row["source"],output)
                write_report(args.output/name/"documents"/(hashlib.sha256(row["segment_id"].encode()).hexdigest()+".report.json"),report)
                if (index+1)%selected.values["evaluation"]["progress_records"]==0: print(f"{name}: {index+1}/{len(rows)} records",flush=True)
        elapsed=time.perf_counter()-started; metrics=score(predictions,[r["target"] for r in rows],rows)
        summary={"name":name,"records":len(rows),"metrics":metrics,"taxonomy_counts":{f"E{i}":counts[f"E{i}"] for i in range(1,8)},"taxonomy_rates":{f"E{i}":100*counts[f"E{i}"]/len(rows) for i in range(1,8)},"runtime_seconds":elapsed,"seconds_per_unit":elapsed/len(rows),"model_identity":selected.values["translator"]["model_identity"],"dev_sha256":dev_hash,"code_sha256":code_version(),"config_sha256":selected.hash,"round_trip_rate":100*sum(reassemble(parse_document(r["source"]),identity=True)==r["source"] for r in rows)/len(rows),"structure_preservation_rate":100*sum(markdown_structure_report(r["source"],p)["structure_counts_match"] for r,p in zip(rows,predictions))/len(rows),"changes":changes}
        summary.update(code_sha256=execution_code_hash,code_changed_during_run=code_version()!=execution_code_hash,
                       environment={"device":str(device),"gpu":torch.cuda.get_device_name() if device.type=="cuda" else None,"packages":{p:importlib.metadata.version(p) for p in ("torch","transformers","peft","sacrebleu")}},
                       E7_status="measured_approved_entries" if args.mode=="ablation" and selected.values["features"]["glossary"] and pipeline.glossary.entries else "not_measured_no_active_approved_entries")
        if reports:
            total=sum(r.get("summary",{}).get("units",0) for r in reports)
            retries=sum(r.get("summary",{}).get("RETRIED_FIXED",0)+r.get("summary",{}).get("RETRIED_UNFIXED",0) for r in reports)
            fixed=sum(r.get("summary",{}).get("RETRIED_FIXED",0) for r in reports)
            finals=sum(r.get("invariants",{}).get("final_units",0) for r in reports)
            summary.update(unit_coverage_rate=100*finals/total if total else None,retry_rate=100*retries/total if total else 0,retry_fix_rate=100*fixed/retries if retries else 0,source_kept=sum(r.get("summary",{}).get("SOURCE_KEPT",0) for r in reports),fallback_documents=sum(bool(r.get("fallback")) for r in reports),seconds_per_document=elapsed/len({r["sample_id"] for r in rows}))
            summary["max_document_seconds"]=max(document_times.values(),default=0)
            summary["structure_preservation_rate"]=100*sum(r.get("invariants",{}).get("structure_preserved",markdown_structure_report(row["source"],prediction)["structure_counts_match"]) for r,row,prediction in zip(reports,rows,predictions))/len(rows)
        summaries.append(summary); full_outputs[name]=predictions; full_reports[name]=reports
        (args.output/f"{name}_predictions.jsonl").write_text("\n".join(json.dumps(r,ensure_ascii=False) for r in detail)+"\n",encoding="utf-8")
        (args.output/f"{name}_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({"candidate":name,"BLEU":metrics["BLEU"],"chrF++":metrics["chrF++"],"seconds":elapsed}),flush=True)
    if args.mode=="ab":
        base=summaries[0]; eligible=[r for r in summaries[1:] if r["metrics"]["chrF++"]>=base["metrics"]["chrF++"] and sum(r["taxonomy_counts"][e] for e in ("E2","E3","E4"))<sum(base["taxonomy_counts"][e] for e in ("E2","E3","E4"))]
        best=min(eligible,key=lambda r:(sum(r["taxonomy_counts"][e] for e in ("E2","E3","E4")),-r["metrics"]["chrF++"],r["runtime_seconds"])) if eligible else base
        overrides=best["changes"]
        decision={"status":"selected","selected":best["name"],"overrides":overrides,"new_decoding_improved":bool(eligible),"dev_sha256":dev_hash,"model_identity":config.values["translator"]["model_identity"],"base_generation":asdict(experiment.generation),"code_sha256":code_version(),"evaluated_records":len(rows),"partial":bool(args.limit),"note":"A0 retained if no candidate improves errors without chrF++ regression"}
        decision.update(code_sha256=execution_code_hash,behavior_sha256=behavior_hash(config),code_changed_during_run=code_version()!=execution_code_hash)
        (args.output/"selection.json").write_text(json.dumps(decision,indent=2),encoding="utf-8")
    if args.mode=="ablation":
        manual_review(rows,full_outputs,full_reports,config,args.output)
        acceptance(summaries,selected,experiment,args,args.output)
    table_report(args.mode,summaries,args.output)


def validate_selection(decision,config,experiment,dev_hash,execution_code_hash,*,allow_partial):
    expected={"status":"selected","model_identity":config.values["translator"]["model_identity"],"dev_sha256":dev_hash,"base_generation":asdict(experiment.generation),"code_sha256":execution_code_hash,"behavior_sha256":behavior_hash(config)}
    if any(decision.get(k)!=v for k,v in expected.items()) or decision.get("code_changed_during_run"):
        raise ValueError("A/B selection identity does not match this model/dev/config/code")
    if decision.get("partial") and not allow_partial: raise ValueError("A partial A/B selection cannot be used for full ablation")


def placeholder_run(rows,config,experiment,tokenizer,model,device,output):
    available=[]
    for row in rows:
        for unit in parse_document(row["source"],doc_id=row["segment_id"]).units:
            if any(p.role!="single" for p in unit.placeholders): available.append((row,unit.order_index))
    rng=random.Random(config.values["seed"]); chosen=rng.sample(available,min(len(available),config.values["evaluation"]["placeholder_samples"]))
    summaries=[]; translator=ModelTranslator(tokenizer,model,experiment,config,device) if chosen else None
    for fmt in config.values["evaluation"]["placeholder_formats"]:
        units=[parse_document(r["source"],doc_id=r["segment_id"],placeholder_format=fmt).units[index] for r,index in chosen]
        values=translator.generate_many([u.src_masked for u in units]) if units else []
        failures=sum(bool(placeholder_errors(v[0].text,u.placeholders)) for u,v in zip(units,values))
        summaries.append({"format":fmt,"samples":len(units),"survived":len(units)-failures,"survival_rate":100*(len(units)-failures)/len(units) if units else None})
    report={"status":"measured" if len(chosen)>=config.values["evaluation"]["placeholder_samples"] else "insufficient_dev_markup","available":len(available),"results":summaries,"selected":max(summaries,key=lambda s:s["survival_rate"] or -1)["format"] if len(chosen)>=config.values["evaluation"]["placeholder_samples"] else None}
    report.update(model_identity=config.values["translator"]["model_identity"],
                  generation=asdict(experiment.generation) if experiment else None,
                  code_sha256=code_version(),behavior_sha256=behavior_hash(config),
                  dev_sha256=config.values["evaluation"]["fixed_dev_sha256"])
    (output/"placeholder_survival.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    (output/"placeholder_survival.md").write_text("# Placeholder survival\n\n```json\n"+json.dumps(report,indent=2)+"\n```\n",encoding="utf-8")
    return report


def manual_review(rows,outputs,reports,config,output):
    rng=random.Random(config.values["seed"]); indices=rng.sample(range(len(rows)),min(len(rows),config.values["evaluation"]["manual_review_records"]))
    lines=["# Manual legal review","","Fixed random sample. Leave verdict pending until reviewed by the user."]
    for i in indices:
        row=rows[i]; lines += ["",f"## {row['segment_id']}","","Verdict: pending","","Source:","```text",row["source"],"```","R0:","```text",outputs["R0"][i],"```","R5:","```text",outputs["R5"][i],"```","Checks:","```json",json.dumps([u.get("final",{}).get("checks",[]) for u in reports["R5"][i].get("units",[])],ensure_ascii=False,indent=2),"```"]
    (output/"manual_review.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (output/"manual_review.json").write_text(json.dumps({"seed":config.values["seed"],"units":[{"segment_id":rows[i]["segment_id"],"verdict":"pending","note":""} for i in indices]},indent=2),encoding="utf-8")


def acceptance(summaries,config,experiment,args,output):
    baseline=summaries[0]; final=summaries[-1]; budget=config.values["runtime"]["time_budget_per_doc"]
    reasons=[]
    if args.limit: reasons.append("Partial dev run cannot be promoted")
    if final["structure_preservation_rate"]<config.values["evaluation"]["required_structure_rate"] or final.get("unit_coverage_rate")!=100: reasons.append("Structure/coverage gate failed")
    if final.get("source_kept",0) or final.get("fallback_documents",0): reasons.append("Source-kept/fallback outputs require review")
    if final["metrics"]["chrF++"]<baseline["metrics"]["chrF++"]-config.values["evaluation"]["allowed_chrf_drop"]: reasons.append("chrF++ regression")
    if final["metrics"]["BLEU"]<baseline["metrics"]["BLEU"]-config.values["evaluation"]["allowed_bleu_drop"]: reasons.append("BLEU regression")
    if any(r.get("code_changed_during_run") for r in summaries): reasons.append("Source code changed during evaluation")
    if final["round_trip_rate"]!=100: reasons.append("Round-trip gate failed")
    if budget is None: reasons.append("Submission time budget unknown")
    elif final.get("max_document_seconds",float("inf"))>budget: reasons.append("Worst measured document runtime exceeds budget")
    reasons.append("User manual review and deployment GPU smoke remain required")
    if config.values["features"]["inline_placeholders"]: reasons.append("Exact-candidate real-dev placeholder survival evidence remains required")
    report={"status":"pending" if reasons else "passed","reasons":reasons,"model_identity":config.values["translator"]["model_identity"],"generation":asdict(experiment.generation),"behavior_sha256":behavior_hash(config),"code_sha256":code_version(),"glossary_sha256":file_hash(config.resource(config.values["glossary"]["file"])),"dev_sha256":file_hash(args.dev),"records":len([l for l in args.dev.read_text(encoding='utf-8').splitlines() if l.strip()])}
    (output/"promotion_evidence.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    candidate=config.copy(); candidate.values["features"]["enabled"]=False; candidate.values["evaluation"]["experimental"]=False
    # Use absolute resource paths in the reviewable candidate; move them when mounting.
    candidate.values["glossary"]["file"]=str(config.resource(config.values["glossary"]["file"]))
    candidate.values["promotion"]["evidence"]=str((output/"promotion_evidence.json").resolve())
    (output/"selected_pipeline.json").write_text(json.dumps(candidate.values,indent=2),encoding="utf-8")


def table_report(mode,summaries,output):
    name={"ab":"decoding_ab","causes":"cutoff_cause_probe","ablation":"ablation"}[mode]
    lines=["# "+name,"","Measured generation; error rates are heuristic signals, not manually confirmed legal errors.","","| Run | Records | BLEU | chrF++ | E1 | E2 | E3 | E4 | E5 | E6 | E7 | Structure % | Coverage % | Retry % | Retry fixed % | Seconds/record |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in summaries:
        rates=" | ".join(f"{r['taxonomy_rates'][f'E{i}']:.2f}" for i in range(1,8))
        lines.append(f"| {r['name']} | {r['records']} | {r['metrics']['BLEU']:.4f} | {r['metrics']['chrF++']:.4f} | {rates} | {r['structure_preservation_rate']:.2f} | {r.get('unit_coverage_rate','n/a')} | {r.get('retry_rate','n/a')} | {r.get('retry_fix_rate','n/a')} | {r['seconds_per_unit']:.4f} |")
    if mode=="causes": lines += ["","Inspect A0/A1 candidate provenance in the paired prediction JSONLs. EOS before cap implies model/search termination; cap hit includes forced EOS. A paired improvement with only ngram changed is evidence of sensitivity, not proof that every truncation has the same cause."]
    (output/f"{name}.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (output/f"{name}.json").write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest="command",required=True)
    prep=sub.add_parser("prepare"); prep.add_argument("--archive",type=Path,required=True); prep.add_argument("--output",type=Path,required=True)
    evaluate=sub.add_parser("run"); evaluate.add_argument("--mode",choices=["causes","ab","placeholder","ablation"],required=True)
    evaluate.add_argument("--dev",type=Path,required=True); evaluate.add_argument("--adapter",type=Path,required=True); evaluate.add_argument("--experiment-config",type=Path,default=Path("submission/configs/vi2en.json")); evaluate.add_argument("--pipeline-config",type=Path,default=Path("submission/configs/inference_pipeline.json")); evaluate.add_argument("--output",type=Path,required=True); evaluate.add_argument("--baseline-snapshot",type=Path); evaluate.add_argument("--selection",type=Path); evaluate.add_argument("--allow-cpu",action="store_true"); evaluate.add_argument("--limit",type=int)
    args=parser.parse_args()
    if args.command=="prepare": prepare(args.archive,args.output)
    else: run(args)


if __name__=="__main__": main()
