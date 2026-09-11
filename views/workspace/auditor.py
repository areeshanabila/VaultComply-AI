"""
Workspace right column: the compliance gap auditor.

Extracted from ``render_auditor_column`` in section 8 of the original app.py.
The score is derived, not stored: 67% until the clause is signed off, 100%
after — so the gauge can never disagree with the sign-off state.
"""

from __future__ import annotations

import datetime as dt

import streamlit as st

from components.widgets import gauge
from core.config import ACCENT, CURRENT_USER, DANGER, MUTED, SUCCESS
from core.state import audit_revealed, k


def render(cat: str, cfg: dict) -> None:
    """Idle placeholder until an audit action has run, full panel afterwards.

    Scoring a document the user has neither analysed nor drafted would be
    asserting a finding out of thin air, so the gauge, the disqualification
    alert and the statutory checklist are all held back until
    :func:`core.state.audit_revealed` says there is something to report.

    The idle card keeps the same column width as the full panel, so the
    three-column layout metrics do not shift when it swaps over.
    """
    if not audit_revealed(cat):
        _render_idle(cfg)
        return

    _render_results(cat, cfg)


def _render_idle(cfg: dict) -> None:
    st.markdown('<div class="vc-sec-label">Compliance Gap Auditor</div>',
                unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="vc-card vc-auditor-idle">
          <div class="ring">⏳</div>
          <h4>No assessment on record</h4>
          <p>This document has not been assessed yet.</p>
          <p style="margin-top:10px;">Run a <b>Gap Analysis</b> to assess the intake against the
          statutory baseline, or <b>Generate a Draft Clause</b>. Either one scores this
          document and fills this panel.</p>
          <div class="basis">
            <div class="vc-mono">STATUTORY BASELINE</div>
            {cfg['audit_basis']}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_results(cat: str, cfg: dict) -> None:
    approved = st.session_state[k(cat, "approved")]
    score = 100 if approved else 67
    color = SUCCESS if approved else DANGER
    caption = "Fully Compliant" if approved else "Action Required"

    st.markdown('<div class="vc-sec-label">Compliance Gap Auditor</div>',
                unsafe_allow_html=True)
    st.markdown(gauge(score, caption, color), unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="text-align:center;margin:4px 0 12px 0;">
          <div style="font-size:0.86rem;font-weight:600;color:{color};">
            {score}% — {caption}</div>
          <div style="font-size:0.68rem;color:{MUTED};margin-top:4px;line-height:1.5;">
            <b>Statutory baseline:</b><br/>{cfg['audit_basis']}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    if st.session_state[k(cat, "analysed")]:
        st.markdown(
            f'<div style="font-size:0.68rem;color:{ACCENT};text-align:center;margin-bottom:8px;">'
            f"Assessed {dt.datetime.now():%H:%M} MYT · "
            f"{len(cfg['passed']) + 1} mandatory controls evaluated</div>",
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)

    if approved:
        st.markdown(
            f"""
            <div class="vc-alert-green">
              <div class="t">Mandatory Clause Satisfied</div>
              <div class="d">Section 4.2 Disaster Recovery SLA is present, cited to
              {cfg['citation'][0]} p.{cfg['citation'][1]}, and signed off by {CURRENT_USER}.
              Disqualification risk cleared.</div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="vc-alert-red">
              <div class="t">Missing Mandatory Clause</div>
              <div class="d"><b>{cfg['missing']}</b><br/>
              Disqualification Risk — mandated by {cfg['audit_basis'].split(' + ')[0]}.
              Submission will be rejected at the ePerolehan compliance gate without this clause.</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="vc-sec-label" style="margin-top:14px;">Statutory Checklist</div>',
                unsafe_allow_html=True)

    items = "".join(
        f'<div class="vc-check"><div class="ic" style="color:{SUCCESS};">✔</div>'
        f'<div class="tx">{t}</div></div>'
        for t in cfg["passed"]
    )
    dr_icon = f'<div class="ic" style="color:{SUCCESS};">✔</div>' if approved \
        else f'<div class="ic" style="color:{DANGER};">✘</div>'
    dr_color = SUCCESS if approved else DANGER
    items += (
        f'<div class="vc-check">{dr_icon}'
        f'<div class="tx" style="color:{dr_color};font-weight:600;">'
        f'Section 4.2 Disaster Recovery SLA</div></div>'
    )
    st.markdown(items, unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:0.66rem;color:{MUTED};margin-top:12px;line-height:1.6;">'
        f"Evaluated against <b>{len(cfg['passed']) + 1}</b> mandatory controls drawn from the "
        "statutory baseline documents. Scoring is deterministic and reproducible."
        "</div>",
        unsafe_allow_html=True,
    )
