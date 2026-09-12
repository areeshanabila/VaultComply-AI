from __future__ import annotations

import re

from services.models import AuditResult, Requirement
from services.ollama_client import OllamaError, chat_json, status


def _norm(text: str) -> str:
    text = text.casefold()
    # Normalise a few common UK/US variants so headings do not false-fail.
    text = text.replace("organizational", "organisational")
    text = text.replace("organization", "organisation")
    text = text.replace("behavioral", "behavioural")
    text = text.replace("behavior", "behaviour")
    return re.sub(r"[^a-z0-9.%]+", " ", text).strip()


def _strip_heading_prefix(text: str) -> str:
    value = re.sub(r"\s+", " ", text).strip(" .:-")
    value = re.sub(r"(?i)^\s*PART\s+\d+\s*[:.)-]?\s*", "", value)
    value = re.sub(r"(?i)^\s*\d+(?:\.\d+)*\s*[:.)-]?\s*", "", value)
    return value.strip(" .:-")


def _section_candidates(req: Requirement) -> list[str]:
    raw: list[str] = []
    for value in (req.target, req.title, req.source_text):
        if not value:
            continue
        value = re.sub(r"\s+", " ", value).strip()
        # For source quotes / titles such as "PART 1: Full Heading", use the
        # meaningful heading after the PART prefix as an alias.
        part = re.search(r"(?i)\bPART\s+\d+\s*:\s*(.+)$", value)
        if part:
            raw.append(part.group(1).strip())
        raw.append(value)
        raw.append(_strip_heading_prefix(value))
        simplified = re.sub(r"(?i)\s+(?:section|plan)$", "", _strip_heading_prefix(value)).strip()
        if simplified:
            raw.append(simplified)

    out: list[str] = []
    seen: set[str] = set()
    for candidate in raw:
        n = _norm(candidate)
        if len(n) < 4 or n in seen:
            continue
        # Literal PART 1 / PART 2 tokens are not meaningful enough by themselves.
        if re.fullmatch(r"part\s+\d+", n):
            continue
        seen.add(n)
        out.append(candidate)
    return out


def _snippet(text: str, terms: list[str], span: int = 240) -> tuple[str, str]:
    lower = text.casefold()
    positions = [lower.find(t.casefold()) for t in terms if t and lower.find(t.casefold()) >= 0]
    pos = min(positions) if positions else -1
    if pos < 0:
        # Try normalised terms against normalised text only to locate approximate evidence.
        norm_text = _norm(text)
        for term in terms:
            n = _norm(term)
            if n and n in norm_text:
                return "document text", term
        return "", ""
    start = max(0, pos - span)
    end = min(len(text), pos + span)
    excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
    return "document text", excerpt


def _section_presence(text: str, req: Requirement) -> AuditResult:
    candidates = _section_candidates(req)
    norm_text = _norm(text)

    # Exact semantic heading match after normalisation handles numbering changes,
    # punctuation, line wraps and common UK/US spelling variants.
    for candidate in candidates:
        nc = _norm(candidate)
        if nc and nc in norm_text:
            loc, excerpt = _snippet(text, [candidate])
            return AuditResult(req, "PASS", f"Required section/concept detected: {_strip_heading_prefix(candidate)}", loc, excerpt)

    # Conservative token-overlap fallback for a heading that is slightly reworded.
    stop = {"the", "and", "for", "with", "of", "to", "a", "an", "part", "section", "system"}
    doc_lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) <= 220]
    for candidate in candidates:
        target_tokens = {t for t in _norm(_strip_heading_prefix(candidate)).split() if len(t) > 2 and t not in stop}
        if len(target_tokens) < 2:
            continue
        for line in doc_lines:
            line_tokens = {t for t in _norm(_strip_heading_prefix(line)).split() if len(t) > 2 and t not in stop}
            if not line_tokens:
                continue
            overlap = len(target_tokens & line_tokens) / len(target_tokens)
            if overlap >= 0.75:
                return AuditResult(
                    req, "PASS",
                    f"Equivalent section heading detected: {line}",
                    "document heading", line[:800],
                )

    label = _strip_heading_prefix(candidates[0]) if candidates else _strip_heading_prefix(req.title)
    return AuditResult(req, "FAIL", f"Required section was not detected: {label}")


def _numeric(text: str, req: Requirement) -> AuditResult:
    unit = (req.unit or "").casefold()
    values: list[float] = []
    if unit == "%":
        values = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\s*%", text)]
    elif "week" in unit:
        values = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\s*[- ]?weeks?", text, re.I)]
    elif "hour" in unit:
        values = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\s*[- ]?hours?", text, re.I)]
    elif "minute" in unit:
        values = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\s*[- ]?minutes?", text, re.I)]
    else:
        values = [float(v) for v in re.findall(r"\b(\d+(?:\.\d+)?)\b", text)]

    if not values:
        return AuditResult(req, "FAIL", f"No numeric evidence with unit '{req.unit or 'number'}' was detected.")
    satisfying = [v for v in values if (req.minimum is None or v >= req.minimum) and (req.maximum is None or v <= req.maximum)]
    if satisfying:
        v = satisfying[0]
        loc, excerpt = _snippet(text, [f"{v:g}"])
        return AuditResult(req, "PASS", f"Detected value {v:g} {req.unit or ''} satisfies the threshold.", loc, excerpt)
    threshold = []
    if req.minimum is not None:
        threshold.append(f">= {req.minimum:g}")
    if req.maximum is not None:
        threshold.append(f"<= {req.maximum:g}")
    return AuditResult(req, "FAIL", f"Observed values {values[:6]} do not satisfy {' and '.join(threshold)} {req.unit or ''}.")


