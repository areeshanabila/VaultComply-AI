"""Workspace centre column: real ingestion, retrieval, drafting, audit and sign-off."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import math

import pandas as pd
import streamlit as st

from components.widgets import file_row, kpi
from core.config import ACCENT, CURRENT_USER, DANGER, MUTED, SUCCESS, WARN
from core.state import k
from services.audit_engine import audit_document, compliance_score
from services.document_ingestion import DocumentParseError, parse_document
from services.drafting import generate_grounded_draft
from services.ollama_client import CHAT_MODEL, EMBED_MODEL, status as ollama_status
from services.requirement_engine import extract_requirements
from services.retrieval import retrieve
from services.exporters import build_bundle, build_docx, build_pdf


def _doc_hash(uploaded) -> str:
    return hashlib.sha256(uploaded.getvalue()).hexdigest()


def render(cat: str, cfg: dict) -> None:
    """Render the centre column for one document category."""
    ost = ollama_status()
    if ost.online:
        chat_state = f"{CHAT_MODEL} ready" if ost.chat_model_ready else f"chat model missing: {CHAT_MODEL}"
        embed_state = f"{EMBED_MODEL} ready" if ost.embed_model_ready else f"embedding model missing: {EMBED_MODEL}"
        st.caption(f"Local AI: Ollama online · {chat_state} · {embed_state}")
    else:
        st.caption("Local AI: Ollama offline · deterministic/lexical fallbacks remain available")

    st.markdown('<div class="vc-sec-label">Active Intake — Client Requirements / RFP</div>', unsafe_allow_html=True)
    intake = st.file_uploader(
        f"Upload {cfg['intake']}",
        type=["pdf", "docx", "txt", "md"],
        key=k(cat, "intake_upload"),
        label_visibility="collapsed",
    )
    if intake is not None:
        current = st.session_state[k(cat, "intake_doc")]
        digest = _doc_hash(intake)
        if current is None or current.sha256 != digest:
            try:
                with st.spinner("Parsing requirements and extracting auditable controls locally…"):
                    record = parse_document(intake.name, intake.getvalue(), intake.type or "")
                    requirements, req_engine = extract_requirements(record, prefer_ollama=True)
                st.session_state[k(cat, "intake")] = intake.name
                st.session_state[k(cat, "intake_doc")] = record
                st.session_state[k(cat, "requirements")] = requirements
                st.session_state[k(cat, "requirement_engine")] = req_engine
                st.session_state[k(cat, "analysed")] = False
                st.session_state[k(cat, "audit_results")] = []
                st.session_state[k(cat, "approved")] = False
            except DocumentParseError as exc:
                st.error(str(exc))

    intake_doc = st.session_state[k(cat, "intake_doc")]
    requirements = st.session_state[k(cat, "requirements")]
    if intake_doc:
        engine = st.session_state[k(cat, "requirement_engine")] or "unknown"
        st.markdown(
            file_row(intake_doc.name, f"Parsed · {len(requirements)} requirements · {engine}", ACCENT),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            file_row(cfg["intake"], "Demo filename only · upload a real RFP/checklist to parse", WARN),
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Action</div>', unsafe_allow_html=True)

    tab_a, tab_b = st.tabs(["Verify Existing Document", "Draft a Clause"])

    with tab_a:
        _verify_tab(cat, cfg, requirements, ost.chat_model_ready)

    with tab_b:
        _draft_tab(cat, cfg)


def _verify_tab(cat: str, cfg: dict, requirements, chat_ready: bool) -> None:
    st.markdown(
        f'<p style="font-size:0.78rem;color:{MUTED};line-height:1.6;">'
        "Upload the proposal/report you want to verify. VaultComply compares it against requirements "
        "extracted from the uploaded RFP/checklist. Deterministic rules run first; Ollama semantic review is optional.</p>",
        unsafe_allow_html=True,
    )

    active = st.file_uploader(
        "Document to verify",
        type=["pdf", "docx", "txt", "md"],
        key=k(cat, "active_upload"),
        help="This is the document being audited, not the RFP/checklist.",
    )
    if active is not None:
        current = st.session_state[k(cat, "active_doc")]
        digest = _doc_hash(active)
        if current is None or current.sha256 != digest:
            try:
                record = parse_document(active.name, active.getvalue(), active.type or "")
                st.session_state[k(cat, "active_doc")] = record
                st.session_state[k(cat, "analysed")] = False
                st.session_state[k(cat, "audit_results")] = []
                st.session_state[k(cat, "approved")] = False
            except DocumentParseError as exc:
                st.error(str(exc))

    active_doc = st.session_state[k(cat, "active_doc")]
    if active_doc:
        st.markdown(file_row(active_doc.name, f"Ready · {active_doc.page_count} page(s)", ACCENT), unsafe_allow_html=True)
    elif st.session_state[k(cat, "generated")]:
        st.caption("No separate document uploaded. The current generated draft can be audited instead.")

    use_semantic = st.checkbox(
        "Use Ollama for ambiguous semantic requirements",
        value=False,
        key=k(cat, "semantic_audit_toggle"),
        disabled=not chat_ready,
        help="CPU inference can be slower. Deterministic section, phrase and numeric checks always run first.",
    )

    if st.button("Run Gap Analysis", key=k(cat, "run_gap"), type="primary", width="stretch"):
        if not requirements:
            st.error("Upload a real RFP/checklist first so VaultComply can extract audit requirements.")
        else:
            target_text = active_doc.text if active_doc else (
                st.session_state[k(cat, "draft")] if st.session_state[k(cat, "generated")] else ""
            )
            if not target_text.strip():
                st.error("Upload a document to verify, or generate a draft first.")
            else:
                with st.spinner("Running deterministic compliance checks…"):
                    results = audit_document(target_text, requirements, use_ollama=bool(use_semantic))
                st.session_state[k(cat, "audit_results")] = results
                st.session_state[k(cat, "analysed")] = True
                st.rerun()

    if st.session_state[k(cat, "analysed")] and st.session_state[k(cat, "audit_results")]:
        _render_findings(cat)


def _render_findings(cat: str) -> None:
    results = st.session_state[k(cat, "audit_results")]
    score = compliance_score(results)
    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Control Findings</div>', unsafe_allow_html=True)

    rows = []
    for r in results:
        if r.status == "N/A":
            risk = "Out of scope"
        elif r.status == "REVIEW":
            risk = "Manual review"
        else:
            risk = "Mandatory" if r.requirement.mandatory and r.status != "PASS" else "—"
        scope_label = r.requirement.scope.replace("_", " ").title()
        rows.append([r.requirement.code, r.requirement.title, scope_label, r.status, risk])
    df = pd.DataFrame(rows, columns=["Control", "Requirement", "Scope", "Result", "Risk"])
    st.dataframe(df, width="stretch", hide_index=True, height=min(360, 48 + len(rows) * 34))

    content = [r for r in results if r.requirement.scope == "report_content"]
    passed_n = sum(1 for r in content if r.status == "PASS")
    scoreable_n = sum(1 for r in content if r.status in {"PASS", "FAIL"})
    fail_n = sum(1 for r in content if r.status == "FAIL")
    review_n = sum(1 for r in results if r.status == "REVIEW")
    na_n = sum(1 for r in results if r.status == "N/A")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(kpi("Content Passed", f"{passed_n}/{scoreable_n or len(content)}", "", SUCCESS), unsafe_allow_html=True)
    with m2:
        st.markdown(kpi("Fail / Manual / N-A", f"{fail_n}/{review_n}/{na_n}", "", DANGER if fail_n else WARN), unsafe_allow_html=True)
    with m3:
        st.markdown(kpi("Content Score", "—" if score is None else f"{score}%", "", SUCCESS if score == 100 else DANGER), unsafe_allow_html=True)

    missing = [
        r for r in results
        if r.requirement.scope == "report_content" and r.status in {"FAIL", "REVIEW"}
    ]
    if missing:
        st.markdown(
            '<div class="vc-alert-red" style="margin-top:10px;">'
            '<div class="t">Content Remediation Required</div>'
            '<div class="d">Select or type a missing report-content requirement in <b>Draft a Clause</b>. '
            'Formatting, plagiarism and presentation controls are handled separately and are not treated as missing clauses.</div></div>',
            unsafe_allow_html=True,
        )
    elif review_n or na_n:
        st.caption("Written-content checks passed. Manual/external or out-of-scope controls are listed separately and do not reduce the automatic content score.")


def _draft_tab(cat: str, cfg: dict) -> None:
    st.markdown(
        f'<p style="font-size:0.78rem;color:{MUTED};line-height:1.6;">'
        f"Drafting is RAG-grounded. VaultComply first retrieves relevant chunks from the parsed {cat.lower()} vault, "
        "then sends only those passages to local Ollama. Citation metadata comes from retrieval, not from the model.</p>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="vc-sec-label">Standard Instructions</div>', unsafe_allow_html=True)
    # Prioritize real failed requirements as quick actions.
    failures = [
        r for r in st.session_state[k(cat, "audit_results")]
        if r.requirement.scope == "report_content" and r.status in {"FAIL", "REVIEW"}
    ]
    for r in failures[:3]:
        label = f"Fix: {r.requirement.title[:70]}"
        if st.button(label, key=k(cat, f"fix_{r.requirement.code}"), width="stretch"):
            st.session_state[k(cat, "prompt")] = f"Draft content that satisfies this requirement: {r.requirement.source_text or r.requirement.title}"
            st.rerun()

    for chip in cfg["prompts"][:3]:
        if st.button(chip, key=k(cat, f"chip_{chip[:18]}"), width="stretch"):
            st.session_state[k(cat, "prompt")] = chip
            st.rerun()

    prompt = st.text_area(
        "Custom instruction",
        value=st.session_state[k(cat, "prompt")],
        placeholder="e.g. Draft the missing cybersecurity incident response section using only verified vault evidence…",
        height=105,
        key=k(cat, "prompt_area"),
        label_visibility="collapsed",
    )
    st.session_state[k(cat, "prompt")] = prompt

    g1, g2 = st.columns([2, 1])
    with g1:
        if st.button("Generate Grounded Draft", key=k(cat, "gen"), type="primary", width="stretch"):
            records = st.session_state[k(cat, "vault_records")]
            if not prompt.strip():
                st.error("Enter a drafting instruction first.")
            elif not records:
                st.error("No parsed vault documents are available. Upload at least one real source document to the Semantic Vault first.")
            else:
                with st.spinner("Retrieving grounded evidence from the local Semantic Vault…"):
                    hits, retrieval_engine = retrieve(prompt, records, top_k=4, use_semantic=True)
                if not hits:
                    st.error("No grounded source found for this instruction. VaultComply will not fabricate a citation.")
                else:
                    try:
                        with st.spinner("Drafting from retrieved evidence with local AI…"):
                            draft, draft_engine = generate_grounded_draft(prompt, hits)
                        st.session_state[k(cat, "retrieval_hits")] = hits
                        st.session_state[k(cat, "retrieval_engine")] = retrieval_engine
                        st.session_state[k(cat, "draft_engine")] = draft_engine
                        st.session_state[k(cat, "draft")] = draft
                        st.session_state[k(cat, "draft_area")] = draft
                        st.session_state[k(cat, "generated")] = True
                        st.session_state[k(cat, "approved")] = False
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
    with g2:
        if st.session_state[k(cat, "generated")]:
            if st.button("↺ Discard Draft", key=k(cat, "discard"), width="stretch"):
                st.session_state[k(cat, "generated")] = False
                st.session_state[k(cat, "approved")] = False
                st.session_state[k(cat, "draft")] = ""
                st.session_state.pop(k(cat, "draft_area"), None)
                st.session_state[k(cat, "retrieval_hits")] = []
                st.rerun()

    if st.session_state[k(cat, "generated")]:
        st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
        _document_workspace(cat, cfg)
    else:
        st.markdown(
            f'<div class="vc-card" style="text-align:center;padding:34px 18px;margin-top:12px;border-style:dashed;">'
            f'<h4 style="color:{MUTED} !important;">No active draft</h4>'
            f'<p>Choose a failed requirement or write a custom instruction. A draft is released only when '
            f'grounded vault evidence is found.</p></div>',
            unsafe_allow_html=True,
        )


@st.fragment
def _document_workspace(cat: str, cfg: dict) -> None:
    _draft_canvas(cat, cfg)
    _signoff_and_export(cat, cfg)


def _body_height(text: str) -> int:
    chars_per_line = 62
    rows = sum(max(1, math.ceil(len(line) / chars_per_line)) if line.strip() else 1 for line in text.split("\n"))
    return int(min(2200, max(340, rows * 26 + 32)))


def _draft_canvas(cat: str, cfg: dict) -> None:
    hits = st.session_state[k(cat, "retrieval_hits")]
    retrieval_engine = st.session_state[k(cat, "retrieval_engine")] or "unknown"
    draft_engine = st.session_state[k(cat, "draft_engine")] or "unknown"

    st.markdown('<div class="vc-sec-label">Working Draft</div>', unsafe_allow_html=True)
    with st.container(key="vc-a4-viewport"), st.container(key="vc-a4-sheet"):
        st.markdown(
            f"""
            <div class="vc-doc-head">
              <div class="title">{html.escape(cfg['doc_title'])}</div>
              <div class="meta">Document Ref: {html.escape(cfg['doc_ref'])} &nbsp;·&nbsp;
              Classification: Confidential &nbsp;·&nbsp;
              Generated: {dt.datetime.now():%d %B %Y} &nbsp;·&nbsp;
              Engine: {html.escape(draft_engine)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.session_state[k(cat, "draft")] = st.text_area(
            "Draft body (editable)",
            value=st.session_state[k(cat, "draft")],
            height=_body_height(st.session_state[k(cat, "draft")]),
            key=k(cat, "draft_area"),
            label_visibility="collapsed",
        )

    if hits:
        primary = hits[0]
        st.markdown(
            f'<div style="margin:12px 0 6px 0;">'
            f'<span class="vc-cite">[Source: {html.escape(primary.chunk.document_name)}: Page {primary.chunk.page}]</span>'
            f'<span style="font-size:0.72rem;color:{MUTED};margin-left:9px;">'
            f'{len(hits)} grounded passage(s) · retrieval {html.escape(retrieval_engine)} · score {primary.score:.2f}</span></div>',
            unsafe_allow_html=True,
        )

        with st.expander("Grounding & provenance — inspect retrieved source passages"):
            for idx, hit in enumerate(hits, start=1):
                st.markdown(
                    f"**Source {idx}: {hit.chunk.document_name} · page {hit.chunk.page} · score {hit.score:.2f}**"
                )
                st.code(hit.chunk.text[:1600], language=None)
                st.caption(f"Chunk {hit.chunk.id} · SHA-256 {hit.chunk.sha256[:16]}…")
                if idx != len(hits):
                    st.divider()
    else:
        st.warning("No citation metadata is attached to this draft.")


def _rerun_audit_after_approval(cat: str) -> None:
    requirements = st.session_state[k(cat, "requirements")]
    if not requirements:
        return
    active_doc = st.session_state[k(cat, "active_doc")]
    base = active_doc.text if active_doc else ""
    combined = (base + "\n\n" + st.session_state[k(cat, "draft")]).strip()
    if combined:
        use_semantic = bool(st.session_state.get(k(cat, "semantic_audit_toggle"), False))
        st.session_state[k(cat, "audit_results")] = audit_document(combined, requirements, use_ollama=use_semantic)
        st.session_state[k(cat, "analysed")] = True


def _signoff_and_export(cat: str, cfg: dict) -> None:
    approved = st.session_state[k(cat, "approved")]
    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Human Review & Sign-Off</div>', unsafe_allow_html=True)

    s1, s2 = st.columns([2, 1])
    with s1:
        if approved:
            st.markdown(
                f'<div class="vc-signoff"><span class="vc-status-pill vc-approved">Approved by {CURRENT_USER}</span>'
                f'<div style="font-size:0.70rem;color:{MUTED};margin-top:7px;line-height:1.6;">'
                "The generated revision is accepted. Compliance is recalculated separately; approval itself does not force a PASS.</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="vc-signoff"><span class="vc-status-pill vc-pending">Pending {CURRENT_USER} review</span>'
                f'<div style="font-size:0.70rem;color:{MUTED};margin-top:7px;line-height:1.6;">'
                "Review the wording and cited passages before approval.</div></div>",
                unsafe_allow_html=True,
            )
    with s2:
        st.write("")
        if not approved:
            if st.button("✔ Approve Revision", key=k(cat, "approve"), width="stretch", type="primary"):
                st.session_state[k(cat, "approved")] = True
                _rerun_audit_after_approval(cat)
                st.rerun()
        else:
            if st.button("↺ Revoke Sign-Off", key=k(cat, "revoke"), width="stretch"):
                st.session_state[k(cat, "approved")] = False
                requirements = st.session_state[k(cat, "requirements")]
                active_doc = st.session_state[k(cat, "active_doc")]
                if requirements and active_doc:
                    use_semantic = bool(st.session_state.get(k(cat, "semantic_audit_toggle"), False))
                    st.session_state[k(cat, "audit_results")] = audit_document(active_doc.text, requirements, use_ollama=use_semantic)
                    st.session_state[k(cat, "analysed")] = True
                st.rerun()

    _render_exports(cat, cfg, approved)


def _render_exports(cat: str, cfg: dict, approved: bool) -> None:
    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Export Formats</div>', unsafe_allow_html=True)
    if not approved:
        st.markdown(
            f'<div style="font-size:0.74rem;color:{WARN};margin-bottom:8px;">'
            "Export locked — human approval required before release.</div>",
            unsafe_allow_html=True,
        )

    draft_text = st.session_state[k(cat, "draft")]
    hits = st.session_state[k(cat, "retrieval_hits")]
    results = st.session_state[k(cat, "audit_results")]
    score = compliance_score(results) if results else None
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")

    blocks = []
    for line in draft_text.splitlines():
        if not line.strip():
            continue
        style = "h2" if len(line) < 100 and (line.strip().endswith(":") or re_heading(line)) else "body"
        blocks.append((style, line.strip()))
    blocks.append(("meta", f"Approved by {CURRENT_USER} on {dt.datetime.now():%d %B %Y, %H:%M}"))
    for hit in hits[:4]:
        blocks.append(("meta", f"Source: {hit.chunk.document_name}, page {hit.chunk.page}, chunk {hit.chunk.id}"))

    docx_bytes = build_docx(
        cfg["doc_title"],
        f"Document Ref {cfg['doc_ref']} · VaultComply AI · Human-reviewed draft",
        blocks,
        None,
    )

    pdf_lines = [
        f"Document Ref: {cfg['doc_ref']}",
        f"Generated: {dt.datetime.now():%d %B %Y %H:%M}",
        f"Compliance score: {'Not audited' if score is None else str(score) + '%'}",
        "",
    ]
    for line in draft_text.splitlines():
        line = line.rstrip()
        if not line:
            pdf_lines.append("")
            continue
        while len(line) > 96:
            cut = line.rfind(" ", 0, 96)
            cut = cut if cut > 40 else 96
            pdf_lines.append(line[:cut])
            line = line[cut:].lstrip()
        pdf_lines.append(line)
    pdf_lines += ["", "## Grounded Sources"]
    for hit in hits[:4]:
        pdf_lines.append(f"- {hit.chunk.document_name}, page {hit.chunk.page}, chunk {hit.chunk.id}")
    pdf_bytes = build_pdf(f"{cfg['doc_title']} — Human-Reviewed Export", pdf_lines)

    manifest = [
        "VAULTCOMPLY AI LOCAL PROTOTYPE EXPORT MANIFEST",
        "===============================================",
        f"Document class      : {cat}",
        f"Document reference  : {cfg['doc_ref']}",
        f"Compiled            : {dt.datetime.now():%Y-%m-%d %H:%M:%S}",
        f"Approved by         : {CURRENT_USER}",
        f"Compliance score    : {'Not audited' if score is None else str(score) + '%'}",
        "",
        "GROUNDING SOURCES",
    ] + [f"  - {h.chunk.document_name} p.{h.chunk.page} [{h.chunk.id}]" for h in hits[:4]]

    zip_bytes = build_bundle(cat, docx_bytes, pdf_bytes, manifest, [r.name for r in st.session_state[k(cat, "vault_records")]])

    # Word draft can be released after human approval. Audit-ready exports require
    # all written-content requirements to pass. Manual formatting/plagiarism checks
    # and out-of-scope presentation/submission controls do not permanently lock export.
    content_results = [r for r in results if r.requirement.scope == "report_content"]
    unresolved = any(r.status != "PASS" for r in content_results) if content_results else True
    audit_ready = approved and bool(content_results) and not unresolved

    x1, x2, x3 = st.columns(3)
    with x1:
        st.download_button(
            "Word (.docx)", data=docx_bytes,
            file_name=f"{cfg['doc_ref']}_{cat}_Draft_{stamp}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            disabled=not approved, width="stretch", key=k(cat, "dl_docx"),
        )
    with x2:
        st.download_button(
            "Audit PDF (.pdf)", data=pdf_bytes,
            file_name=f"{cfg['doc_ref']}_{cat}_Audit_{stamp}.pdf",
            mime="application/pdf", disabled=not audit_ready,
            width="stretch", key=k(cat, "dl_pdf"),
        )
    with x3:
        st.download_button(
            "Submission bundle (.zip)", data=zip_bytes,
            file_name=f"{cfg['doc_ref']}_Submission_Bundle_{stamp}.zip",
            mime="application/zip", disabled=not audit_ready,
            width="stretch", key=k(cat, "dl_zip"),
        )
    if approved and not audit_ready:
        st.caption("Word export is available, but audit PDF/bundle stay locked until every written-content requirement passes.")


def re_heading(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) > 90:
        return False
    return bool(stripped and (stripped[0].isdigit() or stripped.isupper()))
