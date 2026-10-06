"""One retry round with strict, auditable candidate selection."""
from __future__ import annotations
from dataclasses import replace
from .chunker import split_unit
from .md_parser import restore_inline, strip_spans
from .types import Candidate
from .validator import penalty, validate
from .reassembler import escape_generated


def error_keys(candidate): return {c["check"] for c in candidate.checks if c["severity"]=="error"}


def choose(first,candidates,weights,*,require_error_fixed=True):
    best=first
    for candidate in candidates:
        fixed=error_keys(first)-error_keys(candidate)
        no_new_error=not (error_keys(candidate)-error_keys(first))
        if penalty(candidate,weights)<penalty(best,weights) and no_new_error and (fixed or not require_error_fixed): best=candidate
    return best


def should_retry(candidate,settings):
    return bool(error_keys(candidate)) or sum(c["severity"]=="warning" for c in candidate.checks)>=settings["minimum_warnings"] or any(c["check"]=="terminology" for c in candidate.checks)


def retry_unit(unit,translator,config,*,direction):
    if any(candidate.stage=="retry" for candidate in unit.translations): raise ValueError("A second retry round is forbidden")
    first=unit.translations[0]; settings=config.values; retry=settings["retry"]; checks={c["check"] for c in first.checks}; candidates=[]
    def check(candidate,ph=None):
        validate(unit,candidate,settings["validator"],direction=direction,placeholders=ph); candidates.append(candidate)
    if "placeholder" in checks:
        text,singles,opening,closing,partial=strip_spans(unit)
        for candidate in translator.generate(text,stage="retry",strategy="strip_spans"):
            check(candidate,singles)
            if not any(c["check"]=="placeholder" for c in candidate.checks):
                candidate.text=opening+restore_inline(escape_generated(candidate.text,singles),singles)+closing; candidate.restored=True
                if partial: candidate.checks.append({"check":"markup_lost","severity":"warning","detail":"Partial inline spans cannot be safely aligned"})
                for p in unit.placeholders:
                    if p.role=="close" and p.original.startswith("]") and p.original not in candidate.text:
                        candidate.checks.append({"check":"protected_inline_loss","severity":"error","detail":"A link/image destination cannot be restored without guessing alignment"})
    elif checks & {"token_cutoff","short","missing_sentences","dangling","empty","numbers","dates","identifiers","references","wrong_language"}:
        pieces=split_unit(unit.src_masked,translator.tokenizer,budget=settings["chunker"]["retry_budget"],hard_budget=settings["chunker"]["hard_budget"],phrases=[h["src_phrase"] for h in unit.glossary_hits],placeholders=unit.placeholders)
        translated=translator.generate_many([p.text for p in pieces],stage="retry",strategy="split_smaller")
        values=[result[0] for result in translated]
        candidate=Candidate("".join(p.separator_before+c.text for p,c in zip(pieces,values,strict=True)),"retry","split_smaller",all(c.gen_finished_by_eos is True for c in values),any(c.reached_token_cap is True for c in values),sum(c.generated_tokens or 0 for c in values),provenance={"pieces":[c.provenance for c in values]})
        check(candidate)
    elif "terminology" in checks:
        for candidate in translator.generate(unit.src_masked,stage="retry",strategy="nbest_rerank",nbest=retry["nbest"]): check(candidate)
        candidates.sort(key=lambda c:(penalty(c,settings["validator"]["weights"]),sum(ch["check"]=="terminology" for ch in c.checks)))
        if retry["constrained"] and all(any(ch["check"]=="terminology" for ch in c.checks) for c in candidates):
            # transformers 5.x moves constrained search to remote custom generation.
            # Fail closed offline rather than fetch executable Hub code.
            first.provenance["constrained_skipped"]="Offline constrained generation is unsupported by the installed inference stack"
    elif "repetition" in checks:
        if retry["anti_repeat"]:
            for candidate in translator.generate(unit.src_masked,overrides=retry["anti_repeat"],stage="retry",strategy="anti_repeat"): check(candidate)
        else: first.provenance["anti_repeat_skipped"]="Requires matched decoding A/B settings"
    unit.translations.extend(candidates)
    unit.final=choose(first,candidates,settings["validator"]["weights"],require_error_fixed=retry["require_error_fixed"])
    unit.status="RETRIED_FIXED" if unit.final is not first else "RETRIED_UNFIXED"
    return unit.final
