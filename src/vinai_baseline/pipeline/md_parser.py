"""Lossless source-offset parser. Structural bytes never pass through the model."""
from __future__ import annotations
import hashlib
import re
from .types import ParsedDocument, Placeholder, TranslationUnit

FORMATS = {"tags": lambda n: f"<ph{n}>", "brackets":lambda n:f"[[PH{n}]]", "braces":lambda n:f"{{PH{n}}}"}
PREFIX = re.compile(r"^(?:[ \t]*(?:> ?))*[ \t]*(?:(?:#{1,6}|\d+[.)]|[A-Za-zđĐ][)]|[-+*]) +)?")
RULE = re.compile(r"^\s*(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$")
ALIGN = re.compile(r"^\s*:?-{3,}:?\s*$")


def _closing(text, start, opening, closing):
    depth = 1; i = start + 1
    while i < len(text):
        if text[i] == "\\": i += 2; continue
        if text[i] == opening: depth += 1
        if text[i] == closing:
            depth -= 1
            if depth == 0: return i
        i += 1
    return -1


def mask_inline(text: str, format_name: str = "brackets") -> tuple[str, list[Placeholder]]:
    make = FORMATS[format_name]; placeholders = []
    def single(value):
        token = make(len(placeholders))
        if token in text: raise ValueError("Source collides with placeholder namespace")
        placeholders.append(Placeholder(token, value)); return token
    def pair(opening, body, closing):
        ident = str(len(placeholders))
        a = single(opening); placeholders[-1].pair = ident; placeholders[-1].role = "open"
        middle = scan(body)
        b = single(closing); placeholders[-1].pair = ident; placeholders[-1].role = "close"
        return a + middle + b
    def scan(value):
        parts = []; i = 0
        while i < len(value):
            remaining = value[i:]; code = re.match(r"(`+)", remaining)
            if code:
                marker = code[0]; end = value.find(marker, i+len(marker))
                if end >= 0:
                    parts.append(single(value[i:end+len(marker)])); i=end+len(marker); continue
            foot = re.match(r"\[\^[^\]\n]+\]", remaining)
            if foot: parts.append(single(foot[0])); i += len(foot[0]); continue
            image = remaining.startswith("![")
            if image or remaining.startswith("["):
                j = i+int(image); end = _closing(value,j,"[","]")
                if end >= 0 and end+1 < len(value) and value[end+1] in "([":
                    op=value[end+1]; close=")" if op=="(" else "]"; dest_end=_closing(value,end+1,op,close)
                    if dest_end >= 0:
                        parts.append(pair(value[i:j+1],value[j+1:end],value[end:dest_end+1])); i=dest_end+1; continue
            url = re.match(r"(?:https?://|mailto:)[^\s<>]+|<[^>\n]+>|\\[^\w\s]",remaining)
            if url:
                raw=url[0]
                if raw.startswith(("http", "mailto:")): raw=raw.rstrip(".,;:!?)")
                parts.append(single(raw)); i += len(raw); continue
            matched = False
            for marker in ("***", "___", "**", "__", "~~", "*", "_"):
                if not remaining.startswith(marker): continue
                if marker.startswith("_") and i > 0 and value[i-1].isalnum(): continue
                end=value.find(marker,i+len(marker))
                if end > i+len(marker) and not value[i+len(marker)].isspace() and not value[end-1].isspace():
                    parts.append(pair(marker,value[i+len(marker):end],marker)); i=end+len(marker); matched=True; break
            if matched: continue
            parts.append(value[i]); i+=1
        return "".join(parts)
    return scan(text), placeholders


def placeholder_errors(text: str, placeholders: list[Placeholder]) -> list[str]:
    errors = []; stack = []
    for p in placeholders:
        if text.count(p.token) != 1: errors.append(f"count:{p.token}")
    if errors: return errors
    for p in sorted(placeholders, key=lambda p:text.index(p.token)):
        if p.role == "open": stack.append(p.pair)
        elif p.role == "close":
            if not stack or stack.pop() != p.pair: errors.append(f"pair_order:{p.pair}")
    if stack: errors.append("unclosed_pair")
    return errors


def restore_inline(text: str, placeholders: list[Placeholder]) -> str:
    errors=placeholder_errors(text,placeholders)
    if errors: raise ValueError("Placeholder survival failed: " + ",".join(errors))
    for p in placeholders: text=text.replace(p.token,p.original)
    return text


def strip_spans(unit: TranslationUnit) -> tuple[str, list[Placeholder], str, str, bool]:
    """Remove paired markup, retain singles, never guess alignment."""
    value=unit.src_masked; singles=[]; opening=""; closing=""; whole_pairs=set()
    for p in unit.placeholders:
        if p.role != "open": continue
        partner=next(q for q in unit.placeholders if q.pair==p.pair and q.role=="close")
        if not value[:value.index(p.token)].strip() and not value[value.index(partner.token)+len(partner.token):].strip(): whole_pairs.add(p.pair)
    for p in unit.placeholders:
        if p.role == "single": singles.append(p); continue
        value=value.replace(p.token,"")
        if p.pair in whole_pairs:
            if p.role=="open": opening+=p.original
            else: closing=p.original+closing
    partial=any(p.role!="single" and p.pair not in whole_pairs for p in unit.placeholders)
    return value,singles,opening,closing,partial


def _pipe_positions(line: str):
    positions=[]; i=0; code=None
    while i < len(line):
        if line[i]=="\\": i+=2; continue
        if line[i]=="`":
            run=re.match(r"`+",line[i:])[0]
            if code is None: code=run
            elif run==code: code=None
            i+=len(run); continue
        if line[i]=="|" and code is None: positions.append(i)
        i+=1
    return positions


