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
            "Workbench: classify lightly first; chat/read-only stays status-free.",
            "Use workspace/service context for orientation; expand task/CLI/policy only for edits, status, evidence, environment, stage, completion, or real-risk ambiguity.",
            "Generated views navigate; YAML, registry, evidence, files, and command output decide facts.",
        ]
    )


def user_prompt_context(root: Path | None) -> str:
    if root is None:
        return ""
    return "\n".join(
        [
            "Workbench: chat/read-only = no status. Expand rules only for edits, state/stage, evidence, environment/external impact, completion, or risky ambiguity.",
            (
                "Confirm before asset edits unless clearly authorized. Respectful correction: when "
                "the user's premise conflicts with files, commands, YAML truth, evidence, policy, "
                "or risk boundaries, briefly present evidence and choose the steadier path."
            ),
            "DO NOT send optional commentary.",
        ]
    )


def _is_workspace_root(path: Path) -> bool:
    return (
        (path / "CURRENT.md").exists()
        and (path / "AGENTS.md").exists()
        and (path / "services" / "registry.yaml").exists()
    )
