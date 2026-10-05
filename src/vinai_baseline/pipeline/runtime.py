"""Optional inference orchestration with source coverage and legacy fallback."""
from __future__ import annotations
from dataclasses import asdict, replace
import re
import time
from ..inference import token_length, markdown_structure_report
from .chunker import split_unit
from .glossary import Glossary
from .md_parser import parse_document, placeholder_errors, restore_inline
from .reassembler import reassemble, coverage, escape_generated
from .report import build_report, log_stage, code_version
from .retry import retry_unit, should_retry
from .types import Candidate
from .validator import validate, citation_variants


class LegalTranslationPipeline:
    def __init__(self,translator,config):
        self.translator=translator; self.config=config
        self.glossary=Glossary(config.resource(config.values["glossary"]["file"]),config.values["glossary"])
        config.values["glossary"]["version"]=self.glossary.version

    def translate(self,source,*,direction,legacy=None,doc_id=None):
        settings=self.config.values; flags=settings["features"]; started=time.perf_counter(); stages={}; count=0
        def record(name,since):
            stages[name]=time.perf_counter()-since; log_stage(name,stages[name],count,settings["runtime"]["structured_logs"])
        if not flags["parser"]:
            if legacy is None: raise ValueError("R0 requires the original document translator")
            return legacy(source)
        try:
            since=time.perf_counter(); document=parse_document(source,doc_id=doc_id,placeholder_format=settings["parser"]["placeholder_format"],inline=flags["inline_placeholders"])
            count=len(document.units); record("parse",since)
            since=time.perf_counter(); domain,scores=self.glossary.domain(source) if flags["glossary"] else ("general",{})
            for unit in document.units:
                unit.domain=domain; unit.context["domain_scores"]=scores
                if flags["glossary"]: unit.glossary_hits=self.glossary.match(unit.src_text,direction=direction,domain=domain)
            record("glossary",since)
            since=time.perf_counter(); piece_map=[]; inputs=[]; short_cells={}; protected_only=set()
            for unit in document.units:
                unit.src_tokens=token_length(self.translator.tokenizer,unit.src_masked)
                remaining=unit.src_masked
                for placeholder in unit.placeholders: remaining=remaining.replace(placeholder.token,"")
                if unit.placeholders and not any(c.isalnum() for c in remaining):
                    protected_only.add(unit.unit_id)
                    piece_map.append((unit,[],[])); continue
                if flags["chunker"]:
                    pieces=split_unit(unit.src_masked,self.translator.tokenizer,budget=settings["chunker"]["target_budget"],hard_budget=settings["chunker"]["hard_budget"],phrases=[h["src_phrase"] for h in unit.glossary_hits],placeholders=unit.placeholders)
                else:
                    from .chunker import Piece
                    pieces=[Piece(unit.src_masked)]
                indices=[]
                for piece in pieces:
                    index=len(inputs); indices.append(index); input_text=piece.text
                    if unit.kind=="table_cell" and unit.src_tokens<=settings["chunker"]["short_cell_tokens"]:
                        strategy=settings["chunker"]["short_cell_strategy"]
                        if strategy=="column_context" and unit.context.get("column_header"):
                            input_text=unit.context["column_header"]+settings["chunker"]["context_separator"]+piece.text
                            short_cells[index]={"strategy":strategy,"original":piece.text}
                        elif strategy=="lookup":
                            entry=settings["chunker"]["short_cell_lookup"].get(piece.text)
                            if entry and entry["status"]=="approved" and entry["direction"]==direction:
                                short_cells[index]={"strategy":strategy,"original":piece.text,"target":entry["target"]}
                    inputs.append(input_text)
                piece_map.append((unit,pieces,indices))
            record("chunk",since)
            since=time.perf_counter(); generated=self.translator.generate_many(inputs) if inputs else []
            for index,cell in short_cells.items():
                if cell["strategy"]=="lookup": generated[index]=[Candidate(cell["target"],strategy="reviewed_short_cell_lookup",provenance={"approved_lookup":True})]
                else:
                    candidate=generated[index][0]; separator=settings["chunker"]["context_separator"]
                    if candidate.text.count(separator)==1: candidate.text=candidate.text.split(separator,1)[1].strip(); candidate.provenance["column_context_removed"]=True
                    else:
                        generated[index]=self.translator.generate(cell["original"],strategy="column_context_fallback")
            record("first_generation",since)
            since=time.perf_counter()
            for unit,pieces,indices in piece_map:
                if unit.unit_id in protected_only:
                    candidate=Candidate(unit.src_masked,strategy="protected_only",provenance={"generation_skipped":"No translatable text outside protected spans"})
                    unit.translations=[candidate]; unit.final=candidate; continue
                values=[generated[i][0] for i in indices]
                candidate=Candidate("".join(p.separator_before+c.text for p,c in zip(pieces,values,strict=True)),gen_finished_by_eos=all(c.gen_finished_by_eos is True for c in values),reached_token_cap=any(c.reached_token_cap is True for c in values),generated_tokens=sum(c.generated_tokens or 0 for c in values),provenance={"pieces":[{"generation":c.provenance,"eos":c.gen_finished_by_eos,"cap":c.reached_token_cap,"generated_tokens":c.generated_tokens} for c in values]})
                unit.translations=[candidate]; unit.final=candidate
                if flags["validator"]: validate(unit,candidate,settings["validator"],direction=direction)
            record("validate",since)
            since=time.perf_counter(); retry_skipped=False
            budget=settings["runtime"]["time_budget_per_doc"]
            reserve=settings["runtime"]["retry_reserve_seconds"]
            if reserve is None: reserve=stages["first_generation"]/max(count,1)*settings["retry"]["nbest"]
            for unit in document.units:
                if unit.unit_id in protected_only or not flags["retry"] or not should_retry(unit.final,settings["retry"]): continue
                if budget is not None and time.perf_counter()-started+reserve>=budget:
                    retry_skipped=True; unit.final.provenance["retry_skipped_budget"]=True; continue
                try: retry_unit(unit,self.translator,self.config,direction=direction)
                except Exception as error:
                    unit.status="RETRIED_UNFIXED"; unit.final.provenance["retry_exception"]=type(error).__name__
            record("retry",since)
            since=time.perf_counter(); lost_markup=0
            for unit in document.units:
                if not unit.final.text.strip() or (not unit.final.restored and placeholder_errors(unit.final.text,unit.placeholders)):
                    fallback=Candidate(unit.src_text,"fallback","source_kept",checks=[{"check":"source_kept","severity":"error","detail":"No safe nonempty candidate with protected spans"}],restored=True)
                    unit.translations.append(fallback); unit.final=fallback; unit.status="SOURCE_KEPT"
                if any(c["check"]=="markup_lost" for c in unit.final.checks): lost_markup+=1
                # Models cannot add physical lines or unescaped table columns.
                if not unit.final.restored:
                    text=unit.final.text
                    if "\n" in text or "\r" in text:
                        text=re.sub(r"[\r\n]+"," ",text); unit.final.checks.append({"check":"newlines_normalized","severity":"warning","detail":"Generated line breaks retained as spaces inside one source slot"})
                    unit.final.text=escape_generated(text,unit.placeholders)
            output=reassemble(document); invariants=coverage(document); structure=markdown_structure_report(source,output)
            invariants.update({"unit_coverage":invariants["source_units"]==invariants["final_units"],"partial_markup_lost_units":lost_markup,"legacy_marker_check":structure,"structure_preserved":not lost_markup and structure["structure_counts_match"]})
            record("reassemble",since); stages["total"]=time.perf_counter()-started
            if budget is not None and stages["total"]>budget: raise TimeoutError("Document pipeline exceeded configured stage-boundary budget")
            report=build_report(document,self.config,self.glossary.version,stages,invariants,retry_skipped=retry_skipped)
            if hasattr(self.translator,"experiment"):
                report["generation"]=asdict(self.translator.experiment.generation)
            organizations={}
            for unit in document.units:
                for hit in unit.glossary_hits:
                    found=[v for v in [hit["preferred"],*hit["accepted_variants"]] if re.search(r"(?<!\w)"+re.escape(v)+r"(?!\w)",unit.final.text,re.I)]
                    organizations.setdefault(hit["id"],set()).update(found)
            report["consistency"]={"citations":citation_variants(output),"glossary_variants":{k:sorted(v) for k,v in organizations.items() if len(v)>1}}
            return output,report
        except Exception as error:
            if not settings["runtime"]["safe_fallback"] or legacy is None: raise
            try: output,report=legacy(source)
            except Exception as fallback_error:
                output=source; report={"chunks":count,"summary":{"SOURCE_KEPT":count},"legacy_failure":type(fallback_error).__name__}
            if not output.strip() and source.strip(): output=source; report["source_kept"]=True
            report.update({"fallback":True,"fallback_reason":type(error).__name__,"doc_id":doc_id or "fallback","invariants":{"structure_preserved":False,"new_pipeline_failed":True},"runtime":{"stages_seconds":stages,"total_seconds":time.perf_counter()-started},"versions":{"config_sha256":self.config.hash,"glossary_sha256":self.glossary.version,"code_sha256":code_version(),"seed":settings["seed"]}})
            log_stage("legacy_fallback",time.perf_counter()-started,count,settings["runtime"]["structured_logs"])
            return output,report
