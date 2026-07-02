from __future__ import annotations

from datetime import datetime


def current_timestamp() -> str:
    """Return a local ISO timestamp stable enough for workbench state files."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def resolve_timestamp(value: str | None) -> str:
    if value and value.strip():
        return value.strip()
    return current_timestamp()
