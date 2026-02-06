"""Startup Smoke Test -- Agent 3

Verifies that the Streamlit app can import all its dependencies
without crashing.  This catches the exact class of bug that caused
the Streamlit Cloud ImportError -- missing names in the import chain.

Run as part of the normal test suite:
    pytest tests/test_app_startup.py -v
"""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_FILE = PROJECT_ROOT / "src" / "app" / "streamlit_app.py"


def _extract_src_imports(source: str) -> List[Tuple[str, List[str]]]:
    """Parse all 'from src.X import Y' statements from source."""
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("src."):
                names = [alias.name for alias in node.names]
                imports.append((node.module, names))
    return imports


class TestAppStartup:
    """Verify that every import used by streamlit_app.py resolves."""

    @pytest.fixture(autouse=True)
    def _ensure_project_root_on_path(self) -> None:
        root = str(PROJECT_ROOT)
        if root not in sys.path:
            sys.path.insert(0, root)

    def test_all_src_modules_importable(self) -> None:
        """Each src.* module referenced in streamlit_app.py can be imported."""
        source = APP_FILE.read_text()
        imports = _extract_src_imports(source)
        modules = {mod for mod, _names in imports}

        failures = []
        for mod in sorted(modules):
            try:
                importlib.import_module(mod)
            except ImportError as exc:
                failures.append(f"{mod}: {exc}")

        assert not failures, (
            "These modules failed to import:\n" + "\n".join(failures)
        )

    def test_all_names_importable(self) -> None:
        """Each name imported from src.* modules actually exists."""
        source = APP_FILE.read_text()
        imports = _extract_src_imports(source)

        failures = []
        for mod_name, names in imports:
            try:
                mod = importlib.import_module(mod_name)
            except ImportError:
                # Already caught by test_all_src_modules_importable
                continue
            for name in names:
                if not hasattr(mod, name):
                    failures.append(f"{mod_name}.{name} does not exist")

        assert not failures, (
            "These names are imported but do not exist:\n" + "\n".join(failures)
        )

    def test_critical_classes_exist(self) -> None:
        """Key classes and functions are importable (smoke check)."""
        from src.config.models import PhaseAConfig, InputCatalog, CatalogItem
        from src.extract.llm_client import LLMClient
        from src.extract.extractor import ParameterExtractor
        from src.extract.prompts import build_extraction_prompt
        from src.excel.writer import PLWriter

        # Verify they are the right types
        assert callable(build_extraction_prompt)
        assert isinstance(PhaseAConfig, type)
        assert isinstance(LLMClient, type)

    def test_version_module(self) -> None:
        """The version module works without errors."""
        from src.app.version import version_label, APP_VERSION

        label = version_label()
        assert APP_VERSION in label
        assert "unknown" in label or len(label) > 5  # has commit info
