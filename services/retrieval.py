from __future__ import annotations

import math
import re
from collections import Counter

from services.models import DocumentChunk, DocumentRecord, RetrievalHit
from services.ollama_client import OllamaError, embed_texts, status

_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "into", "shall", "must",
    "should", "will", "are", "is", "of", "to", "a", "an", "in", "on", "be", "or",
}


def _tokens(text: str) -> list[str]:
    return [
        t for t in re.findall(r"[a-z0-9][a-z0-9._/-]*", text.casefold())
        if len(t) > 2 and t not in _STOP
    ]


def _lexical_score(query: str, text: str) -> float:
    q = Counter(_tokens(query))
    d = Counter(_tokens(text))
    if not q or not d:
        return 0.0
    matched = sum(min(count, d[token]) for token, count in q.items())
    phrase_bonus = 0.25 if query.casefold().strip() in text.casefold() else 0.0
    return min(1.0, matched / max(1, sum(q.values())) + phrase_bonus)


def _cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def index_document_embeddings(record: DocumentRecord) -> tuple[DocumentRecord, str]:
    st = status()
    if not (st.online and st.embed_model_ready):
        return record, "lexical-only"
    try:
        vectors: list[list[float]] = []
        texts = [c.text for c in record.chunks]
        for start in range(0, len(texts), 16):
            vectors.extend(embed_texts(texts[start:start + 16]))
        for chunk, vector in zip(record.chunks, vectors):
            chunk.embedding = vector
        record.indexed_with_embeddings = bool(vectors)
        return record, "ollama-embeddings" if vectors else "lexical-only"
    except OllamaError:
        return record, "lexical-only"


def all_chunks(records: list[DocumentRecord]) -> list[DocumentChunk]:
    return [chunk for record in records for chunk in record.chunks]


def retrieve(
    query: str,
    records: list[DocumentRecord],
    *,
    top_k: int = 4,
    use_semantic: bool = True,
) -> tuple[list[RetrievalHit], str]:
    chunks = all_chunks(records)
    if not query.strip() or not chunks:
        return [], "none"

    query_embedding: list[float] | None = None
    semantic_possible = use_semantic and any(c.embedding for c in chunks)
    if semantic_possible:
        try:
            query_embedding = embed_texts([query])[0]
        except OllamaError:
            query_embedding = None

    hits: list[RetrievalHit] = []
    for chunk in chunks:
        lex = _lexical_score(query, chunk.text)
        sem = _cosine(query_embedding, chunk.embedding) if query_embedding else 0.0
        # Lexical evidence remains part of the score so retrieval still behaves sensibly
        # when an embedding model is unavailable or when exact tender terms matter.
        score = (0.38 * lex + 0.62 * max(0.0, sem)) if query_embedding else lex
        if score > 0:
            hits.append(RetrievalHit(chunk=chunk, score=score, lexical_score=lex, semantic_score=sem))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k], "hybrid" if query_embedding else "lexical"
