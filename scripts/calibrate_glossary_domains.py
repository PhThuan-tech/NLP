"""Derive legal-domain keyword scores and confidence thresholds from frozen train."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import re


def quantile(values,p):
    values=sorted(values); i=(len(values)-1)*p; a=int(i); b=min(a+1,len(values)-1)
    return values[a]+(values[b]-values[a])*(i-a)


def features(text,size):
    words=re.findall(r"[^\W\d_]+",text.casefold())
    return Counter(" ".join(words[i:i+size]) for i in range(len(words)-size+1))


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--train",type=Path,default=Path("artifacts/processed_clean_semantic_seed67_v3/segments_train_vi2en.jsonl")); p.add_argument("--config",type=Path,default=Path("submission/configs/inference_pipeline.json")); p.add_argument("--report",type=Path,default=Path("reports/inference_pipeline/domain_calibration.json")); args=p.parse_args()
    config=json.loads(args.config.read_text(encoding="utf-8")); parameters=config["glossary"]["domain_calibration"]
    rows=[json.loads(line) for line in args.train.read_text(encoding="utf-8").splitlines()]
    totals=Counter(); categories=Counter(); counts=defaultdict(Counter)
    for row in rows:
        terms=set(features(row["source"],parameters["ngram_size"])); totals.update(terms); counts[row["category"]].update(terms); categories[row["category"]]+=1
    domains={}
    for category,words in counts.items():
        frequent_threshold=quantile(list(words.values()),parameters["frequency_quantile"])
        frequent={word:count for word,count in words.items() if count>=frequent_threshold}
        lift={word:(count/totals[word])/(categories[category]/len(rows)) for word,count in frequent.items()}
        threshold=quantile(list(lift.values()),parameters["lift_quantile"])
        domains[category]={word:math.log(value) for word,value in sorted(lift.items()) if value>=threshold and value>1}
    scores=[]; margins=[]; correct=0
    for row in rows:
        bag=features(row["source"],parameters["ngram_size"])
        ranked=sorted(((category,sum(bag[term]*weight for term,weight in keywords.items())) for category,keywords in domains.items()),key=lambda r:(-r[1],r[0]))
        if ranked[0][0]==row["category"] and ranked[0][1]>0:
            correct+=1; scores.append(ranked[0][1]); margins.append(ranked[0][1]-ranked[1][1] if len(ranked)>1 else ranked[0][1])
    if not scores: raise ValueError("No supported domain keywords; keep general-only inference")
    config["glossary"].update(domains=domains,domain_min_score=quantile(scores,parameters["confidence_quantile"]),domain_margin=quantile(margins,parameters["confidence_quantile"]))
    report={"method":"Document-frequency bigrams, frequent-feature lift against category prior; thresholds are train percentiles, not a supervised translation-model update","train_sha256":hashlib.sha256(args.train.read_bytes()).hexdigest(),"records":len(rows),"parameters":dict(parameters),"keywords_per_domain":{k:len(v) for k,v in domains.items()},"train_top1_rate":100*correct/len(rows),"train_top1_note":"Calibration fit statistic, not held-out classification accuracy","minimum_score":config["glossary"]["domain_min_score"],"margin":config["glossary"]["domain_margin"]}
    report["parameters"].pop("provenance",None)
    config["glossary"]["domain_calibration"]["provenance"]=report
    args.config.write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(json.dumps(report,indent=2))


if __name__=="__main__": main()
