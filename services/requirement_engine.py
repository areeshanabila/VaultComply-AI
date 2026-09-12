from __future__ import annotations

import re

from services.models import DocumentRecord, Requirement
from services.ollama_client import OllamaError, chat_json, status

_ALLOWED = {
    "section_presence", "phrase_presence", "numeric_threshold",
    "semantic_requirement", "manual_review", "not_applicable",
}

_SCOPES = {
    "report_content", "report_format", "academic_integrity",
    "presentation", "submission", "administrative",
}

_STOPWORDS = {
    "the", "and", "must", "shall", "include", "required", "proposal", "section", "within",
    "current", "state", "minimum", "maximum", "after", "before", "from", "with", "this",
    "that", "for", "into", "using", "student", "students", "system", "report", "project",
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


def _concepts(text: str, limit: int = 8) -> list[str]:
    tokens = [
        t for t in re.findall(r"[A-Za-z][A-Za-z0-9/-]{2,}", text)
        if t.casefold() not in _STOPWORDS
    ]
    out: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        key = token.casefold()
        if key not in seen:
            seen.add(key)
            out.append(token)
        if len(out) >= limit:
            break
    return out


def _classify_scope(*parts: str | None) -> str:
    text = " ".join(str(p or "") for p in parts)
    compact = re.sub(r"\s+", " ", text).casefold()

    if re.search(r"\bsection\s*b\b", compact) or any(x in compact for x in (
        "recorded presentation", "presentation requirement", "a1 digital poster",
        "project presentation", "present their project",
    )):
        return "presentation"

    if any(x in compact for x in (
        "plagiarism", "similarity index", "turnitin", "academic misconduct",
        "examination misconduct", "cheating",
    )):
        return "academic_integrity"

    if any(x in compact for x in (
        "report formatting requirements", "font size", "line spacing",
        "page number", "bottom centre", "bottom center", "font: arial",
    )):
        return "report_format"

    if any(x in compact for x in (
        "upload the following", "submit all project deliverables", "submission to",
        "date of submission", "saved and submitted both", "e-learning",
    )):
        return "submission"

    if any(x in compact for x in (
        "instruction to candidates", "warning", "punishment", "disciplinary actions",
        "build the design requirements of an effective ai-powered talent management system",
    )):
        return "administrative"

    return "report_content"


def _heading_target(text: str) -> str:
    """Return the semantic heading after PART/number prefixes when possible."""
    line = re.sub(r"\s+", " ", text).strip(" -•\t")
    m = re.search(r"(?i)\bPART\s+\d+\s*:\s*(.+)$", line)
    if m:
        return m.group(1).strip(" .:-")
    m = re.match(r"(?i)^\s*\d+(?:\.\d+)*\s*[:.)-]?\s*(.+)$", line)
    if m:
        return m.group(1).strip(" .:-")
    return line.strip(" .:-")


def _structured_assessment_requirements(record: DocumentRecord) -> list[Requirement]:
    """Detect academic/project briefs that explicitly define PART 1..N.

    When a source clearly provides top-level PART headings, those headings are the
    correct content-level controls for Verify Existing Document. Detailed rubric,
    presentation and administrative instructions are not converted into extra
    document-section failures.
    """
    pattern = re.compile(r"(?im)^[\s.\-•·]*(PART\s+([1-9]\d*)\s*:\s*([^\n]{3,180}))\s*$")
    matches = list(pattern.finditer(record.text))
    numbers = {int(m.group(2)) for m in matches}
    if len(numbers) < 3:
        return []

    requirements: list[Requirement] = []
    seen: set[int] = set()
    for match in matches:
        number = int(match.group(2))
        if number in seen:
            continue
        seen.add(number)
        source_text = re.sub(r"\s+", " ", match.group(1)).strip()
        target = _heading_target(source_text)
        requirements.append(Requirement(
            code="",
            title=source_text[:150],
            mandatory=True,
            source_text=source_text,
            source_page=_source_page(record, source_text),
            rule_type="section_presence",
            target=target,
            expected_concepts=_concepts(target),
            scope="report_content",
        ))

    requirements.sort(key=lambda r: int(re.search(r"(?i)PART\s+(\d+)", r.title).group(1)))
    return requirements


def _auxiliary_assessment_controls(record: DocumentRecord) -> list[Requirement]:
    """Add important non-content controls without mis-scoring the written report."""
    text = record.text
    controls: list[Requirement] = []

    # Formatting is real, but the current text parser cannot reliably prove font,
    # line spacing or page-number placement. Surface it as manual review.
    format_match = re.search(
        r"(?is)(Report Formatting Requirements.{0,320}?(?:Page Number[^\n.]*|Bottom centre|Bottom center))",
        text,
    )
    if format_match:
        quote = re.sub(r"\s+", " ", format_match.group(1)).strip()
        controls.append(Requirement(
            code="",
            title="Report Formatting Requirements",
            mandatory=True,
            source_text=quote[:420],
            source_page=_source_page(record, quote[:180]),
            rule_type="manual_review",
            target="Formatting",
            scope="report_format",
        ))

    # Similarity/plagiarism requires Turnitin or another external checker; keyword
    # presence in the report is not evidence of compliance.
    plagiarism_match = re.search(
        r"(?is)(No plagiarism[^\n.]{0,220}|PLAGIARISM.{0,220}?similarity[^\n.]{0,120})",
        text,
    )
    if plagiarism_match or re.search(r"(?i)\bplagiarism\b", text):
        quote = re.sub(r"\s+", " ", (plagiarism_match.group(1) if plagiarism_match else "Plagiarism / similarity requirement")).strip()
        controls.append(Requirement(
            code="",
            title="Plagiarism / Similarity Check",
            mandatory=True,
            source_text=quote[:420],
            source_page=_source_page(record, quote[:180]),
            rule_type="manual_review",
            target="Plagiarism similarity",
            scope="academic_integrity",
        ))

    # Presentation is a separate deliverable, so it is explicitly shown as N/A
    # rather than as a false failure against the written report.
    presentation_match = re.search(r"(?im)^\s*(SECTION\s+B\s*:\s*PRESENTATION[^\n]*)", text)
    if presentation_match:
        quote = re.sub(r"\s+", " ", presentation_match.group(1)).strip()
        controls.append(Requirement(
            code="",
            title="SECTION B: PRESENTATION",
            mandatory=True,
            source_text=quote,
            source_page=_source_page(record, quote),
            rule_type="not_applicable",
            target="Presentation",
            scope="presentation",
        ))

    return controls


def _renumber(requirements: list[Requirement]) -> list[Requirement]:
    for idx, req in enumerate(requirements, start=1):
        req.code = f"REQ-{idx:03d}"
    return requirements


def _fallback(record: DocumentRecord) -> list[Requirement]:
    # Structured academic/project briefs get a stable top-level content audit.
    structured = _structured_assessment_requirements(record)
    if structured:
        return _renumber(structured + _auxiliary_assessment_controls(record))

    # Generic RFP/checklist fallback: keep sentence boundaries and surviving line boundaries.
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

        scope = _classify_scope(sentence)
        rule_type = "semantic_requirement"
        target = None
        minimum = maximum = None
        expected = None
        unit = None

        if scope in {"report_format", "academic_integrity"}:
            rule_type = "manual_review"
        elif scope in {"presentation", "submission", "administrative"}:
            rule_type = "not_applicable"
        else:
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

        requirements.append(Requirement(
            code="",
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
            expected_concepts=_concepts(sentence),
            scope=scope,
        ))
    return _renumber(requirements)


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
    # If the document explicitly defines PART 1..N, deterministic structural
    # extraction is more reliable than asking an LLM to turn every instruction,
    # rubric item and presentation rule into a written-report failure.
    structured = _structured_assessment_requirements(record)
    if structured:
        return _renumber(structured + _auxiliary_assessment_controls(record)), "structured-assessment"

    st = status()
    if prefer_ollama and st.online and st.chat_model_ready:
        system = (
            "You extract auditable requirements from an RFP/checklist for a WRITTEN DOCUMENT audit. "
            "Use ONLY the supplied source. Never add external requirements. Return JSON with key requirements. "
            "Each item must contain title, source_text (an exact short quote from the source), mandatory, "
            "rule_type, target, minimum, maximum, expected, unit, expected_concepts, scope. "
            "rule_type must be one of section_presence, phrase_presence, numeric_threshold, semantic_requirement, manual_review, not_applicable. "
            "scope must be one of report_content, report_format, academic_integrity, presentation, submission, administrative. "
            "Use report_content only for content that must appear in the written document. "
            "Use report_format/manual_review for font, spacing, page numbering or layout rules. "
            "Use academic_integrity/manual_review for plagiarism or similarity checks. "
            "Use presentation/not_applicable for presentation or poster deliverables. "
            "Use submission or administrative/not_applicable for upload deadlines, exam rules and administrative instructions. "
            "Do NOT convert a broad instruction such as 'build/design the system' into a required section heading unless the source explicitly requires that heading. "
            "Cross-lingual Bahasa Melayu/English wording may be semantically equivalent. Use null when a field is not stated."
        )
        out: list[Requirement] = []
        seen: set[str] = set()
        compact_source = re.sub(r"\s+", " ", record.text).casefold()
        try:
            for segment in _ollama_segments(record):
                payload = chat_json([
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"SOURCE DOCUMENT EXCERPT:\n{segment}"},
                ], timeout=600, num_predict=1600)
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
                    if compact_quote in seen:
                        continue
                    seen.add(compact_quote)

                    title = str(item.get("title") or source_text)[:150]
                    target = str(item["target"]).strip() if item.get("target") else None
                    scope = str(item.get("scope") or "").strip().casefold()
                    if scope not in _SCOPES:
                        scope = _classify_scope(title, source_text, target)

                    rule = str(item.get("rule_type") or "semantic_requirement")
                    if rule not in _ALLOWED:
                        rule = "semantic_requirement"
                    # Deterministic safety override: the model cannot turn non-content
                    # controls into automatic written-document failures.
                    if scope in {"report_format", "academic_integrity"}:
                        rule = "manual_review"
                    elif scope in {"presentation", "submission", "administrative"}:
                        rule = "not_applicable"

                    # If a source explicitly says PART N: Full Heading, audit the semantic
                    # heading rather than the literal token "PART N".
                    if rule == "section_presence" and re.search(r"(?i)\bPART\s+\d+\s*:", source_text):
                        target = _heading_target(source_text)

                    concepts = item.get("expected_concepts") or []
                    if not isinstance(concepts, list):
                        concepts = []
                    out.append(Requirement(
                        code="",
                        title=title,
                        mandatory=bool(item.get("mandatory", True)),
                        source_text=source_text,
                        source_page=_source_page(record, source_text),
                        rule_type=rule,
                        target=target,
                        minimum=_num(item.get("minimum")),
                        maximum=_num(item.get("maximum")),
                        expected=item.get("expected"),
                        unit=(str(item["unit"]).strip() if item.get("unit") else None),
                        expected_concepts=[str(x) for x in concepts if str(x).strip()][:10],
                        scope=scope,
                    ))
            if out:
                return _renumber(out), "ollama-scoped"
        except OllamaError:
            # The deterministic extractor remains available if any model call fails.
            pass
    return _fallback(record), "deterministic-scoped-fallback"


def _num(value):
    try:
        return None if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return None
