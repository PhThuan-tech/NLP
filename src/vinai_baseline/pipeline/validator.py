"""Conservative per-candidate checks; signals are not legal correctness proofs."""
from __future__ import annotations
from collections import Counter
from decimal import Decimal, InvalidOperation
import re
import unicodedata
from ..service import VI_MARKS_RE
from .md_parser import placeholder_errors, restore_inline

MONTHS="January February March April May June July August September October November December".split()
MONTH_MAP={m.lower():i+1 for i,m in enumerate(MONTHS)}
MONTH_MAP.update({m[:3].lower():i+1 for i,m in enumerate(MONTHS)})
MONTH_PATTERN="(?:"+"|".join(MONTHS)+"|"+"|".join(m[:3] for m in MONTHS)+r")\.?"
ID_RE=re.compile(r"(?i)(?<!\w)\d{1,4}\s*/\s*\d{4}\s*/\s*[a-zđ0-9]+(?:\s*[-–]\s*[a-zđ0-9]+)*(?!\w)")
REF_RE=re.compile(r"(?i)\b(articles?|art\.?|điều|clauses?|paragraphs?|khoản|points?|điểm|chapters?|chương|sections?|mục)\s+([a-zđ]|\d+[a-zđ]?|[ivxlcdm]+)\b")
KINDS={"article":"article","articles":"article","art":"article","điều":"article","clause":"clause","clauses":"clause","paragraph":"clause","paragraphs":"clause","khoản":"clause","point":"point","points":"point","điểm":"point","chapter":"chapter","chapters":"chapter","chương":"chapter","section":"section","sections":"section","mục":"section"}
NUM_RE=re.compile(r"(?<!\w)\d+(?:[.,]\d+)*(?:%?)(?!\w)")
NUMBER_WORDS={str(i):w for i,w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


def ascii_legal(text):
    return "".join(c for c in unicodedata.normalize("NFD",text.replace("Đ","D").replace("đ","d")) if unicodedata.category(c)!="Mn")


def normalize_number(raw,language):
    raw=raw.replace("\u00a0","").replace(" ",""); percent=raw.endswith("%"); raw=raw.removesuffix("%")
    thousands="." if language=="vi" else ","; decimal="," if language=="vi" else "."
    if re.fullmatch(r"\d{1,3}(?:"+re.escape(thousands)+r"\d{3})+(?:"+re.escape(decimal)+r"\d+)?",raw): raw=raw.replace(thousands,"")
    raw=raw.replace(decimal,".")
    try: result=format(Decimal(raw).normalize(),"f")
    except InvalidOperation: result="ambiguous:"+raw
    return result+("%" if percent else "")


def dates(text):
    patterns=[(r"(?i)ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",lambda m:(int(m[1]),int(m[2]),int(m[3]))), (r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)",lambda m:(int(m[1]),int(m[2]),int(m[3]))),(r"(?i)\b("+MONTH_PATTERN+r")\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})\b",lambda m:(int(m[2]),MONTH_MAP[m[1].rstrip('.').lower()],int(m[3]))),(r"(?i)\b(\d{1,2})(?:st|nd|rd|th)?\s+("+MONTH_PATTERN+r")\s*,?\s*(\d{4})\b",lambda m:(int(m[1]),MONTH_MAP[m[2].rstrip('.').lower()],int(m[3])))]
    found=[]; occupied=[]
    from datetime import date
    for pattern,extract in patterns:
        for m in re.finditer(pattern,text):
            if any(a<m.end() and m.start()<b for a,b in occupied): continue
            value=extract(m)
            try: date(value[2],value[1],value[0])
            except ValueError: continue
            found.append(value); occupied.append(m.span())
    return Counter(found),occupied


def entities(text,language):
    date_values,spans=dates(text)
    masked=list(text)
    for a,b in spans: masked[a:b]=" "*(b-a)
    rest="".join(masked)
    return {"dates":date_values,"identifiers":Counter(ascii_legal(re.sub(r"\s+","",m[0])).replace("–","-").upper() for m in ID_RE.finditer(rest)),"references":Counter(KINDS[m[1].lower().rstrip('.')]+":"+ascii_legal(m[2].lower()) for m in REF_RE.finditer(rest)),"numbers":Counter(normalize_number(m[0],language) for m in NUM_RE.finditer(rest))}


def numeric_spelling(text):
    _,spans=dates(text); masked=list(text)
    for a,b in spans: masked[a:b]=" "*(b-a)
    return Counter(re.sub(r"[.,]","",m[0]) for m in NUM_RE.finditer("".join(masked)))


def consecutive_runs(text,size):
    tokens=re.findall(r"\w+|[^\w\s]",text.casefold()); maximum=1
    for start in range(len(tokens)-size):
        pattern=tokens[start:start+size]; run=1; pos=start+size
        while tokens[pos:pos+size]==pattern: run+=1; pos+=size
        maximum=max(maximum,run)
    return maximum


