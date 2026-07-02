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
            "Workbench：从 CURRENT.md 入口卡开始；按用户请求、generated 视图、CLI 参数或包路径选择工作对象。",
            "状态变更优先用 CLI；generated 视图只是索引，不能覆盖包 YAML 真源。",
            "讨论/只读探索不写状态；改文件前先打开被选中的任务包。",
        ]
    )


def user_prompt_context(root: Path | None) -> str:
    if root is None:
        return ""
    return "\n".join(
        [
            "Workbench 提醒：讨论和只读探索不写状态；要纳入任务时等用户明确说。",
            "状态变更用 CLI 写包 YAML；无 evidence/handoff 不标 done。",
            "范围、验收、服务关系、公开契约、数据模型或确认口径变化时先暂停。",
        ]
    )


def _is_workspace_root(path: Path) -> bool:
    return (
        (path / "CURRENT.md").exists()
        and (path / "AGENTS.md").exists()
        and (path / "services" / "registry.yaml").exists()
    )
