from __future__ import annotations
from .md_parser import restore_inline
from .types import ParsedDocument


def reassemble(document: ParsedDocument, *, identity: bool=False) -> str:
    pieces=[]; previous=0
    for unit in document.units:
        if unit.start < previous or document.source[unit.start:unit.end] != unit.src_text: raise ValueError("Source offsets/order changed")
        pieces.append(document.source[previous:unit.start])
        if identity: translated=unit.src_text
        else:
            if unit.final is None: raise ValueError(f"Missing final translation: {unit.unit_id}")
            translated=unit.final.text if unit.final.restored else restore_inline(unit.final.text,unit.placeholders)
            if not translated.strip(): raise ValueError(f"Empty final translation: {unit.unit_id}")
        pieces.append(translated); previous=unit.end
    pieces.append(document.source[previous:]); return "".join(pieces)


def coverage(document: ParsedDocument):
    ids=[u.unit_id for u in document.units]
    return {"round_trip":reassemble(document,identity=True).encode()==document.source.encode(),"source_units":len(ids),"final_units":sum(u.final is not None and bool(u.final.text.strip()) for u in document.units),"unique_ordered_ids":len(set(ids))==len(ids) and [u.order_index for u in document.units]==list(range(len(ids)))}
