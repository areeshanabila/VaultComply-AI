"""Home & Trust Center for the local prototype."""

from __future__ import annotations

import streamlit as st

from components.widgets import card, kpi
from core.config import ACCENT, MUTED, SUCCESS, WARN
from core.data import CATEGORIES
from core.state import goto, k
from services.ollama_client import CHAT_MODEL, EMBED_MODEL, status


def render() -> None:
    st.markdown("### Home & Trust Center")
    st.markdown(
        f'<p style="color:{MUTED};font-size:0.86rem;margin-top:-6px;">'
        "Local prototype status, grounding controls and quick access to document workspaces.</p>",
        unsafe_allow_html=True,
    )

    parsed_docs = sum(len(st.session_state.get(k(cat, "vault_records"), [])) for cat in CATEGORIES)
    chunks = sum(
        sum(len(r.chunks) for r in st.session_state.get(k(cat, "vault_records"), []))
        for cat in CATEGORIES
    )
    audits = sum(1 for cat in CATEGORIES if st.session_state.get(k(cat, "audit_results")))
    ost = status()

    st.markdown('<div class="vc-sec-label">Runtime Summary</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi("Parsed Vault Documents", str(parsed_docs), "current session", ACCENT), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Indexed Chunks", str(chunks), "page-aware retrieval", SUCCESS), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Completed Audits", str(audits), "current session", SUCCESS), unsafe_allow_html=True)
    with c4:
        label = "Online" if ost.online else "Fallback"
        detail = CHAT_MODEL if ost.chat_model_ready else "deterministic mode"
        st.markdown(kpi("Local AI", label, detail, SUCCESS if ost.online else WARN), unsafe_allow_html=True)

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">How This Prototype Establishes Trust</div>', unsafe_allow_html=True)

    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown(card(
            "Local AI Processing",
            "VaultComply calls Ollama through localhost by default. If Ollama or a model is unavailable, "
            "the workflow falls back to deterministic extraction, lexical retrieval and grounded template generation rather than failing silently.",
            SUCCESS,
        ), unsafe_allow_html=True)
    with d2:
        st.markdown(card(
            "Grounded Retrieval & Citations",
            "Uploaded files are parsed into page-aware chunks. Draft citations use the retrieved document name, page, chunk ID and hash; "
            "the language model is not trusted to invent source locations.",
            ACCENT,
        ), unsafe_allow_html=True)
    with d3:
        st.markdown(card(
            "Deterministic Compliance Score",
            "The score is calculated from actual mandatory requirement results. Clicking Approve records human acceptance of a revision, "
            "but it never forces a requirement to PASS or turns the score into 100%.",
            WARN,
        ), unsafe_allow_html=True)

    e1, e2, e3 = st.columns(3)
    with e1:
        st.markdown(card(
            "Requirement Interpretation",
            "Client RFP/checklist text is converted into structured requirements using local Ollama when available, with an exact-source grounding gate and a deterministic fallback.",
            ACCENT,
        ), unsafe_allow_html=True)
    with e2:
        st.markdown(card(
            "Human Review Required",
            "Grounded drafts remain provisional until an authorised reviewer approves them. Audit-ready PDF and submission bundle exports stay locked while mandatory findings remain unresolved.",
            SUCCESS,
        ), unsafe_allow_html=True)
    with e3:
        st.markdown(card(
            "Prototype Scope",
            "This build demonstrates local processing and workflow controls. It does not claim production VPC isolation, KMS custody, external certifications or independently attested Zero Data Retention.",
            WARN,
        ), unsafe_allow_html=True)

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Open a Workspace</div>', unsafe_allow_html=True)
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        if st.button("Proposal Drafting", width="stretch", type="primary"):
            goto("Proposal Generation")
    with q2:
        if st.button("Tender Response", width="stretch", type="primary"):
            goto("Tender Generation")
    with q3:
        if st.button("Compliance Reporting", width="stretch", type="primary"):
            goto("Report Generation")
    with q4:
        if st.button("Local AI & Settings", width="stretch"):
            goto("Settings & Security")

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Local AI Models</div>', unsafe_allow_html=True)
    st.caption(
        f"Chat: {CHAT_MODEL} ({'ready' if ost.chat_model_ready else 'not detected'}) · "
        f"Embeddings: {EMBED_MODEL} ({'ready' if ost.embed_model_ready else 'not detected'})."
    )
