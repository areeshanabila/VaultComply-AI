"""
Application constants — section 1 of the original app.py.

Single source of truth for identity, the colour palette and the navigation
map. Imported by nearly every other module; imports nothing from the project
itself, so it can never take part in a circular import.
"""

from __future__ import annotations

from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
STYLESHEET = ASSETS_DIR / "styles.css"

# ── Identity ────────────────────────────────────────────────────────────────
APP_NAME = "VaultComply AI"


APP_SUBTITLE = "AI-Powered Business & Compliance Document Engine"


CURRENT_USER = "Compliance Lead"

PAGE_ICON = "🛡️"
BUILD = "2.4.1"
TENANT_ID = "MY-TN-00417"

# ── Enterprise Dark Mode palette ────────────────────────────────────────────
BG = "#0F172A"        # Slate Charcoal — background


SURFACE = "#1E293B"   # Slate — surface panels


BORDER = "#334155"    # hairline borders


TEXT = "#F8FAFC"      # crisp white


MUTED = "#94A3B8"     # muted slate subtext


SUCCESS = "#10B981"   # emerald — validated


DANGER = "#EF4444"    # crimson — critical risk


ACCENT = "#06B6D4"    # cyan — interactive accent


WARN = "#F59E0B"      # amber — pending review

# Extended tokens used by the stylesheet only.
DEEP = "#0B1220"          # inset / recessed surfaces
SURFACE_2 = "#16202f"     # tab strip, idle chips
BORDER_SOFT = "#263243"   # inner dividers
HOVER = "#16243d"         # button hover fill
ACCENT_HI = "#22d3ee"     # accent hover
ACCENT_INK = "#04283a"    # text on an accent fill
DISABLED = "#475569"
TOPBAR_FROM = "#131f38"

#: Emitted as a ``:root { ... }`` block by :func:`core.theme.inject_css`, so
#: ``assets/styles.css`` can reference every colour as ``var(--vc-name)``.
PALETTE: dict[str, str] = {
    "--vc-bg": BG,
    "--vc-surface": SURFACE,
    "--vc-border": BORDER,
    "--vc-text": TEXT,
    "--vc-muted": MUTED,
    "--vc-success": SUCCESS,
    "--vc-danger": DANGER,
    "--vc-accent": ACCENT,
    "--vc-warn": WARN,
    "--vc-deep": DEEP,
    "--vc-surface-2": SURFACE_2,
    "--vc-border-soft": BORDER_SOFT,
    "--vc-hover": HOVER,
    "--vc-accent-hi": ACCENT_HI,
    "--vc-accent-ink": ACCENT_INK,
    "--vc-disabled": DISABLED,
    "--vc-topbar-from": TOPBAR_FROM,
}

# ── Navigation ──────────────────────────────────────────────────────────────
NAV_ITEMS = [
    ("Home & Trust Center", "🏛️"),
    ("Proposal Generation", "📝"),
    ("Tender Generation", "📋"),
    ("Report Generation", "📊"),
    ("Settings & Security", "⚙️"),
    ("User Access (RBAC)", "👥"),
]

#: Condensed labels for the horizontal top-nav strip, where six tabs share the
#: content width. Keys must match NAV_ITEMS labels exactly; the sidebar keeps
#: the full labels.
NAV_SHORT: dict[str, str] = {
    "Home & Trust Center": "Trust Center",
    "Proposal Generation": "Proposal",
    "Tender Generation": "Tender",
    "Report Generation": "Report",
    "Settings & Security": "Settings",
    "User Access (RBAC)": "Access (RBAC)",
}

#: The three generation workspaces, collapsed under one sidebar group.
#: (route label, icon, label shown inside the group).
DOC_GEN_LABEL = "Document Generation"
DOC_GEN_ICON = "🗂️"
DOC_GEN_ITEMS: list[tuple[str, str, str]] = [
    ("Proposal Generation", "📝", "Proposal"),
    ("Tender Generation", "📋", "Tender"),
    ("Report Generation", "📊", "Report"),
]

#: Sidebar rendering order, declarative so the shape of the menu lives here
#: rather than inside render_sidebar. "item" is a plain route button; "group"
#: is the expandable Document Generation block built from DOC_GEN_ITEMS.
#: NAV_ITEMS above stays the flat, canonical list of every route.
SIDEBAR_NAV: list[tuple[str, str, str]] = [
    ("item", "Home & Trust Center", "🏛️"),
    ("group", DOC_GEN_LABEL, DOC_GEN_ICON),
    ("item", "Settings & Security", "⚙️"),
    ("item", "User Access (RBAC)", "👥"),
]

#: Landing page, and the fallback for an unknown route.
DEFAULT_PAGE = NAV_ITEMS[0][0]

#: Route label -> category key, for the three generation workspaces.
WORKSPACE_ROUTES: dict[str, str] = {
    "Proposal Generation": "Proposal",
    "Tender Generation": "Tender",
    "Report Generation": "Report",
}