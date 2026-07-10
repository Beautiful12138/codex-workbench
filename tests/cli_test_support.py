from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from codex_workbench.cli import app


runner = CliRunner()


def create_workspace(root: Path) -> None:
    (root / "services").mkdir()
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CURRENT.md").write_text("# CURRENT\n", encoding="utf-8")
    (root / "services" / "registry.yaml").write_text(
        "schema_version: '0.1'\nservices: []\n",
        encoding="utf-8",
    )


def write_requirement(
    root: Path,
    *,
    status: str = "readable",
    confirmed_by_user: bool = True,
) -> None:
    requirement_dir = root / "docs" / "active" / "REQ-20260702-001"
    requirement_dir.mkdir(parents=True)
    payload = {
        "schema_version": "0.1",
        "id": "REQ-20260702-001",
        "title": "构建轻量 Workbench",
        "goal": "让 Codex 专注用户任务。",
        "created_at": "2026-07-01T09:00:00+08:00",
        "updated_at": "2026-07-01T09:00:00+08:00",
        "acceptance": ["可以创建任务包。"],
        "readiness": {
            "status": status,
            "confirmed_by_user": confirmed_by_user,
        },
    }
    (requirement_dir / "requirement.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def combined_output(result) -> str:
    return result.output + getattr(result, "stderr", "")


def assert_markdown_template_hint(output: str) -> None:
    hint_lines = [line for line in output.splitlines() if line.startswith("markdown_template_hint")]
    assert hint_lines


def workspace_context_section(output: str, start: str, end: str) -> str:
    start_index = output.index(start)
    end_index = output.index(end, start_index)
    return output[start_index:end_index]


def create_task_via_cli(root: Path, extra_args: list[str] | None = None):
    return runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "实现任务 CLI",
            "--user-goal",
            "创建任务包。",
            "--done",
            "task.yaml 可校验。",
            "--next",
            "运行测试。",
            "--workspace-root",
            str(root),
            "--updated-at",
            "2026-07-01",
            *(extra_args or []),
        ],
    )
