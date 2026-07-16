#!/usr/bin/env python3
"""
Session helpers - map named conversation sessions to history-file paths.

A session is nothing more than a history JSON file under SESSIONS_DIR; all
persistence guarantees (0600 files, 0700 parent directory) come from
ConversationManager, which writes these files. The reserved name "default"
refers to the legacy ~/.chatsystem_history.json and never maps to a file here.
"""

import re
from pathlib import Path
from typing import List

SESSIONS_DIR = Path.home() / ".chatsystem_sessions"

DEFAULT_SESSION = "default"

_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_name(name: str) -> None:
    """Raise ValueError if `name` is not a safe session name."""
    if not name or not _NAME_RE.match(name):
        raise ValueError(
            "Session names must be 1-64 characters of letters, digits, '-' or '_'"
        )
    if name == DEFAULT_SESSION:
        raise ValueError(f"'{DEFAULT_SESSION}' is reserved for the main history file")


def session_path(name: str) -> Path:
    """Return the history-file path for a named session (validates the name)."""
    validate_name(name)
    return SESSIONS_DIR / f"{name}.json"


def list_sessions() -> List[str]:
    """Return sorted session names; empty if the sessions directory is missing."""
    if not SESSIONS_DIR.is_dir():
        return []
    return sorted(p.stem for p in SESSIONS_DIR.glob("*.json") if p.is_file())


def delete_session(name: str) -> None:
    """Delete a session's history file. Raises FileNotFoundError if absent."""
    path = session_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"No session named '{name}'")
    path.unlink()
