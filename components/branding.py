"""
Chrome — section 6 (part 2) of the original app.py.

The logo mark, the trust-badge bar and the two persistent frames (top header
and sidebar navigation) that wrap every view.
"""

from __future__ import annotations

import datetime as dt

import streamlit as st

from core.config import (
    ACCENT,
    APP_SUBTITLE,
    BUILD,
    CURRENT_USER,
    MUTED,
    NAV_ITEMS,
    SUCCESS,
    TENANT_ID,
)
from core.state import goto


LOGO_SVG = """
<svg width="46" height="46" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="vcShield" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#0369A1"/>
    </linearGradient>
  </defs>
  <path d="M32 3 L58 12 V31 C58 46 47 56 32 61 C17 56 6 46 6 31 V12 Z"
        fill="#0B1B33" stroke="url(#vcShield)" stroke-width="3.4" stroke-linejoin="round"/>
  <path d="M20 32.5 L28.5 41.5 L45 23"
        stroke="#F8FAFC" stroke-width="6.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""


TRUST_BADGES = [
    "✔ Zero Data Retention (ZDR) Active",
    "✔ Single-Tenant Isolated Namespace",
    "✔ Malaysia PDPA&nbsp;&amp;&nbsp;Cyber Security Act 2024 Aligned",
    "✔ ePerolehan&nbsp;&amp;&nbsp;Treasury Benchmark Ready",
]


def render_topbar() -> None:
    badges = "".join(f'<span class="vc-badge">{b}</span>' for b in TRUST_BADGES)
    st.markdown(
        f"""
        <div class="vc-topbar">
          <div style="display:flex;align-items:center;gap:15px;flex-wrap:wrap;">
            <div style="flex:0 0 46px;">{LOGO_SVG}</div>
            <div style="flex:1 1 320px;">
              <p class="vc-title">VaultComply <span>AI</span></p>
              <p class="vc-sub">{APP_SUBTITLE}</p>
            </div>
            <div style="text-align:right;">
              <span class="vc-badge vc-badge-user">User: {CURRENT_USER}</span>
              <div class="vc-mono" style="margin-top:5px;">Session {dt.datetime.now():%Y-%m-%d %H:%M} MYT</div>
            </div>
          </div>
          <div style="margin-top:10px;">{badges}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
              <div style="flex:0 0 34px;">{LOGO_SVG.replace('width="46" height="46"', 'width="34" height="34"')}</div>
              <div>
                <div style="font-size:1.02rem;font-weight:700;color:#F8FAFC;line-height:1.1;">
                  VaultComply <span style="color:#06B6D4;">AI</span></div>
                <div style="font-size:0.66rem;color:#94A3B8;">Compliance Document Engine</div>
              </div>
            </div>
            <hr class="vc-divider"/>
            <div class="vc-sec-label">Workspace</div>
            """,
            unsafe_allow_html=True,
        )

        for label, icon in NAV_ITEMS:
            active = st.session_state.page == label
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{label}",
                width="stretch",
                type="primary" if active else "secondary",
            ):
                if not active:
                    goto(label)

        st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
        st.markdown('<div class="vc-sec-label">Tenancy Status</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="font-size:0.72rem;line-height:1.9;">
              <div><span style="color:{SUCCESS};">●</span> ZDR&nbsp;&nbsp;<span style="color:{MUTED};">
                {"Enforced" if st.session_state.zdr else "Disabled"}</span></div>
              <div><span style="color:{SUCCESS};">●</span> Namespace&nbsp;&nbsp;<span style="color:{MUTED};">Isolated VPC</span></div>
              <div><span style="color:{SUCCESS};">●</span> Residency&nbsp;&nbsp;<span style="color:{MUTED};">
                {st.session_state.region.split(',')[0]}</span></div>
              <div><span style="color:{ACCENT};">●</span> Audit Log&nbsp;&nbsp;<span style="color:{MUTED};">
                {"Immutable" if st.session_state.audit_log else "Off"}</span></div>
            </div>
            <hr class="vc-divider"/>
            <div class="vc-mono" style="line-height:1.7;">
              Build {BUILD} · Enterprise<br/>Tenant ID · {TENANT_ID}<br/>© 2026 VaultComply Sdn. Bhd.
            </div>
            """,
            unsafe_allow_html=True,
        )
