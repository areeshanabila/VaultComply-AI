"""
VaultComply AI — AI-Powered Business & Compliance Document Engine
=================================================================
Application entry point.

    streamlit run main.py

This file does four things and nothing else:

    1. Configures the Streamlit page (must happen before any other st.* call).
    2. Injects the theme and initialises session state.
    3. Renders the persistent chrome — sidebar navigation and top header.
    4. Dispatches the current route to a view module.

Everything else lives in a package:

    core/         config, theme, domain content, session state
    services/     stateless document export
    components/   reusable presentational helpers and chrome
    views/        one module per route, each exposing render()
    assets/       styles.css

See README.md for the section-by-section map from the original single-file
app.py to this layout.
"""

from __future__ import annotations

import streamlit as st

from core import config

# ── 1. Page configuration ───────────────────────────────────────────────────
# Must be the first Streamlit call in the process. Every module below defers
# its st.* calls to function bodies, so importing them here is safe.

if "sidebar_state" not in st.session_state:
    st.session_state["sidebar_state"] = "expanded"

st.set_page_config(
    page_title=f"{config.APP_NAME} — {config.APP_SUBTITLE}",
    page_icon=config.PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

from components.branding import render_sidebar, render_topbar  # noqa: E402
from core.state import init_state  # noqa: E402
from core.theme import inject_css  # noqa: E402
from views import home, rbac, settings, workspace  # noqa: E402

# ── 2. Route table ──────────────────────────────────────────────────────────
#: Route label -> zero-argument renderer. Labels match core.config.NAV_ITEMS,
#: which is what the sidebar renders and what st.session_state["page"] holds.
ROUTES: dict[str, callable] = {
    "Home & Trust Center": home.render,
    "Settings & Security": settings.render,
    "User Access (RBAC)": rbac.render,
    **{
        label: (lambda category=category: workspace.render(category))
        for label, category in config.WORKSPACE_ROUTES.items()
    },
}


def render_footer() -> None:
    st.markdown(
        f"""
        <hr class="vc-divider"/>
        <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;
                    font-size:0.68rem;color:{config.MUTED};padding-bottom:10px;">
          <div>{config.APP_NAME} · Build {config.BUILD} Enterprise ·
               Tenant {config.TENANT_ID}</div>
          <div>Zero Data Retention enforced · Single-tenant isolated namespace ·
               Data residency: {st.session_state.region}</div>
          <div>© 2026 VaultComply Sdn. Bhd.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    inject_css()
    init_state()

    render_sidebar()
    render_topbar()

    route = ROUTES.get(st.session_state.page, ROUTES[config.DEFAULT_PAGE])
    route()

    render_footer()


if __name__ == "__main__":
    main()
