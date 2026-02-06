"""Runtime version info -- displayed in the Streamlit sidebar.

The git commit hash is resolved at import time so we always know
exactly which code is running on Streamlit Cloud.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_git_commit() -> str:
    """Return the short git commit hash, or 'unknown' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_git_branch() -> str:
    """Return the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


APP_VERSION = "0.1.0"


def version_label() -> str:
    """Return a human-readable version string like 'v0.1.0 (abc1234 @ main)'."""
    commit = get_git_commit()
    branch = get_git_branch()
    return f"v{APP_VERSION} ({commit} @ {branch})"
