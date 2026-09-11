"""
Workspace left column: the category semantic vault.

Extracted from ``render_vault_column`` in section 8 of the original app.py.
"""

from __future__ import annotations

import datetime as dt

import streamlit as st

from components.widgets import file_row
from core.config import MUTED, SUCCESS
from core.state import k


def render(cat: str, cfg: dict) -> None:
    st.markdown(f'<div class="vc-sec-label">{cat} Document Registry</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<p style="font-size:0.74rem;color:{MUTED};margin-top:-4px;line-height:1.5;">'
        f"Scoped to this document class · single-tenant namespace · encrypted at rest.</p>",
        unsafe_allow_html=True,
    )

    files = st.session_state[k(cat, "vault")]
    html = "".join(file_row(f) for f in files)
    st.markdown(html, unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:0.70rem;color:{MUTED};margin:2px 0 8px 0;">'
        f"<b style='color:{SUCCESS};'>{len(files)}</b> documents on file · "
        f"registry synchronised {dt.datetime.now():%H:%M} MYT</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Add a Source Document</div>',
                unsafe_allow_html=True)

    up = st.file_uploader(
        "Upload to vault",
        type=["pdf", "docx", "xlsx", "csv", "txt"],
        key=k(cat, "vault_upload"),
        label_visibility="collapsed",
        accept_multiple_files=True,
    )
    if up:
        added = [f.name for f in up if f.name not in files]
        if added:
            st.session_state[k(cat, "vault")].extend(added)
            st.rerun()

    st.markdown(
        f'<div style="font-size:0.68rem;color:{MUTED};line-height:1.6;margin-top:6px;">'
        "Uploaded files are indexed into your isolated namespace. The original payload is "
        "discarded once indexing completes, under the zero-retention policy.</div>",
        unsafe_allow_html=True,
    )
