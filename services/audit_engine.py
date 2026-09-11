from __future__ import annotations

import re

from services.models import AuditResult, Requirement
from services.ollama_client import OllamaError, chat_json, status


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9.%]+", " ", text.casefold()).strip()


def _snippet(text: str, terms: list[str], span: int = 240) -> tuple[str, str]:
    lower = text.casefold()
    positions = [lower.find(t.casefold()) for t in terms if t and lower.find(t.casefold()) >= 0]
    pos = min(positions) if positions else -1
    if pos < 0:
        return "", ""
    start = max(0, pos - span)
    end = min(len(text), pos + span)
    excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
    return "document text", excerpt


def _section_presence(text: str, req: Requirement) -> AuditResult:
    raw_target = (req.target or req.title).strip()
    # Prefer the structured target from requirement extraction. Only derive one
    # from source text when the extractor could not supply it.
    candidates: list[str] = []
    if req.target:
        candidates.append(req.target.strip())
        simplified = re.sub(r"(?i)\s+(?:section|plan)$", "", req.target.strip()).strip()
        if simplified and simplified not in candidates:
            candidates.append(simplified)
    else:
        derived = re.sub(r"(?i)^.*?(?:include|contain|provide)\s+(?:an?\s+)?", "", raw_target)
        derived = re.sub(r"[.;].*$", "", derived).strip(" .")
        if derived:
            candidates.append(derived)
            simplified = re.sub(r"(?i)\s+(?:section|plan)$", "", derived).strip()
            if simplified and simplified not in candidates:
                candidates.append(simplified)

    norm_text = _norm(text)
    for c in candidates:
        if c and _norm(c) in norm_text:
            loc, excerpt = _snippet(text, [c])
            return AuditResult(req, "PASS", f"Required section/concept detected: {c}", loc, excerpt)
    label = candidates[0] if candidates else req.title
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
    # Conservative generic rule: any observed value satisfying the threshold can prove the requirement.
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
                "You are a conservative compliance verifier. Compare ONE requirement against the supplied document. "
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
    # Never fake certainty if a semantic requirement could not be verified.
    phrase_result = _phrase(text, req)
    if phrase_result.status == "PASS":
        phrase_result.evidence = "Deterministic concept coverage suggests this requirement is satisfied."
        return phrase_result
    return AuditResult(req, "REVIEW", "Semantic requirement needs AI or human review; deterministic evidence was insufficient.")


def audit_document(text: str, requirements: list[Requirement], *, use_ollama: bool = True) -> list[AuditResult]:
    results: list[AuditResult] = []
    for req in requirements:
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
    mandatory = [r for r in results if r.requirement.mandatory]
    if not mandatory:
        return None
    passed = sum(1 for r in mandatory if r.status == "PASS")
    return round(100 * passed / len(mandatory))
