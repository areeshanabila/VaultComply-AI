"""
Stylesheet loading — section 2 of the original app.py.

The CSS itself now lives in ``assets/styles.css``. This module reads it,
prepends the palette from :mod:`core.config` as CSS custom properties, and
injects both into the page.
"""

from __future__ import annotations

import streamlit as st

from core import config


@st.cache_data(show_spinner=False)
def load_stylesheet(path: str, mtime: float) -> str:
    """Read the stylesheet from disk.

    ``mtime`` is part of the cache key only: touching the file busts the cache,
    so edits to styles.css show up on the next rerun without restarting.
    """
    return config.STYLESHEET.read_text(encoding="utf-8")


def palette_block() -> str:
    """Render PALETTE as a ``:root`` custom-property block."""
    body = "\n".join(f"  {name}: {value};" for name, value in config.PALETTE.items())
    return f":root {{\n{body}\n}}"


def inject_css() -> None:
    """Inject the palette variables and the global stylesheet.

    Two separate <style> tags on purpose: the stylesheet opens with an
    ``@import`` for the web fonts, and ``@import`` is only honoured at the top
    of its own sheet.
    """
    mtime = config.STYLESHEET.stat().st_mtime if config.STYLESHEET.exists() else 0.0
    st.markdown(f"<style>{palette_block()}</style>", unsafe_allow_html=True)
    st.markdown(
        f"<style>{load_stylesheet(str(config.STYLESHEET), mtime)}</style>",
        unsafe_allow_html=True,
    )
