from __future__ import annotations

import re

from services.models import DocumentRecord, Requirement
from services.ollama_client import OllamaError, chat_json, status

_ALLOWED = {
    "section_presence", "phrase_presence", "numeric_threshold",
    "semantic_requirement", "manual_review",
}


def _source_page(record: DocumentRecord, source_text: str) -> int:
    needle = re.sub(r"\s+", " ", source_text).strip().casefold()
    if not needle:
        return 1
    for chunk in record.chunks:
        hay = re.sub(r"\s+", " ", chunk.text).casefold()
        if needle[:100] in hay or needle in hay:
            return chunk.page
    return 1


def _fallback(record: DocumentRecord) -> list[Requirement]:
    # Keep sentence boundaries and surviving line boundaries from PDF/DOCX extraction.
    units = re.split(r"(?<=[.!?;])\s+|\n+", record.text)
    requirements: list[Requirement] = []
    marker = re.compile(
        r"\b(must|shall|required|mandatory|compulsory|at least|minimum|maximum|"
        r"no more than|not exceed|within)\b", re.I,
    )
    for raw in units:
        sentence = re.sub(r"\s+", " ", raw).strip(" -•\t")
        if len(sentence) < 14 or len(sentence) > 420 or not marker.search(sentence):
            continue

        lower = sentence.casefold()
        if re.fullmatch(r"(?:mandatory|required|compulsory) requirements?[:;]?", lower):
            continue
        rule_type = "semantic_requirement"
        target = None
        minimum = maximum = None
        expected = None
        unit = None

        section_match = re.search(
            r"(?:include|contain|provide)\s+(?:an?\s+)?(.{3,90}?)(?:\s+section|\s+plan)(?:[.,;]|$)",
            sentence, re.I,
        )
        if section_match:
            target = section_match.group(1).strip() + (" Plan" if " plan" in lower else " Section")
            rule_type = "section_presence"

        pct = re.search(r"(?:minimum|at least)\s+(\d+(?:\.\d+)?)\s*%", lower)
        max_pct = re.search(r"(?:maximum|no more than|not exceed)\s+(\d+(?:\.\d+)?)\s*%", lower)
        weeks = re.search(r"(?:within|no more than|not exceed)\s+(\d+(?:\.\d+)?)\s*weeks?", lower)
        if pct:
            rule_type, minimum, unit = "numeric_threshold", float(pct.group(1)), "%"
        elif max_pct:
            rule_type, maximum, unit = "numeric_threshold", float(max_pct.group(1)), "%"
        elif weeks:
            rule_type, maximum, unit = "numeric_threshold", float(weeks.group(1)), "weeks"

        tokens = [t for t in re.findall(r"[A-Za-z][A-Za-z0-9/-]{2,}", sentence) if t.casefold() not in {
            "the", "and", "must", "shall", "include", "required", "proposal", "section", "within",
            "current", "state", "minimum", "maximum", "after", "before", "from", "with",
        }]
        requirements.append(Requirement(
            code=f"REQ-{len(requirements)+1:03d}",
            title=sentence[:150],
            mandatory=True,
            source_text=sentence,
            source_page=_source_page(record, sentence),
            rule_type=rule_type,
            target=target,
            minimum=minimum,
            maximum=maximum,
            expected=expected,
            unit=unit,
            expected_concepts=tokens[:8],
        ))
    return requirements


def _ollama_segments(record: DocumentRecord, max_chars: int = 6500) -> list[str]:
    segments: list[str] = []
    current: list[str] = []
    size = 0
    for chunk in record.chunks:
        tagged = f"[PAGE {chunk.page}]\n{chunk.text}"
        if current and size + len(tagged) > max_chars:
            segments.append("\n\n".join(current))
            current, size = [], 0
        current.append(tagged)
        size += len(tagged)
    if current:
        segments.append("\n\n".join(current))
    return segments or [record.text[:max_chars]]


def extract_requirements(record: DocumentRecord, *, prefer_ollama: bool = True) -> tuple[list[Requirement], str]:
    st = status()
    if prefer_ollama and st.online and st.chat_model_ready:
        system = (
            "You extract auditable document requirements from an RFP/checklist. "
            "Use ONLY the supplied source. Never add external requirements. Return JSON with key requirements. "
            "Each item must contain title, source_text (an exact short quote from the source), mandatory, "
            "rule_type, target, minimum, maximum, expected, unit, expected_concepts. "
            "rule_type must be one of section_presence, phrase_presence, numeric_threshold, semantic_requirement, manual_review. "
            "Split compound mandatory rules when useful. Cross-lingual Bahasa Melayu/English wording may be semantically equivalent. "
            "Use null when a field is not stated. Do not treat headings such as 'MANDATORY REQUIREMENTS' as requirements themselves."
        )
        out: list[Requirement] = []
        seen: set[str] = set()
        compact_source = re.sub(r"\s+", " ", record.text).casefold()
        try:
            for segment in _ollama_segments(record):
                payload = chat_json([
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"SOURCE DOCUMENT EXCERPT:\n{segment}"},
                ], timeout=600, num_predict=1400)
                items = payload.get("requirements", []) if isinstance(payload, dict) else payload
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    source_text = str(item.get("source_text") or "").strip()
                    compact_quote = re.sub(r"\s+", " ", source_text).casefold()
                    # Grounding gate: reject model-created obligations that cannot be tied
                    # back to an exact quote in the uploaded RFP/checklist.
                    if not compact_quote or compact_quote not in compact_source:
                        continue
                    key = compact_quote
                    if key in seen:
                        continue
                    seen.add(key)
                    rule = str(item.get("rule_type") or "semantic_requirement")
                    if rule not in _ALLOWED:
                        rule = "semantic_requirement"
                    concepts = item.get("expected_concepts") or []
                    if not isinstance(concepts, list):
                        concepts = []
                    out.append(Requirement(
                        code=f"REQ-{len(out)+1:03d}",
                        title=str(item.get("title") or source_text)[:150],
                        mandatory=bool(item.get("mandatory", True)),
                        source_text=source_text,
                        source_page=_source_page(record, source_text),
                        rule_type=rule,
                        target=(str(item["target"]).strip() if item.get("target") else None),
                        minimum=_num(item.get("minimum")),
                        maximum=_num(item.get("maximum")),
                        expected=item.get("expected"),
                        unit=(str(item["unit"]).strip() if item.get("unit") else None),
                        expected_concepts=[str(x) for x in concepts if str(x).strip()][:10],
                    ))
            if out:
                return out, "ollama"
        except OllamaError:
            # The deterministic extractor remains available if any model call fails.
            pass
    return _fallback(record), "deterministic-fallback"


def _num(value):
    try:
        return None if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return None
