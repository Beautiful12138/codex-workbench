from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def find_workspace_root(payload: dict[str, Any]) -> Path | None:
    candidates: list[Path] = []
    for key in ("WORKBENCH_ROOT", "CODEX_WORKBENCH_ROOT", "CODEX_WORKSPACE"):
        value = os.environ.get(key)
        if value:
            candidates.append(Path(value))
    for key in ("cwd", "workspace_root"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            candidates.append(Path(value))
    cwd = Path.cwd()
    candidates.extend([cwd, *cwd.parents])

    for candidate in candidates:
        root = candidate.expanduser().resolve()
        if _is_workspace_root(root):
            return root
    return None


def emit_context(event_name: str, additional_context: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event_name,
                    "additionalContext": additional_context,
                }
            },
            ensure_ascii=True,
        )
    )


def session_start_context(root: Path | None) -> str:
    if root is None:
        return ""
    return "\n".join(
        [
            "Workbench: understand the request, then use workspace context; CURRENT/recovery/index are navigation aids, not truth.",
            "Do not write status for chat or read-only exploration. Open task rules/CLI before code changes, status writes, stage moves, or completion claims.",
            "Verify before cooperating: if facts or risks do not fit, say so briefly and offer a steadier path.",
        ]
    )


def user_prompt_context(root: Path | None) -> str:
    if root is None:
        return ""
    return "\n".join(
        [
            "Workbench reminder: chat and read-only exploration do not write status; open task rules/CLI before code changes, status writes, external impact, or completion claims.",
            "Verify before cooperating: the user's direction is not automatically fact; if it does not fit, say so calmly and offer a steadier path.",
            "If the user clarifies, corrects, discusses, or asks, confirm understanding first; edit assets only after clear authorization.",
            "DO NOT send optional commentary.",
        ]
    )


def _is_workspace_root(path: Path) -> bool:
    return (
        (path / "CURRENT.md").exists()
        and (path / "AGENTS.md").exists()
        and (path / "services" / "registry.yaml").exists()
    )
