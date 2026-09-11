"""
Project integrity checker for VaultComply AI.

    python3 doctor.py

Cross-file refactors fail in a specific, annoying way: a name gets renamed or
dropped in one module and nothing complains until the exact line that uses it
runs — often several clicks into the UI. This script checks every
project-internal import statically, so those breaks surface in one shot
without launching Streamlit.

It reports:
  * imports of a name a module does not define        (the common one)
  * imports of a project module that does not exist
  * circular imports between project packages
  * a `pages/` folder, which hijacks Streamlit's navigation
  * a foreign `core` package shadowing the local one

Exit code is 0 when clean, 1 when anything is wrong.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGES = {"core", "services", "components", "views"}

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def source_files() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.py")
        if "__pycache__" not in p.parts and ".venv" not in p.parts
    )


def module_name(path: Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def defined_names(tree: ast.Module) -> set[str]:
    """Top-level names a module binds: defs, classes, assignments, imports."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return names


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []

    trees: dict[str, ast.Module] = {}
    paths: dict[str, Path] = {}
    for path in source_files():
        try:
            trees[module_name(path)] = ast.parse(path.read_text(encoding="utf-8"))
            paths[module_name(path)] = path
        except SyntaxError as exc:
            problems.append(f"{path.relative_to(ROOT)}: syntax error line {exc.lineno}: {exc.msg}")

    exports = {name: defined_names(tree) for name, tree in trees.items()}
    edges: dict[str, set[str]] = {name: set() for name in trees}

    # ── every project-internal import ───────────────────────────────────────
    for name, tree in trees.items():
        rel = paths[name].relative_to(ROOT)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                target = node.module or ""
                if target.split(".")[0] not in PACKAGES:
                    continue
                # A package importing its own submodules (`from views.workspace
                # import vault` inside views/workspace/__init__.py) is normal,
                # not a cycle — record the submodules, not the package itself.
                if target != name:
                    edges[name].add(target)
                for alias in node.names:
                    imported = alias.name
                    submodule = f"{target}.{imported}"
                    if submodule in trees:          # `from views.workspace import vault`
                        edges[name].add(submodule)
                        continue
                    if target not in exports:
                        problems.append(f"{rel}:{node.lineno}  no such module '{target}'")
                        continue
                    if imported not in exports[target]:
                        problems.append(
                            f"{rel}:{node.lineno}  '{target}' does not define "
                            f"'{imported}'  {DIM}(add it, or fix the import){RESET}"
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in PACKAGES:
                        edges[name].add(alias.name)
                        if alias.name not in trees:
                            problems.append(
                                f"{rel}:{node.lineno}  no such module '{alias.name}'")

    # ── attribute access on an imported module: config.FOO ──────────────────
    for name, tree in trees.items():
        rel = paths[name].relative_to(ROOT)
        aliases: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "") in PACKAGES:
                for alias in node.names:
                    full = f"{node.module}.{alias.name}"
                    if full in trees:
                        aliases[alias.asname or alias.name] = full
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in trees:
                        aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id in aliases):
                target = aliases[node.value.id]
                if node.attr not in exports.get(target, set()):
                    problems.append(
                        f"{rel}:{node.lineno}  '{target}' has no attribute "
                        f"'{node.attr}'  {DIM}(referenced as {node.value.id}.{node.attr}){RESET}"
                    )

    # ── circular imports ────────────────────────────────────────────────────
    state: dict[str, int] = {}

    def visit(node: str, trail: list[str]) -> None:
        if state.get(node) == 1:
            cycle = trail[trail.index(node):] + [node]
            problems.append("circular import: " + " -> ".join(cycle))
            return
        if state.get(node) == 2:
            return
        state[node] = 1
        for nxt in sorted(edges.get(node, ())):
            if nxt in edges:
                visit(nxt, trail + [node])
        state[node] = 2

    for node in sorted(edges):
        visit(node, [])

    # ── environment traps ───────────────────────────────────────────────────
    if (ROOT / "pages").is_dir():
        problems.append(
            "a 'pages/' folder exists — Streamlit will take over the sidebar "
            "navigation and fight the custom router. Rename it to 'views/'.")

    saved = sys.path[:]
    sys.path = [p for p in sys.path if Path(p or ".").resolve() != ROOT]
    try:
        spec = importlib.util.find_spec("core")
        if spec and spec.origin and ROOT not in Path(spec.origin).parents:
            notes.append(f"a foreign 'core' package is installed at {spec.origin} — "
                         f"harmless while you run from the project root, but "
                         f"'pip uninstall core' removes the ambiguity")
    except (ImportError, ValueError):
        pass
    finally:
        sys.path = saved

    # ── report ──────────────────────────────────────────────────────────────
    print(f"\nVaultComply AI — project check")
    print(f"{DIM}{ROOT}{RESET}")
    print(f"{DIM}{len(trees)} modules, "
          f"{sum(len(v) for v in edges.values())} internal imports{RESET}\n")

    for note in notes:
        print(f"{YELLOW}  note{RESET}  {note}")

    if problems:
        for p in problems:
            print(f"{RED}  fail{RESET}  {p}")
        print(f"\n{RED}{len(problems)} problem(s) found.{RESET}\n")
        return 1

    print(f"{GREEN}  ok{RESET}    every internal import resolves, no cycles\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
