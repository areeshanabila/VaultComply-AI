"""
View 1: Home & Trust Center — section 7 of the original app.py.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.widgets import card, kpi
from core.config import ACCENT, MUTED, SUCCESS, WARN
from core.state import goto


def render() -> None:
    st.markdown("### 🏛️ Home & Trust Center")
    st.markdown(
        f'<p style="color:{MUTED};font-size:0.86rem;margin-top:-6px;">'
        "Enterprise assurance posture, statutory alignment and platform telemetry for the "
        "current single-tenant deployment.</p>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="vc-sec-label">Platform Telemetry</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi("Indexed Vault Documents", "14 Files", "▲ 3 indexed this week", ACCENT),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Compliance Pass Rate", "98.2%", "▲ 4.1% vs. last quarter", SUCCESS),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Average Draft Time Saved", "32.5 Hours", "per submission cycle", SUCCESS),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(kpi("Clauses Pending Sign-Off", "2 Items", "awaiting Compliance Lead", WARN),
                    unsafe_allow_html=True)

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Official Security Declarations</div>',
                unsafe_allow_html=True)

    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown(
            card(
                "Zero Data Retention (ZDR)",
                "No prompt, no document payload and no model output is persisted beyond the "
                "lifetime of the inference request. Vault embeddings remain encrypted at rest "
                "under a customer-held KMS key (AES-256-GCM). No client content is ever used "
                "for model training or evaluation — contractually enforced and independently "
                "attested.",
                SUCCESS, "🔒",
            ),
            unsafe_allow_html=True,
        )
    with d2:
        st.markdown(
            card(
                "Single-Tenant VPC Isolation",
                "Your deployment runs in a dedicated Virtual Private Cloud with a private "
                "namespace, no shared compute and no cross-tenant vector index. Egress is "
                "restricted to an allow-listed inference endpoint; all traffic is mutually "
                "authenticated (mTLS) and terminated inside Malaysian sovereign territory.",
                ACCENT, "🏗️",
            ),
            unsafe_allow_html=True,
        )
    with d3:
        st.markdown(
            card(
                "Statutory & Standards Alignment",
                "Aligned to the Personal Data Protection Act 2010 (Amd. 2024), the Cyber "
                "Security Act 2024 (Act 854), Ministry of Finance procurement circulars, the "
                "ePerolehan submission schema, Treasury Circular PK 2.3 and ISO/IEC 27001:2022. "
                "Immutable audit trails are retained for statutory inspection.",
                WARN, "⚖️",
            ),
            unsafe_allow_html=True,
        )

    e1, e2, e3 = st.columns(3)
    with e1:
        st.markdown(
            card("Human-in-the-Loop Governance",
                 "No generated clause may be exported until an authorised Compliance Lead has "
                 "recorded an explicit sign-off. Every approval is written to an append-only "
                 "ledger with actor, timestamp and clause hash.", ACCENT, "✍️"),
            unsafe_allow_html=True)
    with e2:
        st.markdown(
            card("Verifiable Provenance",
                 "Every generated sentence carries a citation back to an indexed source "
                 "document and page. Un-cited content is blocked at generation time, "
                 "eliminating unsupported assertions in statutory submissions.", SUCCESS, "🔍"),
            unsafe_allow_html=True)
    with e3:
        st.markdown(
            card("Data Residency — Cyberjaya",
                 "Primary processing and vector storage reside in the Cyberjaya datacentre "
                 "(MY-Central-1) with warm standby in Kuala Lumpur. No data leaves Malaysian "
                 "jurisdiction at any point in the document lifecycle.", WARN, "📍"),
            unsafe_allow_html=True)

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Quick Launch — Document Workspaces</div>',
                unsafe_allow_html=True)

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        if st.button("📝  Open Proposal Workspace", width="stretch", type="primary"):
            goto("Proposal Generation")
    with q2:
        if st.button("📋  Open Tender Workspace", width="stretch", type="primary"):
            goto("Tender Generation")
    with q3:
        if st.button("📊  Open Report Workspace", width="stretch", type="primary"):
            goto("Report Generation")
    with q4:
        if st.button("⚙️  Security & Settings", width="stretch"):
            goto("Settings & Security")

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Recent Compliance Activity — Immutable Ledger</div>',
                unsafe_allow_html=True)

    ledger = pd.DataFrame(
        [
            ["2026-09-10 09:42", "Compliance Lead", "Clause Sign-Off",
             "Tender / Section 4.2 DR SLA", "Approved"],
            ["2026-09-10 09:15", "Proposal Writer", "Draft Generated",
             "Proposal / Executive Summary", "Pending Review"],
            ["2026-09-09 17:38", "Auditor", "Gap Analysis Run",
             "Tender / VC-TDR-2026-0088", "Completed"],
            ["2026-09-09 14:02", "Compliance Lead", "Vault Index",
             "MOF_ePerolehan_Template.pdf", "Indexed"],
            ["2026-09-08 11:20", "Proposal Writer", "Export — ePerolehan Bundle",
             "Tender / VC-TDR-2026-0081", "Released"],
        ],
        columns=["Timestamp (MYT)", "Actor", "Event", "Object", "Outcome"],
    )
    st.dataframe(ledger, width="stretch", hide_index=True)
