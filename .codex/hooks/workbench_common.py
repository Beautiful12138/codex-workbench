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
            ensure_ascii=False,
        )
    )


def session_start_context(root: Path | None) -> str:
    if root is None:
        return ""
    return "\n".join(
        [
            "Workbench：优先用 workspace context 接住现场；CURRENT/recovery/index 只辅助定位，不是真源。",
            "讨论/只读探索不写状态；选中正式 task、写状态、推进阶段或声明完成时，再打开任务包和 CLI。",
            "先校验再配合：多思考一步，用户方向不自动等于事实正确。",
        ]
    )


def user_prompt_context(root: Path | None) -> str:
    if root is None:
        return ""
    return "\n".join(
        [
            "Workbench 提醒：默认讨论/聊天/只读探索不写状态；改代码、写状态、碰外部影响或声明完成前，再打开任务规则和 CLI。",
            "先校验再配合：多思考一步，用户方向不自动等于事实正确；发现事实、风险或规则冲突时，简短提醒并给出更稳路径。",
        ]
    )


def _is_workspace_root(path: Path) -> bool:
    return (
        (path / "CURRENT.md").exists()
        and (path / "AGENTS.md").exists()
        and (path / "services" / "registry.yaml").exists()
    )
