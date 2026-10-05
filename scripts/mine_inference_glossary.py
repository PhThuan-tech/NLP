"""Extract pending glossary evidence from aligned frozen train; never approve it."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import csv
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.vinai_baseline.pipeline.validator import REF_RE, KINDS

FIELDS=["id","src_phrase","direction","domain","preferred","accepted_variants","match_mode","priority","evidence","status","train_pairs","translation_distribution","conflict","example_segment_id"]


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--train",type=Path,default=Path("artifacts/processed_clean_semantic_seed67_v3/segments_train_vi2en.jsonl")); p.add_argument("--output",type=Path,default=Path("submission/resources/glossary_candidates.csv")); p.add_argument("--report",type=Path,default=Path("reports/inference_pipeline/citation_convention.md")); args=p.parse_args()
    distributions=defaultdict(Counter); counts=Counter(); examples={}
    for line in args.train.read_text(encoding="utf-8").splitlines():
        row=json.loads(line); source=row["source"]; target=row["target"]
        source_refs={m[1].lower():m[1] for m in REF_RE.finditer(source) if m[1].lower() in {"điều","khoản","điểm","chương","mục"}}
        for term,display in source_refs.items():
            variants=Counter(m[1] for m in REF_RE.finditer(target) if KINDS[m[1].lower().rstrip('.')]==KINDS[term])
            if variants:
                distributions[display.capitalize()].update(variants); counts[display.capitalize()]+=1; examples.setdefault(display.capitalize(),row["segment_id"])
        # Multiline legal headers provide stronger organization boundaries than free text.
        for phrase in re.findall(r"(?m)^\s*((?:BỘ|Bộ|ỦY BAN NHÂN DÂN|Ủy ban nhân dân|TÒA ÁN|Tòa án|SỞ|Sở) [^\n,;:.]+)",source):
            phrase=phrase.strip()
            english=re.findall(r"(?im)^\s*((?:MINISTRY|Ministry|PEOPLE['’]S COMMITTEE|People['’]s Committee|COURT|Court|DEPARTMENT|Department)[^\n;:]+)",target)
            if len(english)==1:
                distributions[phrase][english[0].strip()]+=1; counts[phrase]+=1; examples.setdefault(phrase,row["segment_id"])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=FIELDS); writer.writeheader()
        for i,(phrase,variants) in enumerate(sorted(distributions.items())):
            ranked=variants.most_common(); preferred=ranked[0][0]
            writer.writerow({"id":f"train-{i:05d}","src_phrase":phrase,"direction":"vi2en","domain":"general","preferred":preferred,"accepted_variants":json.dumps([v for v,_ in ranked[1:]],ensure_ascii=False),"match_mode":"exact_phrase","priority":len(phrase.split()),"evidence":"Aligned train co-occurrence; requires user review (not word alignment)","status":"pending","train_pairs":counts[phrase],"translation_distribution":json.dumps(dict(ranked),ensure_ascii=False),"conflict":len(variants)>1,"example_segment_id":examples[phrase]})
    lines=["# Citation conventions from frozen train","","All candidates are pending. Counts are English reference occurrences in aligned train pairs containing the Vietnamese term; they are not semantic alignment proofs.","","| Vietnamese | Majority form | Distribution |","|---|---|---|"]
    for term in ("Điều","Khoản","Điểm","Chương","Mục"):
        variants=distributions[term]; lines.append(f"| {term} | {variants.most_common(1)[0][0] if variants else 'unavailable'} | {json.dumps(dict(variants),ensure_ascii=False)} |")
    args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"pending_candidates":len(distributions),"approved":0,"output":str(args.output)}))


if __name__=="__main__": main()
