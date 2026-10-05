"""Approved, direction-matched phrase glossary; no document-wide replacement."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import re


class Glossary:
    def __init__(self,path: Path | None,settings):
        self.settings=settings; self.entries=[]; self.version="empty"
        if path is not None:
            if not path.is_file(): raise FileNotFoundError(f"Missing inference glossary: {path}")
            self.version=hashlib.sha256(path.read_bytes()).hexdigest()
            with path.open(encoding="utf-8-sig",newline="") as handle:
                for row in csv.DictReader(handle):
                    if row["status"]!="approved": continue
                    if row["match_mode"] not in {"exact_phrase","token_boundary"}: raise ValueError("Unsupported glossary matching")
                    row["accepted_variants"]=json.loads(row["accepted_variants"] or "[]")
                    if not isinstance(row["accepted_variants"],list): raise ValueError("accepted_variants must be a JSON array")
                    row["priority"]=int(row["priority"])
                    if not row["src_phrase"].strip() or not row["preferred"].strip(): raise ValueError("Empty approved glossary term")
                    self.entries.append(row)

    def domain(self,text):
        scores={name:sum(len(re.findall(r"(?<!\w)"+re.escape(term)+r"(?!\w)",text,re.I))*weight for term,weight in keywords.items()) for name,keywords in self.settings["domains"].items()}
        ranked=sorted(scores.items(),key=lambda x:(-x[1],x[0])); threshold=self.settings["domain_min_score"]; margin=self.settings["domain_margin"]
        if not ranked or threshold is None or margin is None: return "general",scores
        best,score=ranked[0]; second=ranked[1][1] if len(ranked)>1 else 0
        return (best if score>=threshold and score-second>=margin else "general"),scores

    def match(self,text,*,direction,domain):
        choices=[]
        for entry in self.entries:
            if entry["direction"]!=direction or entry["domain"] not in {"general",domain}: continue
            for m in re.finditer(r"(?<!\w)"+re.escape(entry["src_phrase"])+r"(?!\w)",text,re.I):
                choices.append((m.start(),m.end(),entry))
        selected=[]; occupied=[]
        for start,end,entry in sorted(choices,key=lambda x:(-(x[1]-x[0]),-x[2]["priority"],x[0],x[2]["id"])):
            if any(a<end and start<b for a,b in occupied): continue
            occupied.append((start,end)); selected.append({**entry,"start":start,"end":end})
        return sorted(selected,key=lambda r:r["start"])
