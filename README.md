# VaultComply AI

**AI-Powered Business & Compliance Document Engine** — an interactive Streamlit prototype
demonstrating grounded document generation, statutory gap auditing and human-in-the-loop
sign-off for Malaysian procurement workflows (MOF / ePerolehan / PDPA / Cyber Security Act 2024).

> Prototype / demonstrator. All vault contents, scores, users and provenance snippets are
> illustrative mock data. No external AI service is called.

---

## Quick start (macOS, Apple Silicon M1, Python 3.13)

```bash
git clone <your-repo-url> vaultcomply-ai
cd vaultcomply-ai

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

streamlit run main.py          # note: main.py, not app.py
```

Opens at <http://localhost:8501>. `Ctrl+C` stops it; `deactivate` leaves the venv.

In VS Code: `Cmd+Shift+P` → **Python: Select Interpreter** → `./.venv/bin/python`, then run
the same command in the integrated terminal.

---

## Project structure

```
vaultcomply-ai/
├── main.py                     # entry point: page config, route table, footer
├── requirements.txt
├── .streamlit/
│   └── config.toml             # dark theme + server defaults
├── assets/
│   └── styles.css              # the entire stylesheet
├── core/                       # no Streamlit UI — config, content, state
│   ├── config.py               # identity, palette, paths, nav map
│   ├── theme.py                # loads styles.css, injects palette as CSS vars
│   ├── data.py                 # CATEGORIES, SLA table, clause text
│   └── state.py                # session state, k(), goto()
├── services/                   # stateless, testable, no Streamlit
│   └── exporters.py            # build_docx / build_pdf / build_bundle
├── components/                 # reusable presentation
│   ├── widgets.py              # card, kpi, gauge, file_row  -> HTML strings
│   └── branding.py             # logo, trust badges, topbar, sidebar
└── views/                      # one module per route, each exposes render()
    ├── home.py
    ├── settings.py
    ├── rbac.py
    └── workspace/              # shared by Proposal / Tender / Report
        ├── __init__.py         # 3-column layout, delegates to the columns
        ├── vault.py            # left   — semantic vault + uploader
        ├── studio.py           # centre — intake, tabs, canvas, sign-off, export
        └── auditor.py          # right  — gauge, alerts, statutory checklist
```

---

## Where each section of the original `app.py` went

