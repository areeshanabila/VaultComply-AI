"""
Views 2-4: the document generation workspaces — section 8 of the original
app.py.

All three routes (Proposal / Tender / Report) share this one implementation;
:data:`core.data.CATEGORIES` supplies the per-category vault, prompts and
checklist. The three-column layout is assembled here and each column is
delegated to its own module:

    vault    -> left    : category semantic vault + uploader
    studio   -> centre  : intake, action tabs, draft canvas, sign-off, export
    auditor  -> right   : compliance gauge, alerts, statutory checklist
"""

from __future__ import annotations

import streamlit as st

from core.config import ACCENT, MUTED
from core.data import CATEGORIES
from views.workspace import auditor, studio, vault


def render(cat: str) -> None:
    cfg = CATEGORIES[cat]

    st.markdown(f"### {cfg['icon']} {cat} Generation")
    st.markdown(
        f'<p style="color:{MUTED};font-size:0.86rem;margin-top:-6px;">{cfg["blurb"]} '
        f"Document ref <span class='vc-mono' style='color:{ACCENT};'>{cfg['doc_ref']}</span></p>",
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1.05, 2.1, 1.15], gap="large")

    # ── LEFT — Semantic vault ───────────────────────────────────────────────
    with left:
        vault.render(cat, cfg)

    # ── CENTER — Intake & studio ────────────────────────────────────────────
    with center:
        studio.render(cat, cfg)

    # ── RIGHT — Gap auditor ─────────────────────────────────────────────────
    with right:
        auditor.render(cat, cfg)