def parse_document(source: str, *, doc_id: str | None = None, placeholder_format: str="brackets", inline: bool=True) -> ParsedDocument:
    doc_id=doc_id or hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    document=ParsedDocument(source,doc_id,[]); offset=0; fence=None; front=False; html=None; article=None; headers=[]
    lines=source.splitlines(keepends=True)
    def add(start,end,kind,prefix,context=None):
        raw=source[start:end]
        if not raw.strip(): return
        masked, placeholders=mask_inline(raw,placeholder_format) if inline else (raw,[]); n=len(document.units)
        document.units.append(TranslationUnit(f"{doc_id}:{n:05d}",doc_id,n,kind,prefix,raw,masked,start,end,placeholders,context or {}))
    for line_no, line in enumerate(lines):
        body=line.rstrip("\r\n"); stripped=body.strip(); block_kind="text"
        fence_body=re.sub(r"^(?:[ \t]*> ?)+","",body)
        fence_body=re.sub(r"^[ \t]*(?:\d+[.)]|[A-Za-zđĐ][)]|[-+*]) +","",fence_body)
        if line_no==0 and stripped.lstrip("\ufeff")=="---" and any(l.strip() in ("---","...") for l in lines[1:]): front=True; block_kind="front_matter"
        elif front:
            block_kind="front_matter"
            if stripped in ("---","..."): front=False
        elif fence:
            block_kind="code"
            if re.match(r"^\s*"+re.escape(fence[0])+"{"+str(fence[1])+r",}\s*$",fence_body): fence=None
        elif re.match(r"^\s{0,3}(`{3,}|~{3,})",fence_body):
            marker=re.match(r"^\s{0,3}(`{3,}|~{3,})",fence_body)[1]; fence=(marker[0],len(marker)); block_kind="code"
        elif html:
            block_kind="html"
            if html=="blank" and not stripped: html=None
            elif html!="blank" and re.search(html,body,re.I): html=None
        elif re.match(r"^\s*<!--",body): block_kind="html"; html=None if "-->" in body else "-->"
        elif re.match(r"^\s*<(?:script|style|pre|div|table|section|details)\b",body,re.I):
            block_kind="html"; tag=re.search(r"<([a-z]+)",body,re.I)[1]; html=None if re.search(r"</"+tag+">",body,re.I) else r"</"+tag+r">"
        elif re.match(r"^\s*(?:<![A-Z]|<\?|</?(?:p|ul|ol|li|h[1-6]|blockquote|hr)\b)",body,re.I): block_kind="html"; html="blank"
        elif not stripped: block_kind="blank"
        elif RULE.fullmatch(body): block_kind="rule"
        elif re.match(r"^\s{4,}|^\t",body) and not re.match(r"^\s*(?:\d+[.)]|[A-Za-zđĐ][)]|[-+*])\s+",body): block_kind="indented_code"
        elif re.match(r"^\s*\[[^\]]+\]:\s*\S+",body) and not re.match(r"^\s*\[\^",body): block_kind="link_definition"
        else:
            pipes=_pipe_positions(body)
            table = bool(pipes) and (bool(headers) or stripped.startswith("|") or (line_no+1<len(lines) and all(ALIGN.fullmatch(x) for x in lines[line_no+1].strip().strip("|").split("|"))))
            if table:
                boundaries=[-1,*pipes,len(body)]; cells=[(a+1,b) for a,b in zip(boundaries,boundaries[1:])]
                cells=[(a,b) for a,b in cells if (a!=b and body[a:b].strip()) or (a!=0 and b!=len(body))]
                if cells and all(not body[a:b].strip() or ALIGN.fullmatch(body[a:b]) for a,b in cells): block_kind="table_alignment"
                else:
                    block_kind="table_row"; current=[]
                    for col,(a,b) in enumerate(cells):
                        raw=body[a:b]; left=len(raw)-len(raw.lstrip()); right=len(raw.rstrip()); current.append(raw.strip())
                        add(offset+a+left,offset+a+right,"table_cell", "", {"column_index":col,"column_header":headers[col] if col<len(headers) else "", "article":article})
                    if not headers: headers=current
            else:
                if stripped: headers=[]
                prefix=PREFIX.match(body)[0]; a=len(prefix); end=len(body.rstrip(" \t"))
                closing=re.search(r"\s+#+\s*$",body[a:end]) if re.match(r"^\s*#{1,6} ",body) else None
                if closing: end=a+closing.start()
                content=body[a:end]; kind="paragraph"
                if re.match(r"(?:Điều|Article)\s+\d+",content,re.I): kind="article_heading"; article=content
                elif "#" in prefix: kind="heading"
                elif re.match(r"Căn cứ\b|Pursuant\b",content,re.I): kind="preamble"
                elif re.search(r"\d+[.)] +$",prefix): kind="clause"
                elif re.search(r"[a-zđ][)] +$",prefix,re.I): kind="point"
                elif re.search(r"[-+*] +$",prefix): kind="list_item"
                elif re.match(r"(?:TM\.|KT\.|FOR THE|ON BEHALF)",content,re.I): kind="signature"
                elif line_no==0: kind="title"
                foot=re.match(r"\[\^[^\]]+\]:\s*",content)
                if foot: a+=len(foot[0]); prefix=body[:a]
                add(offset+a,offset+end,kind,prefix,{"article":article})
        document.blocks.append({"kind":block_kind,"start":offset,"end":offset+len(line)}); offset+=len(line)
    return document