| Original section | Lines | Now lives in |
| --- | --- | --- |
| 1. App config — `st.set_page_config` | 33–38 | `main.py` |
| 1. App config — identity constants | 29–31 | `core/config.py` |
| 1. App config — colour palette | 41–49 | `core/config.py` (`BG`…`WARN`, `PALETTE`) |
| 2. Global CSS injection | 56–312 | `assets/styles.css` (the CSS) + `core/theme.py` (the loader) |
| 3. Export engine | 319–558 | `services/exporters.py` |
| 4. Domain data — `SLA_*`, `DR_BODY`, `CATEGORIES`, `PROVENANCE_QUOTE` | 565–693 | `core/data.py` |
| 4. Domain data — `NAV_ITEMS` | 695–702 | `core/config.py` (it's routing, not content) |
| 5. Session state — `k`, `init_state`, `goto` | 709–732 | `core/state.py` |
| 6. Components — `card`, `kpi`, `gauge`, `file_row` | 836–878 | `components/widgets.py` |
| 6. Components — `LOGO_SVG`, `TRUST_BADGES`, `render_topbar`, `render_sidebar` | 739–833 | `components/branding.py` |
| 7. View 1 — `view_home` | 885–1012 | `views/home.py` → `render()` |
| 8. `render_vault_column` | 1019–1061 | `views/workspace/vault.py` → `render()` |
| 8. `render_draft_canvas` | 1064–1141 | `views/workspace/studio.py` → `_draft_canvas()` |
| 8. `render_signoff_and_export` | 1144–1317 | `views/workspace/studio.py` → `_signoff_and_export()` |
| 8. `render_auditor_column` | 1320–1398 | `views/workspace/auditor.py` → `render()` |
| 8. `view_workspace` — layout shell | 1401–1417 | `views/workspace/__init__.py` → `render()` |
| 8. `view_workspace` — centre column body | 1418–1583 | `views/workspace/studio.py` → `render()` |
| 9. View 5 — `view_settings` | 1594–1703 | `views/settings.py` → `render()` |
| 10. View 6 — `view_rbac` | 1710–1797 | `views/rbac.py` → `render()` |
| 11. Router — `main` | 1804–1838 | `main.py` (`ROUTES` dict + `main()`) |
| 11. Footer markup | 1820–1836 | `main.py` → `render_footer()` |

Function bodies were moved verbatim. The only renames: each view's public entry point is now
`render()`, and the two studio helpers are underscore-prefixed to mark them internal.

---

## How the pieces call each other

Dependencies point in one direction only, so no module ever imports one that imports it back:

```
main.py
  ├── core.config ─────────────── (imports nothing from the project)
  ├── core.theme     → core.config
  ├── core.state     → core.config, core.data
  ├── components.*   → core.*
  └── views.*        → components.*, core.*, services.*
```

**Adding a new page** takes three steps:

1. Create `views/my_page.py` with a `render()` function.
2. Add `("My Page", "🔧")` to `NAV_ITEMS` in `core/config.py` — the sidebar picks it up.
3. Add `"My Page": my_page.render` to `ROUTES` in `main.py`.

**Adding a document category** takes one: add an entry to `CATEGORIES` in `core/data.py`, then
a route in `WORKSPACE_ROUTES` (`core/config.py`). The whole workspace — vault, studio, auditor,
exports — is driven off that dictionary, so no view code changes.

**Changing a colour**: edit the constant in `core/config.py`. It flows to the stylesheet as a
CSS custom property (`var(--vc-accent)`) *and* to the Python f-strings that build inline styles,
so the two can't drift. Editing `assets/styles.css` alone is fine too — it's re-read whenever its
modification time changes, no restart needed.

### Two things worth knowing

- **The views folder is `views/`, not `pages/`.** A folder named `pages/` next to the entrypoint
  activates Streamlit's built-in multipage mode, which would render its own file-based navigation
  in the sidebar and fight the custom router.
- **`st.set_page_config` runs before the view imports in `main.py`.** It has to be the first
  Streamlit call in the process. Every module defers its `st.*` calls into function bodies, so
  the imports below it are safe — hence the `# noqa: E402` markers.

---

## Demo walkthrough

1. **Home & Trust Center** → security declarations, KPIs, quick-launch into a workspace.
2. **Tender Generation** → the gap auditor opens at **67% (Action Required)** with a red
   disqualification alert for the missing Section 4.2 Disaster Recovery SLA.
3. **Tab A** → *Run Compliance Gap Analysis* for the control-by-control audit breakdown.
4. **Tab B** → pick a preset prompt, then *Generate Compliant Draft*. An editable Word-style
   canvas appears with the SLA table, a `[Source: 2024_Master_Tender.pdf: Page 18]` citation tag
   and an expandable provenance snippet.
5. **Approve Clause / Sign-Off** → amber *Pending* flips to emerald *Approved*, the gauge moves
   to **100% Fully Compliant**, and the export suite unlocks.
6. **Export** → a real `.docx`, a real multi-page `.pdf`, and an ePerolehan `.zip` with a
   manifest, SHA-256 checksums and a sign-off attestation.

Each category keeps its own vault, draft and approval state.

---

## Design palette

| Token | Hex | CSS variable | Use |
| --- | --- | --- | --- |
| Slate Charcoal | `#0F172A` | `--vc-bg` | Background |
| Slate | `#1E293B` | `--vc-surface` | Surface panels |
| Hairline | `#334155` | `--vc-border` | Borders |
| Crisp White | `#F8FAFC` | `--vc-text` | Headers |
| Muted Slate | `#94A3B8` | `--vc-muted` | Subtext |
| Emerald | `#10B981` | `--vc-success` | Success / validated |
| Crimson | `#EF4444` | `--vc-danger` | Critical risk |
| Cyan | `#06B6D4` | `--vc-accent` | Interactive accent |
| Amber | `#F59E0B` | `--vc-warn` | Pending review |

---

## Notes

- `services/exporters.py` imports no Streamlit and holds no state — it's the one module you can
  unit-test directly: `from services.exporters import build_pdf`.
- The export engine writes valid OOXML and PDF bytes without `python-docx` or `reportlab`,
  keeping dependencies to two packages.
- Browser storage APIs are not used; all state lives in `st.session_state`.
- To wire this to a real retrieval backend, replace the simulated progress loops in
  `views/workspace/studio.py` and the static content in `core/data.py`.
