"""Deterministic model adapter with per-sequence EOS/cap provenance."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import asdict
import hashlib
import json
import math
import os
import time
from ..inference import token_length
from .types import Candidate


class ModelTranslator:
    def __init__(self,tokenizer,model,experiment,pipeline,device):
        self.tokenizer=tokenizer; self.model=model; self.experiment=experiment; self.pipeline=pipeline; self.device=device; self.cache={}
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG",pipeline.values["runtime"]["cublas_workspace_config"])
        import torch
        torch.manual_seed(pipeline.values["seed"])
        if torch.cuda.is_available(): torch.cuda.manual_seed_all(pipeline.values["seed"])
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark=False
        self.model.to(device); self.model.eval()

    def generation(self,text,overrides=None):
        settings=self.pipeline.values; params=asdict(self.experiment.generation)
        if settings["features"]["new_decoding"]: params.update(settings["translator"]["candidate_decoding"])
        dynamic=settings["features"]["dynamic_length"]
        extras=dict(overrides or {}); dynamic=extras.pop("_dynamic_length",dynamic)
        params.update(extras)
        if dynamic:
            t=settings["translator"]; cap=math.ceil(t["dynamic_slope"]*token_length(self.tokenizer,text)+t["dynamic_margin"])
            params["max_new_tokens"]=min(t["maximum_new_tokens"],max(t["minimum_new_tokens"],cap))
        if params.get("max_new_tokens") is not None: params.pop("max_length",None)
        params.update(do_sample=False,return_dict_in_generate=True)
        return params

    def generate_many(self,texts,*,overrides=None,stage="first",strategy="baseline",nbest=1):
        import torch
        groups=defaultdict(list); output=[None]*len(texts)
        for i,text in enumerate(texts):
            params=self.generation(text,overrides)
            if nbest>1: params.update(num_beams=max(nbest,params["num_beams"]),num_return_sequences=nbest)
            key=json.dumps({"text":text,"params":params,"config":self.pipeline.hash,"glossary":self.pipeline.values["glossary"].get("version"),"model":self.pipeline.values["translator"]["model_identity"]},sort_keys=True,ensure_ascii=False)
            key=hashlib.sha256(key.encode()).hexdigest()
            if self.pipeline.values["features"]["cache"] and key in self.cache:
                copied=[Candidate(**json.loads(json.dumps(asdict(c)))) for c in self.cache[key]]
                for c in copied: c.stage=stage; c.strategy=strategy; c.provenance["cache_hit"]=True
                output[i]=copied; continue
            groups[json.dumps(params,sort_keys=True)].append((i,text,key))
        for raw,items in groups.items():
            params=json.loads(raw); items.sort(key=lambda row:token_length(self.tokenizer,row[1]))
            batch_size=self.pipeline.values["translator"]["batch_size"]
            for start in range(0,len(items),batch_size):
                batch=items[start:start+batch_size]; started=time.perf_counter()
                inputs=self.tokenizer([t for _,t,_ in batch],return_tensors="pt",padding=True,truncation=False)
                if inputs["input_ids"].shape[-1]>self.pipeline.values["chunker"]["hard_budget"]: raise ValueError("Model input exceeds hard budget; truncation forbidden")
                with torch.inference_mode(): result=self.model.generate(**{k:v.to(self.device) for k,v in inputs.items()},**params)
                sequences=result.sequences.detach().cpu().tolist(); decoded=self.tokenizer.batch_decode(sequences,skip_special_tokens=True)
                eos=self.model.generation_config.eos_token_id; eos=set(eos if isinstance(eos,list) else [eos]); pad=self.tokenizer.pad_token_id
                for row,(index,text,key) in enumerate(batch):
                    candidates=[]
                    for n in range(nbest):
                        idx=row*nbest+n; ids=sequences[idx][1:]
                        eos_index=next((j for j,value in enumerate(ids) if value in eos),None)
                        active=ids[:eos_index+1] if eos_index is not None else [v for v in ids if v!=pad]
                        cap=params.get("max_new_tokens",params.get("max_length",0)-1)
                        reached=len(active)>=cap
                        candidate=Candidate(decoded[idx].strip(),stage,strategy,eos_index is not None,reached,len(active),cap,
                                            provenance={"last_token_id":active[-1] if active else None,"forced_eos_at_cap_possible":reached and eos_index is not None,"generation":params,"model_identity":self.pipeline.values["translator"]["model_identity"],"elapsed_batch_seconds":time.perf_counter()-started,"cache_hit":False})
                        candidates.append(candidate)
                    output[index]=candidates
                    if self.pipeline.values["features"]["cache"]: self.cache[key]=candidates
        return output

    def generate(self,text,**kwargs): return self.generate_many([text],**kwargs)[0]
