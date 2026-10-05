"""Read immutable train pairs and derive inference budgets/thresholds only."""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.vinai_baseline.pipeline.md_parser import parse_document


def quantile(values,p):
    values=sorted(values); index=(len(values)-1)*p; low=int(index); high=min(low+1,len(values)-1)
    return values[low]+(values[high]-values[low])*(index-low)


def vi_density(text):
    from src.vinai_baseline.service import VI_MARKS_RE
    letters=sum(c.isalpha() for c in text)
    return len(VI_MARKS_RE.findall(text))/max(letters,1)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train",type=Path,default=Path("artifacts/processed_clean_semantic_seed67_v3/segments_train_vi2en.jsonl"))
    p.add_argument("--tokenizer-dir",type=Path,default=Path("offline_training_assets/models/vinai-translate-vi2en-v2"))
    p.add_argument("--config",type=Path,default=Path("submission/configs/inference_pipeline.json"))
    p.add_argument("--overwrite",action="store_true",help="Explicitly replace a reviewed inference config")
    p.add_argument("--reports",type=Path,default=Path("reports/inference_pipeline")); args=p.parse_args()
    if args.config.exists() and not args.overwrite: raise FileExistsError("Config exists; supply --overwrite only to replace inference settings")
    from transformers import AutoTokenizer
    wrapped=AutoTokenizer.from_pretrained(args.tokenizer_dir,local_files_only=True,src_lang="vi_VN",tgt_lang="en_XX",use_fast=True)
    tokenizer=wrapped.backend_tokenizer
    rows=[json.loads(line) for line in args.train.read_text(encoding="utf-8").splitlines()]
    sources=[r["source"] for r in rows]; targets=[r["target"] for r in rows]
    src=[len(x.ids) for x in tokenizer.encode_batch(sources)]; tgt=[len(x.ids) for x in tokenizer.encode_batch(targets)]
    ratios=[b/a for a,b in zip(src,tgt)]; word_ratios=[len(b.split())/max(len(a.split()),1) for a,b in zip(sources,targets)]
    density=[vi_density(t) for t in targets]
    by_kind=defaultdict(list)
    for source,target in zip(sources,targets):
        units=parse_document(source).units
        if len(units)==1: by_kind[units[0].kind].append(len(target.split())/max(len(source.split()),1))
    model=json.loads((args.tokenizer_dir/"config.json").read_text(encoding="utf-8")); hard=model["max_position_embeddings"]
    target=min(hard,int(quantile(src,.95)+.999999)); retry=max(1,target//2)
    residual=[b-a for a,b in zip(src,tgt)]; safety=max(0,int(quantile(residual,.99)+.999999))
    stats={"records":len(rows),"source_percentiles":{str(q):quantile(src,q) for q in (.5,.9,.95,.99)},"token_ratio_p99":quantile(ratios,.99),"target_minus_source_p99":safety,"word_ratio_p01":quantile(word_ratios,.01),"english_vi_density_p99":quantile(density,.99),"by_kind_word_ratio_p01":{k:{"records":len(v),"threshold":quantile(v,.01)} for k,v in by_kind.items()},"train_sha256":hashlib.sha256(args.train.read_bytes()).hexdigest(),"tokenizer_sha256":hashlib.sha256((args.tokenizer_dir/"sentencepiece.bpe.model").read_bytes()).hexdigest(),"stored_length_matches":sum(a==r["source_token_count"] for a,r in zip(src,rows)),"calibration_method":"local fast tokenizer encode_batch with special tokens; p95 target, half retry, p99 target/source linear slope and residual margin"}
    config={"schema_version":1,"seed":67,"directions":["vi2en"],"features":{"enabled":False,"parser":True,"inline_placeholders":True,"chunker":True,"new_decoding":False,"dynamic_length":False,"glossary":True,"retry":True,"validator":True,"cache":True,"reverse_check":False},"parser":{"placeholder_format":"brackets","placeholder_format_selected":False},"chunker":{"target_budget":target,"hard_budget":hard,"retry_budget":retry,"short_cell_tokens":4,"short_cell_strategy":"isolated","short_cell_lookup":{},"context_separator":" : "},"translator":{"batch_size":8,"minimum_new_tokens":8,"maximum_new_tokens":hard-1,"dynamic_slope":stats["token_ratio_p99"],"dynamic_margin":safety,"candidate_decoding":{"no_repeat_ngram_size":0},"model_identity":None},"validator":{"weights":{"error":3,"warning":1,"info":0},"short_ratio":stats["word_ratio_p01"],"short_ratio_by_kind":{k:v["threshold"] for k,v in stats["by_kind_word_ratio_p01"].items()},"vi_density_limit":stats["english_vi_density_p99"],"kept_names":[],"dangling_pattern":r"(?:/ND|\bof the|\band|People[’'])\s*$","sentence_retention_ratio":quantile([len(__import__('re').findall(r'[.;:](?:\s|$)',b))/max(1,len(__import__('re').findall(r'[.;:](?:\s|$)',a))) for a,b in zip(sources,targets)],.01),"consecutive_ngram_sizes":[1,2,3,4],"consecutive_repeat_min":3},"glossary":{"file":"../resources/glossary.csv","domains":{},"domain_min_score":None,"domain_margin":None},"retry":{"rounds":1,"minimum_warnings":2,"nbest":4,"constrained":False,"constrained_max_terms":1,"anti_repeat":{},"require_error_fixed":True},"runtime":{"time_budget_per_doc":None,"retry_reserve_seconds":None,"structured_logs":True,"reports_directory":"../reports","safe_fallback":True},"evaluation":{"experimental":False,"random_clean_records":30,"cause_probe_minimum":10,"placeholder_samples":200,"placeholder_formats":["tags","brackets","braces"],"length_penalties":[1.0,1.2],"manual_review_records":30,"allowed_chrf_drop":0.0,"required_structure_rate":100.0},"promotion":{"approved":False,"evidence":None},"calibration":stats}
    config["legacy"]={"maximum_source_tokens":448,"batch_size":8}
    config["evaluation"]["progress_records"]=25
    config["runtime"]["cublas_workspace_config"]=":4096:8"
    args.config.parent.mkdir(parents=True,exist_ok=True); args.config.write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    args.reports.mkdir(parents=True,exist_ok=True); (args.reports/"train_length_stats.json").write_text(json.dumps(stats,indent=2),encoding="utf-8")
    (args.reports/"train_length_stats.md").write_text("# Train token length calibration\n\nRead-only calibration of frozen VI→EN train, using the actual local tokenizer.\n\n```json\n"+json.dumps(stats,indent=2)+f"\n```\n\nTarget budget: {target}; hard budget: {hard}; retry budget: {retry}.\n\nDynamic generation is disabled until A/B. Thresholds come from train, not public test.\nKind-specific length ratios use only single-unit aligned train pairs.\n",encoding="utf-8")
    print(json.dumps(stats,indent=2))


if __name__=="__main__": main()
