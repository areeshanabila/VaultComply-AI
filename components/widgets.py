"""
Reusable presentational helpers — section 6 (part 1) of the original app.py.

Each function returns an HTML *string*; the caller decides where to render it
with ``st.markdown(..., unsafe_allow_html=True)``. Keeping them pure makes them
trivially composable and keeps layout decisions in the views.
"""

from __future__ import annotations

from core.config import ACCENT, BORDER, MUTED, SUCCESS, SURFACE


def card(title: str, body: str, accent: str = ACCENT, icon: str = "") -> str:
    return f"""
    <div class="vc-card" style="border-left:3px solid {accent};">
      <h4 style="color:{accent} !important;">{icon} {title}</h4>
      <p>{body}</p>
    </div>"""


def kpi(label: str, value: str, delta: str = "", accent: str = ACCENT) -> str:
    return f"""
    <div class="vc-kpi" style="border-left-color:{accent};">
      <div class="lab">{label}</div>
      <div class="val">{value}</div>
      <div class="delta" style="color:{accent};">{delta}</div>
    </div>"""


def gauge(pct: int, caption: str, color: str) -> str:
    deg = pct * 3.6
    return f"""
    <div style="display:flex;justify-content:center;padding:6px 0 2px 0;">
      <div style="width:158px;height:158px;border-radius:50%;
                  background:conic-gradient({color} 0deg {deg}deg, #263243 {deg}deg 360deg);
                  display:flex;align-items:center;justify-content:center;
                  box-shadow:0 0 26px {color}33;">
        <div style="width:124px;height:124px;border-radius:50%;background:{SURFACE};
                    border:1px solid {BORDER};display:flex;flex-direction:column;
                    align-items:center;justify-content:center;">
          <div style="font-size:2.0rem;font-weight:700;color:{color};line-height:1;">{pct}%</div>
          <div style="font-size:0.66rem;color:{MUTED};margin-top:5px;text-align:center;
                      max-width:104px;line-height:1.3;">{caption}</div>
        </div>
      </div>
    </div>"""


def file_row(name: str, status: str = "Indexed", color: str = SUCCESS) -> str:
    return f"""
    <div class="vc-file">
      <div class="dot" style="background:{color};box-shadow:0 0 7px {color};"></div>
      <div class="nm">{name}</div>
      <div class="st" style="color:{color};">{status}</div>
    </div>"""
