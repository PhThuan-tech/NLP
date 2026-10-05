"""Budget-aware splits that preserve atomic legal spans and exact separators."""
from __future__ import annotations
from dataclasses import dataclass
import re
from ..inference import token_length


class ChunkingError(ValueError): pass


@dataclass(frozen=True)
class Piece:
    text: str
    separator_before: str = ""


def protected_spans(text, *, phrases=(), placeholders=()):
    spans=[]
    patterns=[r"(?i)(?:Điều|Khoản|Điểm|Article|Clause|Paragraph|Point)\s+[\w]+(?:\s+(?:Điều|Khoản|Điểm|Article|Clause|Paragraph|Point)\s+[\w]+)*",r"(?i)(?:Nghị định|Thông tư|Quyết định|Decree|Circular|Decision)\s+(?:số\s+|No\.?\s*)?\d+(?:/[^\s,;]+)*(?:\s+ngày\s+\d+\s+tháng\s+\d+\s+năm\s+\d+)?",r"\d+(?:[.,/]\d+)*(?:\s+tháng\s+\d+\s+năm\s+\d+)?",r"(?:TP|Đ|No|Art)\."]
    for p in patterns: spans.extend((m.start(),m.end()) for m in re.finditer(p,text))
    for phrase in phrases:
        spans.extend((m.start(),m.end()) for m in re.finditer(r"(?<!\w)"+re.escape(phrase)+r"(?!\w)",text,re.I))
    stack=[]
    for i,char in enumerate(text):
        if char=="(": stack.append(i)
        elif char==")" and stack: spans.append((stack.pop(),i+1))
    by_pair={}
    for p in placeholders:
        if p.token not in text: continue
        i=text.index(p.token); spans.append((i,i+len(p.token)))
        if p.role=="open": by_pair[p.pair]=i
        elif p.role=="close" and p.pair in by_pair: spans.append((by_pair[p.pair],i+len(p.token)))
    return spans


def split_unit(text, tokenizer, *, budget, hard_budget, phrases=(), placeholders=()):
    if token_length(tokenizer,text)<=budget: return [Piece(text)]
    spans=protected_spans(text,phrases=phrases,placeholders=placeholders)
    # Whitespace is the only allowable cut, preserving punctuation and byte layout.
    cuts=[m for m in re.finditer(r"\s+",text) if not any(a<m.start()<b or a<m.end()<b for a,b in spans)]
    result=[]; start=0; separator=""
    while start<len(text):
        if token_length(tokenizer,text[start:])<=budget:
            result.append(Piece(text[start:],separator)); break
        available=[m for m in cuts if m.start()>start and token_length(tokenizer,text[start:m.start()])<=budget]
        if available:
            sentence=[m for m in available if text[m.start()-1] in ".;:\n" and not any(a<m.start()<=b for a,b in spans)]
            chosen=(sentence or available)[-1]
        else:
            # An indivisible legal span may exceed target, but never the model limit.
            chosen=next((m for m in cuts if m.start()>start),None)
            end=chosen.start() if chosen else len(text)
            if token_length(tokenizer,text[start:end])>hard_budget: raise ChunkingError("Indivisible span exceeds hard budget")
            if chosen is None: result.append(Piece(text[start:],separator)); break
        result.append(Piece(text[start:chosen.start()],separator)); separator=chosen[0]; start=chosen.end()
    if "".join(p.separator_before+p.text for p in result)!=text: raise AssertionError("Chunk source coverage lost")
    if any(token_length(tokenizer,p.text)>hard_budget for p in result): raise ChunkingError("Chunk exceeds hard budget")
    return result
