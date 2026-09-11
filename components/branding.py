"""
Chrome — persistent frames (top header and sidebar navigation).
"""

from __future__ import annotations

import datetime as dt
import streamlit as st
import streamlit.components.v1 as components

from core.config import (
    APP_SUBTITLE,
    CURRENT_USER,
    DOC_GEN_ICON,
    DOC_GEN_ITEMS,
    DOC_GEN_LABEL,
    SIDEBAR_NAV,
    ACCENT,
    MUTED,
    SUCCESS,
    BUILD,
    TENANT_ID,
)

from core.state import goto

LOGO_SVG = """
<svg width="42" height="42" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
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
    "✔ Malaysia PDPA & Cyber Security Act 2024 Aligned",
    "✔ ePerolehan & Treasury Benchmark Ready",
]


#: Binds the topbar's hamburger to Streamlit's own sidebar toggle.
#:
#: Two things make this necessary:
#:
#: 1. ``st.markdown`` sanitises the HTML it renders and STRIPS ``onclick``
#:    attributes, so an inline handler on the button is silently discarded --
#:    the button renders but is inert. Script tags in st.markdown are dropped
#:    too. ``components.html`` runs in an iframe where scripts DO execute, and
#:    ``window.parent.document`` reaches the real app document from there.
#:
#: 2. Streamlit uses a DIFFERENT control for each direction, and BOTH exist in
#:    the DOM at all times -- the collapse button simply slides off-screen with
#:    the sidebar. Picking by ``aria-expanded`` is what makes the toggle work
#:    in both directions instead of only one.
#:
#: The listener is delegated from the document and installed once, so it keeps
#: working after Streamlit re-renders the topbar on every rerun.
_SIDEBAR_TOGGLE_JS = """
<script>
(function () {
  const doc = window.parent.document;

  /* Publish the real topbar height as --vc-topbar-h. styles.css derives the
     sidebar's top offset and height, and the main content's top padding, from
     that one property -- so when the trust badges wrap onto a second row at a
     narrow width, the sidebar follows the header down instead of hiding
     underneath it. */
  function syncTopbarHeight() {
    const bar = doc.querySelector('.vc-topbar');
    if (!bar) return;
    const h = Math.round(bar.getBoundingClientRect().height);
    if (h > 0) doc.documentElement.style.setProperty('--vc-topbar-h', h + 'px');
  }

  /* Give the draft canvas a true A4 footprint (1 : 1.414) from its own live
     width, so the sheet keeps page proportions whatever the column is doing.
     styles.css carries a fixed fallback for before this runs. */
  function syncSheetAspect() {
    doc.querySelectorAll('.st-key-vc-a4-sheet').forEach(function (sheet) {
      const w = sheet.getBoundingClientRect().width;
      if (w > 0) sheet.style.minHeight = Math.round(w * 1.414) + 'px';
    });
  }

  /* Grow the draft textarea to its content so the page never shows an inner
     scrollbar -- a scrollbar mid-paper is what gives away that it is a form
     field. Python sizes it on render; this keeps up while the user types. */
  function autoGrow(el) {
    if (!el || el.tagName !== 'TEXTAREA') return;
    if (!el.closest('.st-key-vc-a4-sheet')) return;
    el.style.height = 'auto';
    el.style.height = (el.scrollHeight + 2) + 'px';
  }

  function growAll() {
    doc.querySelectorAll('.st-key-vc-a4-sheet textarea').forEach(autoGrow);
  }

  /* Runs on EVERY rerun, unlike the click binding below: Streamlit rebuilds
     the topbar each time, so the observer has to be re-attached to the new
     element. */
  syncTopbarHeight();

  /* The sheet is NOT in the DOM when this script first runs -- the toggle
     iframe is rendered by render_topbar(), before the route renders the
     workspace below it. Timers guessing at "later" are flaky, so a
     MutationObserver watches for the sheet appearing instead and sizes it
     then. Only childList is observed, so the inline heights written by
     growAll() cannot retrigger it; the rAF debounce collapses bursts. */
  if (!doc.__vcSheetKick) {
    let queued = false;
    doc.__vcSheetKick = function () {
      if (queued) return;
      queued = true;
      window.parent.requestAnimationFrame(function () {
        queued = false;
        syncSheetAspect();
        growAll();
      });
    };
    doc.__vcSheetObserver = new MutationObserver(doc.__vcSheetKick);
    doc.__vcSheetObserver.observe(doc.body, { childList: true, subtree: true });
  }
  doc.__vcSheetKick();
  const bar = doc.querySelector('.vc-topbar');
  if (bar && window.ResizeObserver) {
    if (doc.__vcTopbarRO) doc.__vcTopbarRO.disconnect();
    doc.__vcTopbarRO = new ResizeObserver(syncTopbarHeight);
    doc.__vcTopbarRO.observe(bar);
  }
  if (!doc.__vcResizeBound) {
    doc.__vcResizeBound = true;
    window.parent.addEventListener('resize', function () {
      syncTopbarHeight();
      syncSheetAspect();
    });
    /* Delegated so it survives Streamlit replacing the textarea on rerun. */
    doc.addEventListener('input', function (ev) { autoGrow(ev.target); }, true);
  }

  function findToggle() {
    const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
    const expanded = sidebar && sidebar.getAttribute('aria-expanded') === 'true';

    const collapse = [
      '[data-testid="stSidebarCollapseButton"] button',
      'button[data-testid="stBaseButton-headerNoPadding"]',
      'button[data-testid="baseButton-headerNoPadding"]',
    ];
    const expand = [
      'button[data-testid="stExpandSidebarButton"]',
      '[data-testid="stSidebarCollapsedControl"] button',
      '[data-testid="collapsedControl"] button',
      '[data-testid="collapsedControl"]',
    ];

    for (const sel of (expanded ? collapse : expand)) {
      const el = doc.querySelector(sel);
      if (el) return el;
    }
    // Last resort for Streamlit versions that rename the test ids.
    return doc.querySelector('button[aria-label*="sidebar" i]');
  }

  if (doc.__vcSidebarBound) return;
  doc.__vcSidebarBound = true;

  doc.addEventListener('click', function (ev) {
    const target = ev.target.closest
      ? ev.target.closest('#vc-sidebar-trigger, .vc-toggle-btn')
      : null;
    if (!target) return;
    ev.preventDefault();
    ev.stopPropagation();
    const toggle = findToggle();
    if (toggle) toggle.click();
  }, true);
})();
</script>
"""


def render_topbar() -> None:
    badges_html = "".join(f'<span class="vc-badge">{b}</span>' for b in TRUST_BADGES)
    now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    st.markdown(
        f"""
        <div class="vc-topbar">
          <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
            <!-- Trigger button built into the topbar. The click handler is
                 installed by _SIDEBAR_TOGGLE_JS below, not inline: st.markdown
                 strips onclick attributes. -->
            <button id="vc-sidebar-trigger" class="vc-toggle-btn"
                    title="Toggle Navigation Sidebar" aria-label="Toggle navigation sidebar">
              ☰
            </button>
            <div style="flex:0 0 42px;">{LOGO_SVG}</div>
            <div style="flex:1 1 320px;">
              <p class="vc-title">VaultComply <span>AI</span></p>
              <p class="vc-sub">{APP_SUBTITLE}</p>
            </div>
            <div style="text-align:right;">
              <span class="vc-badge vc-badge-user">User: {CURRENT_USER}</span>
              <div class="vc-mono" style="margin-top:4px;">Session {now_str} MYT</div>
            </div>
          </div>
          <div style="margin-top:8px;">{badges_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _install_sidebar_toggle()


def _install_sidebar_toggle() -> None:
    """Ship the toggle handler into the page inside a zero-height iframe.

    ``components.html`` is the only Streamlit API that executes a script with
    access to the parent document: ``st.markdown`` and ``st.html`` strip
    scripts, and ``st.iframe`` takes a URL, so a data: URL there would land on
    an opaque origin and be blocked from reaching ``window.parent``.

    It is deprecated in favour of ``st.iframe`` and logs a notice on the
    server, so the call is guarded: if a future Streamlit removes it, the
    hamburger goes inert rather than taking the whole app down with it. The
    sidebar is still reachable then by un-hiding Streamlit's native control in
    styles.css (the block above the ``.vc-toggle-btn`` rules).
    """
    try:
        components.html(_SIDEBAR_TOGGLE_JS, height=0)
    except Exception:  # pragma: no cover - only on a future API removal
        pass


def _nav_button(label: str, icon: str, text: str, key: str) -> None:
    """One sidebar route button. Highlights itself when it is the live route."""
    active = st.session_state.get("page") == label
    if st.button(
        f"{icon}  {text}",
        key=key,
        use_container_width=True,
        type="primary" if active else "secondary",
    ):
        if not active:
            goto(label)


def _nav_group() -> None:
    """The collapsible Document Generation block.

    Open/closed lives in ``st.session_state['nav_docgen_open']`` rather than in
    an ``st.expander``: an expander resets to its ``expanded`` argument on every
    rerun, so the group would snap shut each time you picked a workspace.

    The header takes the active highlight only while the group is CLOSED and a
    workspace is the live route — otherwise the highlight would land on both
    the header and the child at once.
    """
    open_ = st.session_state.get("nav_docgen_open", True)
    on_workspace = st.session_state.get("page") in {r for r, _, _ in DOC_GEN_ITEMS}

    with st.container(key="vc-nav-group-head"):
        if st.button(
            f"{DOC_GEN_ICON}  {DOC_GEN_LABEL}  {'▾' if open_ else '▸'}",
            key="nav_group_docgen",
            use_container_width=True,
            type="primary" if (on_workspace and not open_) else "secondary",
        ):
            st.session_state.nav_docgen_open = not open_
            st.rerun()

    if open_:
        with st.container(key="vc-nav-group-items"):
            for label, icon, short in DOC_GEN_ITEMS:
                _nav_button(label, icon, short, key=f"nav_{label}")


def render_sidebar() -> None:
    with st.sidebar:
        # The branding block that used to sit here is gone: the fixed topbar
        # already carries the logo, name and subtitle, and repeating it pushed
        # the nav down for no gain.
        st.markdown('<div class="vc-sec-label">Workspace</div>', unsafe_allow_html=True)

        for kind, label, icon in SIDEBAR_NAV:
            if kind == "group":
                _nav_group()
            else:
                _nav_button(label, icon, label, key=f"nav_{label}")

        region_str = st.session_state.get("region", "ap-southeast-1 (Malaysia)").split(",")[0]
        zdr_val = "Enforced" if st.session_state.get("zdr", True) else "Disabled"
        audit_val = "Immutable" if st.session_state.get("audit_log", True) else "Off"

        st.markdown('<hr class="vc-divider"/>', unsafe_allow_html=True)
        st.markdown('<div class="vc-sec-label">Tenancy Status</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="font-size:0.72rem;line-height:1.9;">
              <div><span style="color:{SUCCESS};">●</span> ZDR&nbsp;&nbsp;<span style="color:{MUTED};">
                {zdr_val}</span></div>
              <div><span style="color:{SUCCESS};">●</span> Namespace&nbsp;&nbsp;<span style="color:{MUTED};">Isolated VPC</span></div>
              <div><span style="color:{SUCCESS};">●</span> Residency&nbsp;&nbsp;<span style="color:{MUTED};">
                {region_str}</span></div>
              <div><span style="color:{ACCENT};">●</span> Audit Log&nbsp;&nbsp;<span style="color:{MUTED};">
                {audit_val}</span></div>
            </div>
            <hr class="vc-divider"/>
            <div class="vc-mono" style="line-height:1.7;">
              Build {BUILD} · Enterprise<br/>Tenant ID · {TENANT_ID}<br/>© 2026 VaultComply Sdn. Bhd.
            </div>
            """,
            unsafe_allow_html=True,
        )