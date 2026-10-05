from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Placeholder:
    token: str
    original: str
    pair: str | None = None
    role: str = "single"


@dataclass
class Candidate:
    text: str
    stage: str = "first"
    strategy: str = "baseline"
    gen_finished_by_eos: bool | None = None
    reached_token_cap: bool | None = None
    generated_tokens: int | None = None
    max_new_tokens: int | None = None
    checks: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    restored: bool = False


@dataclass
class TranslationUnit:
    unit_id: str
    doc_id: str
    order_index: int
    kind: str
    prefix: str
    src_text: str
    src_masked: str
    start: int
    end: int
    placeholders: list[Placeholder] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    domain: str = "general"
    glossary_hits: list[dict[str, Any]] = field(default_factory=list)
    src_tokens: int = 0
    translations: list[Candidate] = field(default_factory=list)
    final: Candidate | None = None
    status: str = "OK"


@dataclass
class ParsedDocument:
    source: str
    doc_id: str
    units: list[TranslationUnit]
    blocks: list[dict[str, Any]] = field(default_factory=list)
