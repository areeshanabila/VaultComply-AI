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
    fail_n = sum(1 for r in results if r.status == "FAIL")
    review_n = sum(1 for r in results if r.status == "REVIEW")

    if score == 100 and not fail_n and not review_n:
        color, caption = SUCCESS, "Fully Compliant"
    elif fail_n:
        color, caption = DANGER, "Action Required"
    else:
        color, caption = WARN, "Review Required"

    shown_score = 0 if score is None else score
    st.markdown('<div class="vc-sec-label">Compliance Gap Auditor</div>', unsafe_allow_html=True)
    st.markdown(gauge(shown_score, caption, color), unsafe_allow_html=True)
    st.markdown(
        f'<div style="text-align:center;margin:4px 0 12px 0;">'
        f'<div style="font-size:0.86rem;font-weight:600;color:{color};">'
        f'{"—" if score is None else str(score)+"%"} — {caption}</div>'
        f'<div style="font-size:0.68rem;color:{MUTED};margin-top:4px;line-height:1.5;">'
        f'<b>Requirements:</b> {len(results)} · FAIL {fail_n} · REVIEW {review_n}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)

    unresolved = [r for r in results if r.status in {"FAIL", "REVIEW"}]
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
        st.markdown(
            '<div class="vc-alert-green"><div class="t">All mandatory requirements passed</div>'
            '<div class="d">The current audited document satisfies every extracted mandatory requirement. '
            'Human approval remains a separate governance step.</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="vc-sec-label" style="margin-top:14px;">Requirement Checklist</div>', unsafe_allow_html=True)
    items: list[str] = []
    for result in results:
        if result.status == "PASS":
            icon, col = "✔", SUCCESS
        elif result.status == "FAIL":
            icon, col = "✘", DANGER
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
        f'Requirements extracted via <b>{html.escape(engine)}</b>. Score is derived from mandatory PASS results; '
        'human approval never forces a compliance score.</div>',
        unsafe_allow_html=True,
    )