def _phrase(text: str, req: Requirement) -> AuditResult:
    norm = _norm(text)
    concepts = [c for c in req.expected_concepts if len(_norm(c)) >= 3]
    if not concepts:
        concepts = re.findall(r"[A-Za-z][A-Za-z0-9/-]{3,}", req.source_text)[:6]
    matched = [c for c in concepts if _norm(c) in norm]
    required = max(1, min(len(concepts), 3))
    if len(matched) >= required:
        loc, excerpt = _snippet(text, matched)
        return AuditResult(req, "PASS", f"Detected supporting concepts: {', '.join(matched[:6])}.", loc, excerpt)
    return AuditResult(req, "FAIL", f"Only {len(matched)}/{required} expected concepts were detected.")


def _semantic(text: str, req: Requirement, *, use_ollama: bool) -> AuditResult:
    if use_ollama:
        st = status()
        if st.online and st.chat_model_ready:
            system = (
                "You are a conservative compliance verifier. Compare ONE written-document requirement against the supplied document. "
                "Return JSON with status PASS, FAIL, or REVIEW; evidence; excerpt. PASS only when the document clearly satisfies it. "
                "FAIL when clearly missing or contradicted. REVIEW when ambiguous. Do not use outside knowledge. "
                "Treat semantically equivalent Bahasa Melayu and English wording as equivalent even when the phrases are not verbatim."
            )
            user = f"REQUIREMENT:\n{req.source_text or req.title}\n\nDOCUMENT:\n{text[:12000]}"
            try:
                payload = chat_json([
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ], timeout=420, num_predict=500)
                if isinstance(payload, dict):
                    s = str(payload.get("status", "REVIEW")).upper()
                    if s not in {"PASS", "FAIL", "REVIEW"}:
                        s = "REVIEW"
                    return AuditResult(
                        req,
                        s,
                        str(payload.get("evidence") or "Semantic verification completed."),
                        "semantic review",
                        str(payload.get("excerpt") or "")[:800],
                    )
            except OllamaError:
                pass
    phrase_result = _phrase(text, req)
    if phrase_result.status == "PASS":
        phrase_result.evidence = "Deterministic concept coverage suggests this requirement is satisfied."
        return phrase_result
    return AuditResult(req, "REVIEW", "Semantic requirement needs AI or human review; deterministic evidence was insufficient.")


def audit_document(text: str, requirements: list[Requirement], *, use_ollama: bool = True) -> list[AuditResult]:
    results: list[AuditResult] = []
    for req in requirements:
        # These controls are important, but cannot honestly be proven by looking
        # for words inside the report text.
        if req.scope == "report_format":
            results.append(AuditResult(
                req, "REVIEW",
                "Manual formatting review required. The current text parser does not verify font, line spacing or page-number placement.",
            ))
            continue
        if req.scope == "academic_integrity":
            results.append(AuditResult(
                req, "REVIEW",
                "External similarity/plagiarism check required; keyword presence in the report is not valid evidence.",
            ))
            continue
        if req.scope in {"presentation", "submission", "administrative"} or req.rule_type == "not_applicable":
            results.append(AuditResult(
                req, "N/A",
                "Not applicable to the written-document content audit.",
            ))
            continue

        if req.rule_type == "section_presence":
            result = _section_presence(text, req)
        elif req.rule_type == "numeric_threshold":
            result = _numeric(text, req)
        elif req.rule_type == "phrase_presence":
            result = _phrase(text, req)
        elif req.rule_type == "manual_review":
            result = AuditResult(req, "REVIEW", "Requirement explicitly requires human review.")
        else:
            result = _semantic(text, req, use_ollama=use_ollama)
        results.append(result)
    return results


def compliance_score(results: list[AuditResult]) -> int | None:
    """Score only automatically decidable written-content controls.

    Manual formatting/plagiarism reviews and N/A presentation/submission controls
    are shown to the user but are not counted as failures in the automatic score.
    A semantic REVIEW is likewise not converted into a fabricated failure.
    """
    scoreable = [
        r for r in results
        if r.requirement.mandatory
        and r.requirement.scope == "report_content"
        and r.status in {"PASS", "FAIL"}
    ]
    if not scoreable:
        return None
    passed = sum(1 for r in scoreable if r.status == "PASS")
    return round(100 * passed / len(scoreable))
