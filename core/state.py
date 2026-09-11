"""Session state and routing helpers."""

from __future__ import annotations

import streamlit as st

from core.config import DEFAULT_PAGE
from core.data import CATEGORIES


def k(cat: str, name: str) -> str:
    return f"{cat.lower()}__{name}"


def init_state() -> None:
    st.session_state.setdefault("page", DEFAULT_PAGE)
    st.session_state.setdefault("sidebar_state", "expanded")
    st.session_state.setdefault("nav_docgen_open", True)
    for cat, cfg in CATEGORIES.items():
        # ``vault`` preserves the original UI registry list. ``vault_records`` contains
        # only documents that have actually been parsed/indexed in this session.
        st.session_state.setdefault(k(cat, "vault"), list(cfg["vault"]))
        st.session_state.setdefault(k(cat, "vault_records"), [])
        st.session_state.setdefault(k(cat, "intake"), None)
        st.session_state.setdefault(k(cat, "intake_doc"), None)
        st.session_state.setdefault(k(cat, "requirements"), [])
        st.session_state.setdefault(k(cat, "requirement_engine"), "")
        st.session_state.setdefault(k(cat, "active_doc"), None)
        st.session_state.setdefault(k(cat, "analysed"), False)
        st.session_state.setdefault(k(cat, "audit_results"), [])
        st.session_state.setdefault(k(cat, "generated"), False)
        st.session_state.setdefault(k(cat, "approved"), False)
        st.session_state.setdefault(k(cat, "draft"), "")
        st.session_state.setdefault(k(cat, "prompt"), "")
        st.session_state.setdefault(k(cat, "retrieval_hits"), [])
        st.session_state.setdefault(k(cat, "retrieval_engine"), "")
        st.session_state.setdefault(k(cat, "draft_engine"), "")
        st.session_state.setdefault(k(cat, "last_error"), "")
    st.session_state.setdefault("zdr", True)
    st.session_state.setdefault("audit_log", True)
    st.session_state.setdefault("region", "Local prototype environment")
    st.session_state.setdefault("pii_redaction", True)
    st.session_state.setdefault("model_training_optout", True)


def audit_revealed(cat: str) -> bool:
    """Only reveal audit claims after a real assessment has produced results."""
    return bool(st.session_state.get(k(cat, "analysed")) and st.session_state.get(k(cat, "audit_results")))


def goto(page: str) -> None:
    st.session_state.page = page
    st.rerun()
