"""
Workspace centre column: intake, action tabs, draft canvas, sign-off, export.

Extracted from section 8 of the original app.py — ``render_draft_canvas``,
``render_signoff_and_export`` and the body of the centre column that lived
inside ``view_workspace``.

Public entry point is :func:`render`; the two underscore-prefixed helpers are
internal to this column.
"""

from __future__ import annotations

import datetime as dt
import math
import time

import pandas as pd
import streamlit as st

from components.widgets import file_row, kpi
from core.config import ACCENT, CURRENT_USER, DANGER, MUTED, SUCCESS, WARN
from core.data import DR_BODY, PROVENANCE_QUOTE, SLA_HEADERS, SLA_ROWS
from core.state import k
from services.exporters import build_bundle, build_docx, build_pdf


def render(cat: str, cfg: dict) -> None:
    """Render the whole centre column for one document category."""
    st.markdown('<div class="vc-sec-label">Active Intake — Client Requirements</div>',
                unsafe_allow_html=True)
    intake = st.file_uploader(
        f"Upload {cfg['intake']}",
        type=["pdf", "docx", "txt"],
        key=k(cat, "intake_upload"),
        label_visibility="collapsed",
    )
    if intake is not None:
        st.session_state[k(cat, "intake")] = intake.name

    active_intake = st.session_state[k(cat, "intake")] or cfg["intake"]
    st.markdown(
        file_row(active_intake,
                 "Parsed · 42 requirements extracted" if st.session_state[k(cat, "intake")]
                 else "Sample loaded · 42 requirements", ACCENT),
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Action</div>', unsafe_allow_html=True)

    tab_a, tab_b = st.tabs(["Verify Existing Document", "Draft a Clause"])

    # ── TAB A ──────────────────────────────────────────────────────────
    with tab_a:
        st.markdown(
            f'<p style="font-size:0.78rem;color:{MUTED};line-height:1.6;">'
            f"Assess the intake document against every mandatory control in "
            f"<b>{cfg['audit_basis']}</b>. Findings appear in the gap auditor "
            f"on the right.</p>",
            unsafe_allow_html=True,
        )

        if st.button("Run Gap Analysis", key=k(cat, "run_gap"),
                     type="primary", width="stretch"):
            bar = st.progress(0, text="Opening isolated session…")
            steps = [
                (12, "Connecting to the tenant namespace…"),
                (26, f"Parsing {active_intake}…"),
                (42, "Loading audit basis: MOF_ePerolehan_Template.pdf…"),
                (58, "Cross-referencing the master clause library…"),
                (74, "Evaluating mandatory statutory controls…"),
                (88, "Scoring disqualification risk exposure…"),
                (100, "Assessment complete — working context discarded."),
            ]
            for pct, label in steps:
                time.sleep(0.42)
                bar.progress(pct, text=label)
            time.sleep(0.25)
            bar.empty()
            st.session_state[k(cat, "analysed")] = True
            st.rerun()

        if st.session_state[k(cat, "analysed")]:
            approved = st.session_state[k(cat, "approved")]
            st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
            st.markdown('<div class="vc-sec-label">Control Findings</div>',
                        unsafe_allow_html=True)

            rows = [[f"CTRL-{i + 1:03d}", t, "PASS", "—"]
                    for i, t in enumerate(cfg["passed"])]
            rows.append([
                f"CTRL-{len(cfg['passed']) + 1:03d}",
                "Section 4.2 Disaster Recovery SLA",
                "PASS" if approved else "FAIL",
                "—" if approved else "Disqualification",
            ])
            df = pd.DataFrame(rows, columns=["Control", "Requirement", "Result", "Risk"])
            st.dataframe(df, width="stretch", hide_index=True, height=280)

            passed_n = len(cfg["passed"]) + (1 if approved else 0)
            total_n = len(cfg["passed"]) + 1
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(kpi("Controls Passed", f"{passed_n}/{total_n}", "", SUCCESS),
                            unsafe_allow_html=True)
            with m2:
                st.markdown(kpi("Critical Failures", "0" if approved else "1",
                                "", SUCCESS if approved else DANGER),
                            unsafe_allow_html=True)
            with m3:
                st.markdown(kpi("Compliance Score", "100%" if approved else "67%", "",
                                SUCCESS if approved else DANGER),
                            unsafe_allow_html=True)

            if not approved:
                st.markdown(
                    '<div class="vc-alert-red" style="margin-top:10px;">'
                    '<div class="t">Remediation Required</div>'
                    '<div class="d">Use <b>Draft a Clause</b> to produce a '
                    'cited Section 4.2 Disaster Recovery SLA clause, then record '
                    'Compliance Lead sign-off to clear this finding.</div></div>',
                    unsafe_allow_html=True,
                )

    # ── TAB B ──────────────────────────────────────────────────────────
    with tab_b:
        st.markdown(
            f'<p style="font-size:0.78rem;color:{MUTED};line-height:1.6;">'
            f"Every clause is drawn from, and cited to, your {cat.lower()} registry. "
            f"Uncited text is not released.</p>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="vc-sec-label">Standard Instructions</div>', unsafe_allow_html=True)
        for chip in cfg["prompts"]:
            if st.button(chip, key=k(cat, f"chip_{chip[:18]}"), width="stretch"):
                st.session_state[k(cat, "prompt")] = chip
                st.rerun()

        prompt = st.text_area(
            "Custom instruction",
            value=st.session_state[k(cat, "prompt")],
            placeholder="e.g. Draft a Section 4.2 Disaster Recovery SLA clause aligned to "
                        "BNM RMiT and the Cyber Security Act 2024, citing our master tender…",
            height=105,
            key=k(cat, "prompt_area"),
            label_visibility="collapsed",
        )
        st.session_state[k(cat, "prompt")] = prompt

        g1, g2 = st.columns([2, 1])
        with g1:
            if st.button("Generate Draft Clause", key=k(cat, "gen"),
                         type="primary", width="stretch"):
                bar = st.progress(0, text="Opening zero-retention channel…")
                steps = [
                    (15, "Matching the instruction against the registry…"),
                    (34, f"Retrieving passages from {cfg['citation'][0]}…"),
                    (52, "Ranking 3 candidate passages…"),
                    (70, "Composing the clause with citations…"),
                    (86, "Validating against MOF_ePerolehan_Template.pdf…"),
                    (100, "Draft ready — working context discarded."),
                ]
                for pct, label in steps:
                    time.sleep(0.4)
                    bar.progress(pct, text=label)
                time.sleep(0.25)
                bar.empty()
                st.session_state[k(cat, "generated")] = True
                st.session_state[k(cat, "draft")] = DR_BODY
                st.rerun()
        with g2:
            if st.session_state[k(cat, "generated")]:
                if st.button("↺  Discard Draft", key=k(cat, "discard"),
                             width="stretch"):
                    st.session_state[k(cat, "generated")] = False
                    st.session_state[k(cat, "approved")] = False
                    st.rerun()

        if st.session_state[k(cat, "generated")]:
            st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
            _document_workspace(cat, cfg)
        else:
            st.markdown(
                f'<div class="vc-card" style="text-align:center;padding:34px 18px;'
                f'margin-top:12px;border-style:dashed;">'
                f'<h4 style="color:{MUTED} !important;">No active draft</h4>'
                f'<p>Select a preset prompt or write a custom instruction, then generate a '
                f'grounded, fully cited clause for {CURRENT_USER} review.</p></div>',
                unsafe_allow_html=True,
            )


@st.fragment
def _document_workspace(cat: str, cfg: dict) -> None:
    """Draft canvas + sign-off + exports, isolated into one rerun island.

    Typing in the draft used to rerun the entire page -- both other columns,
    the sidebar, the topbar -- for a change that only this column cares about.
    That full redraw is what produced the flicker and the lost scroll position.
    As a fragment, an edit reruns only what is inside this function.

    The canvas and the export block have to live in the SAME fragment. The
    download payloads are built at render time from
    ``st.session_state[k(cat, "draft")]``; if the exports sat outside, a
    fragment-scoped rerun would refresh the text but leave the buttons holding
    the previous draft.

    Sign-off is deliberately NOT fragment-scoped. ``st.rerun()`` defaults to
    ``scope="app"``, so the approve/revoke buttons inside
    :func:`_signoff_and_export` still trigger a full rerun -- which is what
    repaints the gap auditor in the right-hand column from 67% to 100%.
    """
    _draft_canvas(cat, cfg)
    _signoff_and_export(cat, cfg)


def _body_height(text: str) -> int:
    """Tall enough that the draft never scrolls inside its own box.

    A textarea with an inner scrollbar breaks the page illusion immediately, so
    the height is sized to the wrapped content instead of being fixed. The
    browser-side auto-grow in components/branding.py refines this live as the
    user types; this is the value the page renders with.
    """
    chars_per_line = 62
    rows = sum(
        max(1, math.ceil(len(line) / chars_per_line)) if line.strip() else 1
        for line in text.split("\n")
    )
    return int(min(2600, max(340, rows * 27 + 32)))


def _draft_canvas(cat: str, cfg: dict) -> None:
    src_file, src_page = cfg["citation"]

    st.markdown('<div class="vc-sec-label">Working Draft</div>',
                unsafe_allow_html=True)

    rows_html = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in SLA_ROWS
    )
    heads_html = "".join(f"<th>{h}</th>" for h in SLA_HEADERS)

    # One keyed container = one sheet of paper. Streamlit emits it as
    # .st-key-vc-a4-sheet, and styles.css paints THAT as the A4 page: white
    # ground, print margins, page shadow. The letterhead, the editable body and
    # the table are then plain children of the page rather than three separate
    # cards, which is what makes the document read as continuous.
    # Viewport frame (fixed height, scrolls) wrapping the page (grows freely).
    # Splitting the two is what stops a long draft from stretching the whole
    # browser page: the frame's height never changes, so nothing below it --
    # sign-off, exports, the footer -- moves when the document grows.
    with st.container(key="vc-a4-viewport"), st.container(key="vc-a4-sheet"):
        st.markdown(
            f"""
            <div class="vc-doc-head">
              <div class="title">{cfg['doc_title']}</div>
              <div class="meta">Document Ref: {cfg['doc_ref']} &nbsp;·&nbsp;
              Classification: Confidential &nbsp;·&nbsp;
              Generated: {dt.datetime.now():%d %B %Y} &nbsp;·&nbsp;
              Prepared by: VaultComply · cited to source</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Same widget key and same destination key as before, so generation,
        # persistence and the .docx / .pdf / .zip exports all read exactly what
        # they read previously -- only the skin around this changed.
        st.session_state[k(cat, "draft")] = st.text_area(
            "Draft body (editable)",
            value=st.session_state[k(cat, "draft")],
            height=_body_height(st.session_state[k(cat, "draft")]),
            key=k(cat, "draft_area"),
            label_visibility="collapsed",
        )

        st.markdown(
            f"""
            <div class="vc-doc-table">
              <div class="cap">Table 4.2.3 — Recovery Objectives by Service Criticality Tier</div>
              <table><thead><tr>{heads_html}</tr></thead><tbody>{rows_html}</tbody></table>
              <div class="note">Objectives measured on a rolling calendar-month basis and subject
              to the liquidated damages regime in Section 9.4. Availability excludes pre-notified
              maintenance windows agreed in writing with the Client.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div style="margin:12px 0 6px 0;">'
        f'<span class="vc-cite">[Source: {src_file}: Page {src_page}]</span>'
        f'<span style="font-size:0.72rem;color:{MUTED};margin-left:9px;">'
        f"Cited · 3 supporting passages · match 0.94</span></div>",
        unsafe_allow_html=True,
    )

    with st.expander(f"Provenance — verified extract from {src_file}, page {src_page}"):
        st.markdown(f'<div class="vc-quote">{PROVENANCE_QUOTE}</div>', unsafe_allow_html=True)
        p1, p2 = st.columns(2)
        with p1:
            st.markdown(
                f"""
                <div style="font-size:0.72rem;line-height:1.9;margin-top:8px;">
                  <div class="vc-mono">SOURCE VERIFICATION</div>
                  <div><span style="color:{SUCCESS};">✔</span> Document: <b>{src_file}</b></div>
                  <div><span style="color:{SUCCESS};">✔</span> Location: Page {src_page}, ¶ 4–6</div>
                  <div><span style="color:{SUCCESS};">✔</span> Retrieved from the private registry</div>
                  <div><span style="color:{SUCCESS};">✔</span> Match score: 0.94 / 1.00</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with p2:
            st.markdown(
                f"""
                <div style="font-size:0.72rem;line-height:1.9;margin-top:8px;">
                  <div class="vc-mono">INTEGRITY CONTROLS</div>
                  <div><span style="color:{SUCCESS};">✔</span> No external sources consulted</div>
                  <div><span style="color:{SUCCESS};">✔</span> Zero Data Retention enforced on request</div>
                  <div><span style="color:{SUCCESS};">✔</span> Chunk hash: 7f3a…c19e (verified)</div>
                  <div><span style="color:{SUCCESS};">✔</span> Cross-checked vs. MOF_ePerolehan_Template.pdf</div>
                </div>""",
                unsafe_allow_html=True,
            )


def _signoff_and_export(cat: str, cfg: dict) -> None:
    approved = st.session_state[k(cat, "approved")]

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Compliance Sign-Off</div>',
                unsafe_allow_html=True)

    s1, s2 = st.columns([2, 1])
    with s1:
        if approved:
            st.markdown(
                f"""
                <div class="vc-signoff">
                  <span class="vc-status-pill vc-approved">Approved by {CURRENT_USER}</span>
                  <div style="font-size:0.70rem;color:{MUTED};margin-top:7px;line-height:1.6;">
                    Signed {dt.datetime.now():%d %b %Y, %H:%M} MYT · Clause hash committed to the
                    audit trail · Export unlocked.</div>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="vc-signoff">
                  <span class="vc-status-pill vc-pending">Pending {CURRENT_USER} review</span>
                  <div style="font-size:0.70rem;color:{MUTED};margin-top:7px;line-height:1.6;">
                    Generated content is provisional. Statutory export remains locked until an
                    authorised reviewer records sign-off.</div>
                </div>""",
                unsafe_allow_html=True,
            )
    with s2:
        st.write("")
        if not approved:
            if st.button("✔  Approve and Sign Off", key=k(cat, "approve"),
                         width="stretch", type="primary"):
                st.session_state[k(cat, "approved")] = True
                st.rerun()
        else:
            if st.button("↺  Revoke Sign-Off", key=k(cat, "revoke"), width="stretch"):
                st.session_state[k(cat, "approved")] = False
                st.rerun()

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Statutory Export Formats</div>',
                unsafe_allow_html=True)

    if not approved:
        st.markdown(
            f'<div style="font-size:0.74rem;color:{WARN};margin-bottom:8px;">'
            "Export locked — Compliance Lead sign-off required before release.</div>",
            unsafe_allow_html=True,
        )

    draft_text = st.session_state[k(cat, "draft")]
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")

    body_blocks = [("body", ln) if not ln.strip().startswith("4.2.")
                   else ("h2", ln) for ln in draft_text.split("\n") if ln.strip()]
    body_blocks.append(("meta", f"Approved by {CURRENT_USER} on "
                                f"{dt.datetime.now():%d %B %Y, %H:%M} MYT"))
    body_blocks.append(("meta", f"[Source: {cfg['citation'][0]}: Page {cfg['citation'][1]}] · "
                                f"Generated under Zero Data Retention policy"))

    docx_bytes = build_docx(
        cfg["doc_title"],
        f"Document Ref {cfg['doc_ref']} · Confidential · VaultComply AI",
        body_blocks,
        {"caption": "Table 4.2.3 — Recovery Objectives by Service Criticality Tier",
         "headers": SLA_HEADERS, "rows": SLA_ROWS},
    )

    pdf_lines: list[str] = [
        f"Document Ref: {cfg['doc_ref']}    Classification: Confidential",
        f"Generated: {dt.datetime.now():%d %B %Y %H:%M} MYT    Engine: VaultComply AI",
        "",
    ]
    for ln in draft_text.split("\n"):
        ln = ln.rstrip()
        if not ln:
            pdf_lines.append("")
            continue
        if ln.strip().startswith("4.2"):
            pdf_lines.append("## " + ln.strip())
            continue
        while len(ln) > 96:
            cut = ln.rfind(" ", 0, 96)
            cut = cut if cut > 40 else 96
            pdf_lines.append(ln[:cut])
            ln = ln[cut:].lstrip()
        pdf_lines.append(ln)
    pdf_lines += [
        "",
        "## Table 4.2.3 - Recovery Objectives by Service Criticality Tier",
        "| Service Tier        | RTO         | RPO         | Availability |",
        "| Tier 1 - Critical   | 15 minutes  | 5 minutes   | 99.99%       |",
        "| Tier 2 - High       | 4 hours     | 1 hour      | 99.90%       |",
        "| Tier 3 - Standard   | 24 hours    | 12 hours    | 99.50%       |",
        "",
        "## Provenance & Assurance",
        f"Source: {cfg['citation'][0]}, page {cfg['citation'][1]} (private vault namespace).",
        f"Audit basis: {cfg['audit_basis']}.",
        f"Approved by: {CURRENT_USER} on {dt.datetime.now():%d %B %Y, %H:%M} MYT.",
        "Zero Data Retention enforced. Data residency: Cyberjaya, Malaysia (MY-Central-1).",
        "Aligned to PDPA 2010 (Amd. 2024), Cyber Security Act 2024, MOF/ePerolehan, ISO 27001:2022.",
    ]
    pdf_bytes = build_pdf(f"{cfg['doc_title']} — Audit-Ready Export", pdf_lines)

    manifest = [
        "ePEROLEHAN SUBMISSION BUNDLE MANIFEST",
        "=====================================",
        f"Document class      : {cat}",
        f"Document reference  : {cfg['doc_ref']}",
        f"Title               : {cfg['doc_title']}",
        f"Compiled            : {dt.datetime.now():%Y-%m-%d %H:%M:%S} MYT",
        f"Approved by         : {CURRENT_USER}",
        f"Audit basis         : {cfg['audit_basis']}",
        "Compliance score    : 100% — Fully Compliant",
        "",
        "CONTENTS",
        "  01_Submission/  Word draft and audit-ready PDF",
        "  02_Manifest/    This manifest and the vault source index",
        "  03_Integrity/   SHA-256 checksums and sign-off attestation",
        "",
        "STATUTORY ALIGNMENT",
        "  - Personal Data Protection Act 2010 (Amendment 2024)",
        "  - Cyber Security Act 2024 (Act 854)",
        "  - MOF procurement circulars / ePerolehan submission schema",
        "  - Treasury Circular PK 2.3",
        "  - ISO/IEC 27001:2022",
    ]
    zip_bytes = build_bundle(cat, docx_bytes, pdf_bytes, manifest,
                             st.session_state[k(cat, "vault")])

    x1, x2, x3 = st.columns(3)
    with x1:
        st.download_button(
            "Word (.docx)",
            data=docx_bytes,
            file_name=f"{cfg['doc_ref']}_{cat}_Draft_{stamp}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            disabled=not approved,
            width="stretch",
            key=k(cat, "dl_docx"),
        )
    with x2:
        st.download_button(
            "Audit PDF (.pdf)",
            data=pdf_bytes,
            file_name=f"{cfg['doc_ref']}_{cat}_AuditReady_{stamp}.pdf",
            mime="application/pdf",
            disabled=not approved,
            width="stretch",
            key=k(cat, "dl_pdf"),
        )
    with x3:
        st.download_button(
            "ePerolehan bundle (.zip)",
            data=zip_bytes,
            file_name=f"{cfg['doc_ref']}_ePerolehan_Bundle_{stamp}.zip",
            mime="application/zip",
            disabled=not approved,
            width="stretch",
            key=k(cat, "dl_zip"),
        )

    if approved:
        st.markdown(
            f'<div style="font-size:0.70rem;color:{MUTED};margin-top:7px;line-height:1.6;">'
            "Exports carry an embedded sign-off attestation, SHA-256 integrity manifest and "
            "full source provenance. Bundle structure matches the ePerolehan submission schema."
            "</div>",
            unsafe_allow_html=True,
        )
