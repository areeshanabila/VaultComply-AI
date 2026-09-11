"""Workspace left column: real local Semantic Vault ingestion and indexing."""

from __future__ import annotations

import datetime as dt
import hashlib

import streamlit as st

from components.widgets import file_row
from core.config import ACCENT, MUTED, SUCCESS, WARN
from core.state import k
from services.document_ingestion import DocumentParseError, parse_document
from services.retrieval import index_document_embeddings


def render(cat: str, cfg: dict) -> None:
    st.markdown(f'<div class="vc-sec-label">{cat} Document Registry</div>', unsafe_allow_html=True)
    st.markdown(
        f'<p style="font-size:0.74rem;color:{MUTED};margin-top:-4px;line-height:1.5;">'
        "Historical company documents used for retrieval and grounded drafting. "
        "Uploaded content is parsed locally in this Streamlit session.</p>",
        unsafe_allow_html=True,
    )

    listed_names: list[str] = st.session_state[k(cat, "vault")]
    records = st.session_state[k(cat, "vault_records")]
    indexed_by_name = {r.name: r for r in records}

    html_parts: list[str] = []
    for name in listed_names:
        record = indexed_by_name.get(name)
        if record:
            mode = "semantic" if record.indexed_with_embeddings else "lexical"
            html_parts.append(file_row(name, f"Indexed · {len(record.chunks)} chunks · {mode}", SUCCESS))
        else:
            html_parts.append(file_row(name, "Reference only · upload to index", WARN))
    st.markdown("".join(html_parts), unsafe_allow_html=True)

    total_chunks = sum(len(r.chunks) for r in records)
    st.markdown(
        f'<div style="font-size:0.70rem;color:{MUTED};margin:2px 0 8px 0;">'
        f"<b style='color:{SUCCESS};'>{len(records)}</b> parsed documents · "
        f"<b style='color:{ACCENT};'>{total_chunks}</b> indexed chunks · "
        f"updated {dt.datetime.now():%H:%M}</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Add Source Documents</div>', unsafe_allow_html=True)

    up = st.file_uploader(
        "Upload to vault",
        type=["pdf", "docx", "xlsx", "csv", "txt", "md"],
        key=k(cat, "vault_upload"),
        label_visibility="collapsed",
        accept_multiple_files=True,
    )

    if up:
        existing_hashes = {r.sha256 for r in records}
        changed = False
        messages: list[str] = []
        for uploaded in up:
            data = uploaded.getvalue()
            digest = hashlib.sha256(data).hexdigest()
            if digest in existing_hashes:
                continue
            try:
                with st.spinner(f"Indexing {uploaded.name} locally…"):
                    record = parse_document(uploaded.name, data, uploaded.type or "")
                    record, engine = index_document_embeddings(record)
                records.append(record)
                existing_hashes.add(record.sha256)
                if uploaded.name not in listed_names:
                    listed_names.append(uploaded.name)
                messages.append(f"{uploaded.name}: {len(record.chunks)} chunks ({engine})")
                changed = True
            except DocumentParseError as exc:
                st.error(str(exc))
        if changed:
            st.session_state[k(cat, "vault_records")] = records
            st.session_state[k(cat, "vault")] = listed_names
            st.session_state[k(cat, "last_error")] = ""
            st.success("Indexed locally: " + "; ".join(messages))
            st.rerun()

    if records and st.button("Clear session index", key=k(cat, "clear_vault_index"), width="stretch"):
        st.session_state[k(cat, "vault_records")] = []
        # Preserve the original registry names but remove names added only through uploads.
        st.session_state[k(cat, "vault")] = list(cfg["vault"])
        st.session_state[k(cat, "retrieval_hits")] = []
        st.rerun()

    st.markdown(
        f'<div style="font-size:0.68rem;color:{MUTED};line-height:1.6;margin-top:6px;">'
        "PDF page numbers are preserved for citations. If the local embedding model is available, "
        "the vault uses hybrid semantic + lexical retrieval; otherwise it falls back to lexical retrieval. "
        "The original uploaded bytes are not persisted by VaultComply.</div>",
        unsafe_allow_html=True,
    )
