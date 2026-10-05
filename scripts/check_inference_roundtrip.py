"""Check every exact frozen-dev segment without modifying it."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.vinai_baseline.pipeline.md_parser import parse_document
from src.vinai_baseline.pipeline.reassembler import reassemble
from src.vinai_baseline.pipeline.types import Candidate


def main():
    p=argparse.ArgumentParser(); p.add_argument("--dev",type=Path,default=Path("artifacts/processed_clean_semantic_seed67_v3/segments_dev_vi2en.jsonl")); p.add_argument("--output",type=Path,default=Path("reports/inference_pipeline/roundtrip.json")); args=p.parse_args()
    records=markup=units=0; failures=[]
    for line in args.dev.read_text(encoding="utf-8").splitlines():
        row=json.loads(line); source=row["source"]; records+=1; doc=parse_document(source,doc_id=row["segment_id"])
        units+=len(doc.units); markup+=sum(any(ph.role!="single" for ph in u.placeholders) for u in doc.units)
        for unit in doc.units: unit.final=Candidate(unit.src_masked)
        if reassemble(doc).encode()!=source.encode() or reassemble(doc,identity=True).encode()!=source.encode(): failures.append(row["segment_id"])
    report={"records":records,"units":units,"markup_units":markup,"failures":failures,"round_trip_rate":100*(records-len(failures))/records}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(report,indent=2),encoding="utf-8"); print(json.dumps(report)); return bool(failures)


if __name__=="__main__": raise SystemExit(main())
