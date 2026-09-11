"""
Session state and routing helpers — section 5 of the original app.py.

Every mutable value in the app lives in ``st.session_state`` under a key built
by :func:`k`, which namespaces state per document category so the Proposal,
Tender and Report workspaces never collide.
"""

from __future__ import annotations

import streamlit as st

from core.config import DEFAULT_PAGE
from core.data import CATEGORIES, DR_BODY


def k(cat: str, name: str) -> str:
    return f"{cat.lower()}__{name}"


def init_state() -> None:
    st.session_state.setdefault("page", DEFAULT_PAGE)
    st.session_state.setdefault("sidebar_state", "expanded")
    st.session_state.setdefault("nav_docgen_open", True)
    for cat, cfg in CATEGORIES.items():
        st.session_state.setdefault(k(cat, "vault"), list(cfg["vault"]))
        st.session_state.setdefault(k(cat, "intake"), None)
        st.session_state.setdefault(k(cat, "analysed"), False)
        st.session_state.setdefault(k(cat, "generated"), False)
        st.session_state.setdefault(k(cat, "approved"), False)
        st.session_state.setdefault(k(cat, "draft"), DR_BODY)
        st.session_state.setdefault(k(cat, "prompt"), "")
    st.session_state.setdefault("zdr", True)
    st.session_state.setdefault("audit_log", True)
    st.session_state.setdefault("region", "Cyberjaya, Malaysia (MY-Central-1)")
    st.session_state.setdefault("pii_redaction", True)
    st.session_state.setdefault("model_training_optout", True)


def audit_revealed(cat: str) -> bool:
    """Has the user done anything in this workspace worth auditing yet?

    The compliance gap auditor stays in an idle placeholder until one of the
    two explicit actions has run:

        "Run Compliance Gap Analysis"  -> sets <cat>__analysed
        "Generate Compliant Draft"     -> sets <cat>__generated

    Both flags already exist, already live in session_state, and are already
    namespaced per document category by :func:`k`, so this derives from them
    rather than adding a third flag that could drift out of sync with them.

    A consequence worth knowing: discarding a draft that was never analysed
    returns the panel to idle, because at that point there is genuinely nothing
    to report. Running the analysis is sticky — <cat>__analysed is never reset.
    """
    return bool(
        st.session_state.get(k(cat, "analysed")) or st.session_state.get(k(cat, "generated"))
    )


def goto(page: str) -> None:
    st.session_state.page = page
    st.rerun()
