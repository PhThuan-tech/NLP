"""Create an offline Kaggle project with copied frozen data and immutable adapters."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); parser.add_argument("--output",type=Path,default=Path("dist/NLP_inference_pipeline.zip")); args=parser.parse_args()
    root=args.root.resolve(); output=args.output.resolve(); output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): raise FileExistsError("Use a new output filename; do not overwrite an existing handoff")
    manifest={"schema_version":1,"purpose":"inference only, no training or split regeneration","files":{},"adapters":{}}
    selected=[root/p for p in ("README.md","requirements.txt","requirements-training-colab.txt","requirements-training.txt","src","tests","scripts","docs","configs","notebooks/05_inference_pipeline_kaggle.ipynb","submission/configs","submission/resources","submission/requirements-inference.txt","submission/Dockerfile","submission/translate.sh","submission/README.md","data/instruction.md","artifacts/processed_clean_semantic_seed67_v3","reports/inference_pipeline")]
    files=[]
    for path in selected:
        if not path.exists(): raise FileNotFoundError(path)
        files.extend(path.rglob("*") if path.is_dir() else [path])
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        def add(name,data):
            bundle.writestr("project/"+name,data); manifest["files"][name]={"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
        for path in sorted(set(files)):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc",".pyo"}: continue
            if path.is_relative_to(root/"reports/inference_pipeline") and (set(path.parts)&{"workspace","evaluation"} or path.suffix==".jsonl"): continue
            add(path.relative_to(root).as_posix(),path.read_bytes())
        for direction in ("en2vi","vi2en"):
            candidates=sorted((root/"modelAI").glob(f"*{direction}*zip"))
            if len(candidates)!=1: raise ValueError(f"Select exactly one current {direction} archive")
            with zipfile.ZipFile(candidates[0]) as archive:
                for item in archive.infolist():
                    path=Path(item.filename)
                    if path.is_absolute() or ".." in path.parts or "\\" in item.filename: raise ValueError("Unsafe model archive path")
                    keep=(path.parts and path.parts[0]=="best_model" and path.suffix in {".json",".model",".safetensors"}) or item.filename in {"resolved_config.json","run_manifest.json","predictions/validation_predictions.jsonl"}
                    if keep and not item.is_dir(): add(f"attached_runs/{direction}/"+path.as_posix(),archive.read(item))
                manifest["adapters"][direction]={"archive":candidates[0].name,"adapter_sha256":hashlib.sha256(archive.read("best_model/adapter_model.safetensors")).hexdigest()}
        bundle.writestr("project/bundle_manifest.json",json.dumps(manifest,indent=2))
    checksum=hashlib.sha256(output.read_bytes()).hexdigest(); output.with_suffix(".zip.sha256").write_text(checksum+"  "+output.name+"\n",encoding="utf-8")
    print(json.dumps({"output":str(output),"bytes":output.stat().st_size,"sha256":checksum,"adapters":manifest["adapters"]},indent=2))


if __name__=="__main__": main()
