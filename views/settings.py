"""
View 5: Settings & Security — section 9 of the original app.py.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import DANGER, MUTED, SUCCESS, WARN


def render() -> None:
    st.markdown("### Settings & Security")
    st.markdown(
        f'<p style="color:{MUTED};font-size:0.86rem;margin-top:-6px;">'
        "Tenant-level security posture. Controls marked <b>locked</b> are enforced by contract "
        "and cannot be relaxed from the application layer.</p>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown('<div class="vc-sec-label">Data Handling</div>', unsafe_allow_html=True)
        st.toggle("Zero Data Retention (ZDR) — enforced", value=True, disabled=True,
                  key="zdr_toggle",
                  help="Contractually locked ON. Prompts, retrieved context and model outputs "
                       "are discarded at the end of each inference request.")
        st.markdown(
            f'<div style="font-size:0.70rem;color:{SUCCESS};margin:-6px 0 12px 26px;">'
            "Locked on — modification requires a signed contract variation.</div>",
            unsafe_allow_html=True,
        )

        st.session_state.model_training_optout = st.toggle(
            "Opt out of model training & evaluation",
            value=st.session_state.model_training_optout,
            disabled=True,
            help="Client content is never used to train or evaluate models.",
        )
        st.session_state.pii_redaction = st.toggle(
            "Automatic PII redaction before embedding (PDPA 2010)",
            value=st.session_state.pii_redaction,
        )
        st.session_state.audit_log = st.toggle(
            "Audit trail (append-only, immutable)",
            value=st.session_state.audit_log,
        )

        st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
        st.markdown('<div class="vc-sec-label">Data Residency & Tenancy</div>',
                    unsafe_allow_html=True)
        st.session_state.region = st.selectbox(
            "VPC regional residency",
            [
                "Cyberjaya, Malaysia (MY-Central-1)",
                "Kuala Lumpur, Malaysia (MY-Central-2)",
                "Johor Bahru, Malaysia (MY-South-1)",
            ],
            index=[
                "Cyberjaya, Malaysia (MY-Central-1)",
                "Kuala Lumpur, Malaysia (MY-Central-2)",
                "Johor Bahru, Malaysia (MY-South-1)",
            ].index(st.session_state.region),
        )
        st.text_input("Tenant namespace", value="my-tn-00417-vaultcomply", disabled=True)
        st.text_input("Encryption key custodian (KMS)", value="Customer-held · AES-256-GCM",
                      disabled=True)
        st.markdown(
            f'<div style="font-size:0.70rem;color:{MUTED};line-height:1.6;">'
            "All regions are within Malaysian sovereign territory. Cross-border transfer is "
            "disabled at the network policy layer.</div>",
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown('<div class="vc-sec-label">Certifications &amp; Statutory Standing</div>',
                    unsafe_allow_html=True)
        certs = pd.DataFrame(
            [
                ["ISO/IEC 27001:2022", "Certified", "2027-03-14", "SIRIM QAS International"],
                ["ISO 22301:2019 (BCM)", "Certified", "2027-01-08", "SIRIM QAS International"],
                ["PDPA 2010 (Amd. 2024)", "Compliant", "Continuous", "Internal + External DPO"],
                ["Cyber Security Act 2024", "Aligned", "Continuous", "NACSA-registered NCII"],
                ["MOF / ePerolehan", "Registered", "2027-06-30", "Ministry of Finance Malaysia"],
                ["SOC 2 Type II", "Attested", "2026-11-30", "Independent CPA firm"],
            ],
            columns=["Framework", "Status", "Valid Until", "Assessor"],
        )
        st.dataframe(certs, width="stretch", hide_index=True)

        st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
        st.markdown('<div class="vc-sec-label">Current Posture</div>', unsafe_allow_html=True)

        rows = [
            ("Zero Data Retention", "Enforced", SUCCESS),
            ("Tenancy model", "Single-tenant isolated VPC", SUCCESS),
            ("Data residency", st.session_state.region, SUCCESS),
            ("PII redaction", "Enabled" if st.session_state.pii_redaction else "Disabled",
             SUCCESS if st.session_state.pii_redaction else WARN),
            ("Audit trail", "Append-only, immutable" if st.session_state.audit_log
             else "Disabled — non-compliant", SUCCESS if st.session_state.audit_log else DANGER),
            ("Model training", "Opted out (contractual)", SUCCESS),
            ("Transport security", "mTLS 1.3, allow-listed egress", SUCCESS),
            ("Human sign-off gate", "Mandatory before export", SUCCESS),
        ]
        html = "".join(
            f'<div class="vc-check"><div class="ic" style="color:{c};">●</div>'
            f'<div class="tx"><b>{label}</b> — <span style="color:{c};">{val}</span></div></div>'
            for label, val, c in rows
        )
        st.markdown(html, unsafe_allow_html=True)

        if not st.session_state.audit_log:
            st.markdown(
                '<div class="vc-alert-red" style="margin-top:12px;">'
                '<div class="t">Audit trail disabled</div>'
                '<div class="d">Statutory submissions require an immutable audit trail. '
                'Re-enable before releasing any ePerolehan bundle.</div></div>',
                unsafe_allow_html=True,
            )
