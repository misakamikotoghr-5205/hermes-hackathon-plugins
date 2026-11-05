"""Static & runtime validator mirroring `hermes plugins validate` and Catalog Rules 1-18."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests"))

from test_all_plugins import MockPluginContext, load_plugin_package  # noqa: E402

PLUGIN_DIRS = ["claim-market-router", "hunk-consent-guard", "source-trail-supervisor"]

FORBIDDEN_PATTERNS = (
    "auth.json",
    ".codex/auth.json",
    "AIAgent.",
    "window.hermesDesktop",
)


def parse_simple_yaml_lists(yaml_text: str) -> dict[str, list[str]]:
    """Lightweight parser for provides_tools, provides_hooks, provides_middleware in plugin.yaml."""
    result: dict[str, list[str]] = {
        "provides_tools": [],
        "provides_hooks": [],
        "provides_middleware": [],
    }
    current_key: str | None = None
    for raw_line in yaml_text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if indent == 0 and stripped.endswith(":"):
            key = stripped[:-1].strip()
            current_key = key if key in result else None
        elif indent == 0 and ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip()
            if key in result and val == "[]":
                result[key] = []
            current_key = None
        elif current_key and stripped.startswith("- "):
            result[current_key].append(stripped[2:].strip())
    return result


def validate_all() -> int:
    errors: list[str] = []
    for pdir in PLUGIN_DIRS:
        root = REPO_ROOT / pdir
        manifest_path = root / "plugin.yaml"
        init_path = root / "__init__.py"
        readme_path = root / "README.md"
        catalog_path = REPO_ROOT / "plugin-catalog" / f"{pdir}.yaml"

        for req in (manifest_path, init_path, readme_path, catalog_path):
            if not req.exists():
                errors.append(f"[{pdir}] Missing required file: {req}")

        manifest_lists = parse_simple_yaml_lists(manifest_path.read_text(encoding="utf-8"))
        pkg = load_plugin_package(pdir)
        ctx = MockPluginContext()
        pkg.register(ctx)

        # Rule 6: Declared capabilities must match reality
        reg_tools = sorted(ctx.tools.keys())
        decl_tools = sorted(manifest_lists["provides_tools"])
        if reg_tools != decl_tools:
            errors.append(f"[{pdir}] provides_tools mismatch: declared={decl_tools}, registered={reg_tools}")

        reg_hooks = sorted(ctx.hooks.keys())
        decl_hooks = sorted(manifest_lists["provides_hooks"])
        if reg_hooks != decl_hooks:
            errors.append(f"[{pdir}] provides_hooks mismatch: declared={decl_hooks}, registered={reg_hooks}")

        reg_mw = sorted(ctx.middleware.keys())
        decl_mw = sorted(manifest_lists["provides_middleware"])
        if reg_mw != decl_mw:
            errors.append(f"[{pdir}] provides_middleware mismatch: declared={decl_mw}, registered={reg_mw}")

        # Rule 7 / 9 / 11: AST and source scan
        for py_file in root.rglob("*.py"):
            src = py_file.read_text(encoding="utf-8")
            ast.parse(src, filename=str(py_file))
            for pat in FORBIDDEN_PATTERNS:
                if pat in src:
                    errors.append(f"[{pdir}] Forbidden pattern {pat!r} in {py_file.name}")

        print(
            f"[OK] {pdir}: tools={len(reg_tools)}, hooks={len(reg_hooks)}, "
            f"middleware={len(reg_mw)}, delegation_providers={len(ctx.delegation_providers)}, "
            f"skills={len(ctx.skills)}, slash_commands={len(ctx.commands)}, cli_commands={len(ctx.cli_commands)}"
        )

    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    print("\nAll 3 Hermes plugins passed manifest parity, AST, and Catalog Rules validation!")
    return 0


if __name__ == "__main__":
    raise SystemExit(validate_all())
