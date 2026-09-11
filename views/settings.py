"""Settings & local AI diagnostics for the prototype."""

from __future__ import annotations

import streamlit as st

from core.config import ACCENT, MUTED, SUCCESS, WARN
from services.ollama_client import CHAT_MODEL, EMBED_MODEL, OLLAMA_BASE_URL, status


def render() -> None:
    st.markdown("### Settings & Local AI")
    st.markdown(
        f'<p style="color:{MUTED};font-size:0.86rem;margin-top:-6px;">'
        "Runtime diagnostics and prototype privacy controls. These labels describe this local prototype, "
        "not an external security certification.</p>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown('<div class="vc-sec-label">Local Processing</div>', unsafe_allow_html=True)
        st.session_state.zdr = st.toggle(
            "Keep AI processing local",
            value=st.session_state.get("zdr", True),
            help="VaultComply is configured to call Ollama only through localhost by default.",
        )
        st.session_state.pii_redaction = st.toggle(
            "PII redaction before optional embedding",
            value=st.session_state.get("pii_redaction", True),
            help="Prototype setting only; extend the redactor before production use.",
        )
        st.session_state.audit_log = st.toggle(
            "Session audit events",
            value=st.session_state.get("audit_log", True),
            help="This prototype keeps workflow state in the current Streamlit session; it is not an immutable production audit store.",
        )
        st.session_state.region = st.text_input(
            "Environment label",
            value=st.session_state.get("region", "Local prototype environment"),
        )

        st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
        st.markdown('<div class="vc-sec-label">Prototype Boundaries</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:0.73rem;color:{MUTED};line-height:1.8;">'
            "• Uploaded document bytes are parsed in memory and are not deliberately persisted by VaultComply.<br/>"
            "• Parsed text, chunks, embeddings, drafts and audit results live in Streamlit session state.<br/>"
            "• Citations come from retrieved document chunks and page metadata, not from model-generated page numbers.<br/>"
            "• Human approval and compliance scoring are separate controls.<br/>"
            "• Production VPC/KMS/certification claims are intentionally not asserted by this prototype."
            "</div>",
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown('<div class="vc-sec-label">Ollama Diagnostics</div>', unsafe_allow_html=True)
        if st.button("Refresh Ollama status", width="stretch"):
            st.session_state["ollama_refresh_nonce"] = st.session_state.get("ollama_refresh_nonce", 0) + 1
            ost = status(refresh=True)
        else:
            ost = status()

        online_color = SUCCESS if ost.online else WARN
        st.markdown(
            f'<div class="vc-card" style="border-left:3px solid {online_color};">'
            f'<h4 style="color:{online_color} !important;">{"Ollama Online" if ost.online else "Ollama Offline"}</h4>'
            f'<p>Endpoint: <code>{OLLAMA_BASE_URL}</code></p>'
            f'<p>Chat model: <b>{CHAT_MODEL}</b> — {"ready" if ost.chat_model_ready else "not installed / not detected"}</p>'
            f'<p>Embedding model: <b>{EMBED_MODEL}</b> — {"ready" if ost.embed_model_ready else "not installed / not detected"}</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        if ost.online and ost.models:
            st.markdown('<div class="vc-sec-label">Installed Ollama Models</div>', unsafe_allow_html=True)
            st.code("\n".join(ost.models), language=None)
        elif not ost.online:
            st.warning("Start Ollama, then refresh this page. The app can still use deterministic extraction and lexical retrieval fallbacks.")

        if not ost.chat_model_ready or not ost.embed_model_ready:
            st.markdown('<div class="vc-sec-label">Recommended Setup</div>', unsafe_allow_html=True)
            st.code(
                f"ollama pull {CHAT_MODEL}\n"
                f"ollama pull {EMBED_MODEL}",
                language="powershell",
            )
            st.caption(
                "The chat model handles grounded drafting and optional semantic checks. "
                "The embedding model enables hybrid semantic + lexical retrieval."
            )

        st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
        st.markdown('<div class="vc-sec-label">Active Architecture</div>', unsafe_allow_html=True)
        rows = [
            ("Document parsing", "Local Python", SUCCESS),
            ("Retrieval", "Hybrid if embeddings are ready; lexical fallback otherwise", ACCENT),
            ("Requirement extraction", "Ollama JSON extraction; deterministic fallback", ACCENT),
            ("Drafting", "Grounded Ollama; deterministic grounded fallback", ACCENT),
            ("Scoring", "Deterministic from actual audit results", SUCCESS),
            ("Citations", "Retrieved file/page/chunk metadata", SUCCESS),
        ]
        html = "".join(
            f'<div class="vc-check"><div class="ic" style="color:{color};">●</div>'
            f'<div class="tx"><b>{label}</b> — <span style="color:{color};">{value}</span></div></div>'
            for label, value, color in rows
        )
        st.markdown(html, unsafe_allow_html=True)
