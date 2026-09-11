from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class DocumentChunk:
    id: str
    document_name: str
    page: int
    text: str
    sha256: str
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentRecord:
    name: str
    mime_type: str
    sha256: str
    page_count: int
    text: str
    chunks: list[DocumentChunk] = field(default_factory=list)
    indexed_with_embeddings: bool = False


@dataclass
class Requirement:
    code: str
    title: str
    mandatory: bool = True
    source_text: str = ""
    source_page: int = 1
    rule_type: str = "semantic_requirement"
    target: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    expected: str | float | None = None
    unit: str | None = None
    expected_concepts: list[str] = field(default_factory=list)
    severity: str = "mandatory"


@dataclass
class AuditResult:
    requirement: Requirement
    status: str
    evidence: str
    location: str = ""
    excerpt: str = ""


@dataclass
class RetrievalHit:
    chunk: DocumentChunk
    score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0
