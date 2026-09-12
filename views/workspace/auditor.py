"""Workspace right column: actual compliance results derived from audit output."""

from __future__ import annotations

import html

import streamlit as st

from components.widgets import gauge
from core.config import ACCENT, DANGER, MUTED, SUCCESS, WARN
from core.state import audit_revealed, k
from services.audit_engine import compliance_score


def render(cat: str, cfg: dict) -> None:
    if not audit_revealed(cat):
        _render_idle(cat)
        return
    _render_results(cat)


def _render_idle(cat: str) -> None:
    reqs = st.session_state[k(cat, "requirements")]
    st.markdown('<div class="vc-sec-label">Compliance Gap Auditor</div>', unsafe_allow_html=True)
    detail = (
        f"{len(reqs)} requirements extracted and ready for assessment."
        if reqs else
        "Upload an RFP/checklist to extract requirements, then upload a document to verify."
    )
    st.markdown(
        f"""
        <div class="vc-card vc-auditor-idle">
          <div class="ring">⏳</div>
          <h4>No assessment on record</h4>
          <p>{html.escape(detail)}</p>
          <p style="margin-top:10px;">Run <b>Gap Analysis</b> after selecting the document under test.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_results(cat: str) -> None:
    results = st.session_state[k(cat, "audit_results")]
    score = compliance_score(results)
    content_results = [r for r in results if r.requirement.scope == "report_content"]
    fail_n = sum(1 for r in content_results if r.status == "FAIL")
    content_review_n = sum(1 for r in content_results if r.status == "REVIEW")
    manual_n = sum(1 for r in results if r.status == "REVIEW" and r.requirement.scope != "report_content")
    na_n = sum(1 for r in results if r.status == "N/A")

    if score == 100 and not fail_n and not content_review_n:
        if manual_n or na_n:
            color, caption = SUCCESS, "Written Content Compliant"
        else:
            color, caption = SUCCESS, "Fully Compliant"
    elif fail_n:
        color, caption = DANGER, "Action Required"
    else:
        color, caption = WARN, "Content Review Required"

    shown_score = 0 if score is None else score
    st.markdown('<div class="vc-sec-label">Compliance Gap Auditor</div>', unsafe_allow_html=True)
    st.markdown(gauge(shown_score, caption, color), unsafe_allow_html=True)
    st.markdown(
        f'<div style="text-align:center;margin:4px 0 12px 0;">'
        f'<div style="font-size:0.86rem;font-weight:600;color:{color};">'
        f'{"—" if score is None else str(score)+"%"} — {caption}</div>'
        f'<div style="font-size:0.68rem;color:{MUTED};margin-top:4px;line-height:1.5;">'
        f'<b>Content controls:</b> {len(content_results)} · FAIL {fail_n} · REVIEW {content_review_n}'
        f' &nbsp;|&nbsp; Manual {manual_n} · N/A {na_n}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)

    unresolved = [
        r for r in content_results if r.status in {"FAIL", "REVIEW"}
    ]
    if unresolved:
        first = unresolved[0]
        box = "vc-alert-red" if first.status == "FAIL" else "vc-card"
        st.markdown(
            f'<div class="{box}"><div class="t">{html.escape(first.status)} — '
            f'{html.escape(first.requirement.title)}</div>'
            f'<div class="d">{html.escape(first.evidence)}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        detail = (
            "All written-content requirements passed. Manual/external and out-of-scope controls remain listed below."
            if manual_n or na_n else
            "The current audited document satisfies every extracted written-content requirement."
        )
        st.markdown(
            f'<div class="vc-alert-green"><div class="t">Written-content audit complete</div>'
            f'<div class="d">{html.escape(detail)} Human approval remains a separate governance step.</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="vc-sec-label" style="margin-top:14px;">Requirement Checklist</div>', unsafe_allow_html=True)
    items: list[str] = []
    for result in results:
        if result.status == "PASS":
            icon, col = "✔", SUCCESS
        elif result.status == "FAIL":
            icon, col = "✘", DANGER
        elif result.status == "N/A":
            icon, col = "–", MUTED
        else:
            icon, col = "?", WARN
        title = html.escape(result.requirement.title)
        evidence = html.escape(result.evidence)
        items.append(
            f'<div class="vc-check"><div class="ic" style="color:{col};">{icon}</div>'
            f'<div class="tx"><b style="color:{col};">{result.status}</b> — {title}'
            f'<div style="font-size:0.63rem;color:{MUTED};margin-top:3px;">{evidence}</div></div></div>'
        )
    st.markdown("".join(items), unsafe_allow_html=True)

    engine = st.session_state[k(cat, "requirement_engine")] or "unknown"
    st.markdown(
        f'<div style="font-size:0.66rem;color:{MUTED};margin-top:12px;line-height:1.6;">'
        f'Requirements extracted via <b>{html.escape(engine)}</b>. The automatic score uses only written-content '
        'PASS/FAIL controls; manual formatting/plagiarism reviews and N/A presentation/submission controls are shown separately. '
        'Human approval never forces a compliance score.</div>',
        unsafe_allow_html=True,
    )
