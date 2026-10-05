"""One versioned JSON for all optional inference-layer settings."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path


class PipelineConfig:
    def __init__(self, values, *, path=None):
        self.values=values; self.path=Path(path).resolve() if path else None
        self.validate()

    @classmethod
    def load(cls,path, *, environment=True):
        values=json.loads(Path(path).read_text(encoding="utf-8"))
        if environment:
            for name in values["features"]:
                variable="VINAI_PIPELINE_"+name.upper()
                if variable in os.environ:
                    raw=os.environ[variable].lower()
                    if raw not in {"0","1","true","false"}: raise ValueError(f"Invalid boolean: {variable}")
                    values["features"][name]=raw in {"1","true"}
        return cls(values,path=path)

    def validate(self):
        v=self.values
        if v["schema_version"]!=1: raise ValueError("Unsupported pipeline config version")
        if any(not isinstance(x,bool) for x in v["features"].values()): raise ValueError("Feature flags must be booleans")
        c=v["chunker"]
        if not 0<c["retry_budget"]<=c["target_budget"]<=c["hard_budget"]: raise ValueError("Invalid chunk budgets")
        if v["runtime"]["time_budget_per_doc"] is not None and v["runtime"]["time_budget_per_doc"]<=0: raise ValueError("Time budget must be positive or null")
        if v["translator"]["batch_size"]<1: raise ValueError("Batch size must be positive")
        if v["retry"]["rounds"]!=1: raise ValueError("Only one retry round is allowed")
        if v["translator"]["candidate_decoding"].get("do_sample",False): raise ValueError("Sampling is forbidden")
        if v["features"]["new_decoding"] and not v["evaluation"]["experimental"] and not v["promotion"].get("approved",False):
            raise ValueError("New decoding requires promotion evidence or explicit experimental mode")

    @property
    def hash(self):
        return hashlib.sha256(json.dumps(self.values,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

    def resource(self,path):
        p=Path(path)
        if p.is_absolute(): return p
        # Resource paths are relative to the single mounted config.
        return (self.path.parent / p).resolve() if self.path else p

    def copy(self):
        return PipelineConfig(json.loads(json.dumps(self.values)),path=self.path)
