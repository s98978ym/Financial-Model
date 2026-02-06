#!/usr/bin/env python3
"""Deploy Compatibility Checker -- Agent 2

Verifies that ALL imports used by streamlit_app.py exist in a target
branch (default: origin/main).  Run this BEFORE merging to catch
missing exports early instead of discovering them on Streamlit Cloud.

Usage:
    python scripts/check_deploy_compat.py                     # check vs origin/main
    python scripts/check_deploy_compat.py origin/some-branch  # check vs specific branch

Exit codes:
    0 = all imports verified
    1 = missing imports detected
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_FILE = PROJECT_ROOT / "src" / "app" / "streamlit_app.py"

# Imports that have intentional fallbacks (try/except in streamlit_app.py)
KNOWN_FALLBACKS = {
    # compat.py itself has inline fallback if the file is missing
    "src.app.compat": {
        "LLMClient", "LLMError",
        "SYSTEM_PROMPT_NORMAL", "SYSTEM_PROMPT_STRICT",
        "INDUSTRY_PROMPTS", "BUSINESS_MODEL_PROMPTS",
        "USER_PROMPT_TEMPLATE",
    },
    # version.py import is wrapped in try/except in sidebar
    "src.app.version": {"version_label"},
    # Individual fallbacks (used when compat.py is missing)
    "src.extract.llm_client": {"LLMError"},
    "src.extract.prompts": {
        "SYSTEM_PROMPT_NORMAL",
        "SYSTEM_PROMPT_STRICT",
        "INDUSTRY_PROMPTS",
        "BUSINESS_MODEL_PROMPTS",
        "USER_PROMPT_TEMPLATE",
    },
    "src.simulation.engine": {"SimulationEngine", "export_simulation_summary"},
}


def git_show(branch: str, filepath: str) -> str | None:
    """Read a file's content from a specific git branch."""
    try:
        result = subprocess.run(
            ["git", "show", f"{branch}:{filepath}"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return None


def extract_imports(source: str) -> List[Tuple[str, List[str]]]:
    """Extract 'from X import Y, Z' statements from Python source."""
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("src."):
                names = [alias.name for alias in node.names]
                imports.append((node.module, names))
    return imports


def module_to_filepath(module: str) -> str:
    """Convert dotted module to file path, e.g. 'src.extract.llm_client' -> 'src/extract/llm_client.py'."""
    return module.replace(".", "/") + ".py"


def find_defined_names(source: str) -> set[str]:
    """Find all top-level names defined in a Python source file."""
    names = set()
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def check_compatibility(branch: str) -> List[Dict[str, str]]:
    """Check that all imports from streamlit_app.py exist in the target branch.

    Returns a list of missing-import dicts with keys: module, name, status.
    """
    app_source = APP_FILE.read_text()
    imports = extract_imports(app_source)

    issues = []
    for module, names in imports:
        filepath = module_to_filepath(module)
        branch_source = git_show(branch, filepath)

        if branch_source is None:
            for name in names:
                fallback = module in KNOWN_FALLBACKS and name in KNOWN_FALLBACKS[module]
                issues.append({
                    "module": module,
                    "name": name,
                    "status": "FALLBACK" if fallback else "MISSING_FILE",
                    "file": filepath,
                })
            continue

        defined = find_defined_names(branch_source)
        for name in names:
            if name not in defined:
                fallback = module in KNOWN_FALLBACKS and name in KNOWN_FALLBACKS[module]
                issues.append({
                    "module": module,
                    "name": name,
                    "status": "FALLBACK" if fallback else "MISSING",
                    "file": filepath,
                })

    return issues


def main() -> None:
    branch = sys.argv[1] if len(sys.argv) > 1 else "origin/main"

    print(f"Deploy Compatibility Check")
    print(f"  App:    {APP_FILE.relative_to(PROJECT_ROOT)}")
    print(f"  Target: {branch}")
    print()

    # Fetch latest
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
    )

    issues = check_compatibility(branch)

    if not issues:
        print("  ALL IMPORTS OK -- safe to deploy")
        sys.exit(0)

    missing_count = 0
    fallback_count = 0

    for issue in issues:
        if issue["status"] == "FALLBACK":
            fallback_count += 1
            print(f"  [FALLBACK]     {issue['module']}.{issue['name']}")
            print(f"                 -> has try/except fallback, OK")
        elif issue["status"] == "MISSING_FILE":
            missing_count += 1
            print(f"  [MISSING FILE] {issue['file']}")
            print(f"                 -> {issue['name']} cannot be imported")
        else:
            missing_count += 1
            print(f"  [MISSING]      {issue['module']}.{issue['name']}")
            print(f"                 -> not defined in {issue['file']} on {branch}")

    print()
    print(f"Summary: {fallback_count} with fallback, {missing_count} MISSING")

    if missing_count > 0:
        print()
        print("FAIL: These imports will cause ImportError on deployment.")
        print("  Options:")
        print("    1. Add try/except fallback in streamlit_app.py")
        print("    2. Merge the code that defines these names to the target branch")
        sys.exit(1)
    else:
        print("  All gaps covered by fallbacks -- safe to deploy")
        sys.exit(0)


if __name__ == "__main__":
    main()
