"""
View 6: User Access (RBAC) — section 10 of the original app.py.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.widgets import card, kpi
from core.config import ACCENT, MUTED, SUCCESS, WARN


def render() -> None:
    st.markdown("### User Access")
    st.markdown(
        f'<p style="color:{MUTED};font-size:0.86rem;margin-top:-6px;">'
        "Role-based access control for the tenant namespace. Export release is restricted to "
        "roles holding the <b>Sign-Off</b> capability.</p>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi("Active Users", "7", "across 3 roles", ACCENT), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Sign-Off Authority", "2", "Compliance Leads", SUCCESS),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("MFA Enrolment", "100%", "hardware key enforced", SUCCESS),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(kpi("Dormant Accounts", "1", "review recommended", WARN),
                    unsafe_allow_html=True)

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">User Directory</div>', unsafe_allow_html=True)

    users = pd.DataFrame(
        [
            ["Nurul A. Hashim", "nurul.hashim@tenant.my", "Compliance Lead",
             "Read · Generate · Sign-Off · Export", "Hardware key", "2026-09-10 09:42", "Active"],
            ["Daniel Tan Wei Jian", "daniel.tan@tenant.my", "Compliance Lead",
             "Read · Generate · Sign-Off · Export", "Hardware key", "2026-09-09 18:05", "Active"],
            ["Farah Idris", "farah.idris@tenant.my", "Proposal Writer",
             "Read · Generate", "TOTP", "2026-09-10 09:15", "Active"],
            ["Arif Rahman", "arif.rahman@tenant.my", "Proposal Writer",
             "Read · Generate", "TOTP", "2026-09-08 16:22", "Active"],
            ["Siti Nadhrah Yusof", "siti.yusof@tenant.my", "Proposal Writer",
             "Read · Generate", "TOTP", "2026-09-10 08:47", "Active"],
            ["Kavitha Ramasamy", "kavitha.r@tenant.my", "Auditor",
             "Read · Export Audit Log", "Hardware key", "2026-09-09 17:38", "Active"],
            ["James Loh", "james.loh@tenant.my", "Auditor",
             "Read · Export Audit Log", "TOTP", "2026-07-21 10:04", "Dormant"],
        ],
        columns=["User", "Email", "Role", "Capabilities", "MFA", "Last Active (MYT)", "Status"],
    )
    st.dataframe(users, width="stretch", hide_index=True)

    st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
    st.markdown('<div class="vc-sec-label">Role Capability Matrix</div>', unsafe_allow_html=True)

    matrix = pd.DataFrame(
        [
            ["View vault documents", "✔", "✔", "✔"],
            ["Index new source documents", "✔", "✔", "✘"],
            ["Run compliance gap analysis", "✔", "✔", "✔"],
            ["Generate drafts", "✔", "✔", "✘"],
            ["Edit draft canvas", "✔", "✔", "✘"],
            ["Approve clause / sign-off", "✔", "✘", "✘"],
            ["Export statutory bundles", "✔", "✘", "✘"],
            ["Export audit trail", "✔", "✘", "✔"],
            ["Modify security settings", "✔", "✘", "✘"],
            ["Manage users & roles", "✔", "✘", "✘"],
        ],
        columns=["Capability", "Compliance Lead", "Proposal Writer", "Auditor"],
    )
    st.dataframe(matrix, width="stretch", hide_index=True, height=390)

    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown(
            card("Compliance Lead",
                 "Full authority. Sole holder of the clause sign-off capability and the only "
                 "role permitted to release statutory export bundles or amend tenant security "
                 "settings. 2 active holders.", SUCCESS),
            unsafe_allow_html=True)
    with r2:
        st.markdown(
            card("Proposal Writer",
                 "Drafting authority. May index sources, run gap analysis, generate and edit "
                 "drafts — but cannot approve a clause or export. Enforces separation of duties. "
                 "3 active holders.", ACCENT),
            unsafe_allow_html=True)
    with r3:
        st.markdown(
            card("Auditor",
                 "Read-only assurance. May inspect vault contents, re-run gap analysis and "
                 "export the immutable audit ledger. Cannot generate, edit or approve content. "
                 "2 holders (1 dormant).", WARN),
            unsafe_allow_html=True)