def validate(unit,candidate,settings,*,direction="vi2en",placeholders=None):
    checks=[]
    def add(name,severity,detail): checks.append({"check":name,"severity":severity,"detail":detail})
    text=candidate.text
    ph=unit.placeholders if placeholders is None else placeholders
    broken=[] if candidate.restored else placeholder_errors(text,ph)
    if broken: add("placeholder","error",broken)
    plain=text if candidate.restored or broken else restore_inline(text,ph)
    # Kept syntax/code/URLs and entity names do not count as wrong-language text.
    for p in ph:
        if p.role=="single": plain=plain.replace(p.original,"").replace(p.token,"")
    if not plain.strip(): add("empty","error","No language-bearing output")
    if direction=="vi2en":
        language_text=plain
        for name in settings["kept_names"]: language_text=language_text.replace(name,"")
        density=len(VI_MARKS_RE.findall(language_text))/max(1,sum(c.isalpha() for c in language_text))
        if density>settings["vi_density_limit"]: add("wrong_language","error",{"density":density,"limit":settings["vi_density_limit"]})
    if candidate.reached_token_cap is True or candidate.gen_finished_by_eos is False: add("token_cutoff","error",{"eos":candidate.gen_finished_by_eos,"cap":candidate.reached_token_cap})
    elif candidate.gen_finished_by_eos is None: add("generation_unknown","info","Saved text has no EOS/cap evidence")
    if re.search(settings["dangling_pattern"],plain,re.I) or (re.search(r"[.;:!?]\s*$",unit.src_text) and not re.search(r"[.;:!?][\s\"')]*$",plain)):
        add("dangling","warning","Incomplete ending signal; not proof of missing meaning")
    ratio=len(plain.split())/max(1,len(unit.src_text.split())); threshold=settings["short_ratio_by_kind"].get(unit.kind,settings["short_ratio"])
    if ratio<threshold: add("short","warning",{"word_ratio":ratio,"train_p01":threshold})
    src_lang,tgt_lang=("vi","en") if direction=="vi2en" else ("en","vi")
    source_entities=entities(unit.src_text,src_lang); output_entities=entities(plain,tgt_lang)
    for name in ("dates","identifiers","references","numbers"):
        missing=source_entities[name]-output_entities[name]; extra=output_entities[name]-source_entities[name]
        if missing or extra:
            severity="error"; written=False
            if name=="numbers" and direction=="vi2en" and not extra:
                written=all(n in NUMBER_WORDS and len(re.findall(r"(?i)\b"+NUMBER_WORDS[n]+r"\b",plain))>=count for n,count in missing.items())
                if written or all(n.startswith("ambiguous:") for n in missing): severity="warning"
            if name=="numbers" and numeric_spelling(unit.src_text)==numeric_spelling(plain): severity="warning"
            add(name,severity,{"missing":{str(k):v for k,v in missing.items()},"extra":{str(k):v for k,v in extra.items()},"written_number_equivalence":written})
    for hit in unit.glossary_hits:
        variants=[hit["preferred"],*hit["accepted_variants"]]
        if not any(re.search(r"(?<!\w)"+re.escape(v)+r"(?!\w)",plain,re.I) for v in variants): add("terminology","warning",{"entry":hit["id"],"preferred":hit["preferred"]})
    for size in settings["consecutive_ngram_sizes"]:
        run=consecutive_runs(plain,size); original=consecutive_runs(unit.src_text,size)
        if run>=settings["consecutive_repeat_min"] and run>original: add("repetition","warning",{"ngram":size,"run":run,"source_run":original}); break
    count=lambda s:len(re.findall(r"[.;:](?:\s|$)",s))
    source_sentences=count(unit.src_text); output_sentences=count(plain)
    if source_sentences and output_sentences/source_sentences<settings["sentence_retention_ratio"]: add("missing_sentences","warning",{"source":source_sentences,"output":output_sentences})
    candidate.checks=checks; return checks


def penalty(candidate,weights): return sum(weights[c["severity"]] for c in candidate.checks)


def citation_variants(text):
    variants={}
    for m in REF_RE.finditer(text):
        key=KINDS[m[1].lower().rstrip('.')]+":"+ascii_legal(m[2].lower())
        variants.setdefault(key,set()).add(m[0])
    return {key:sorted(values) for key,values in variants.items() if len(values)>1}


TAXONOMY={"empty":"E1","wrong_language":"E1","source_kept":"E1","short":"E2","missing_sentences":"E2","dangling":"E3","token_cutoff":"E3","repetition":"E4","placeholder":"E5","protected_inline_loss":"E5","markup_lost":"E5","dates":"E6","numbers":"E6","identifiers":"E6","references":"E6","terminology":"E7"}
