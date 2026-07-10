from __future__ import annotations

import json
import subprocess
from pathlib import Path


from codex_workbench.cli import app
from tests.cli_test_support import (
    combined_output,
    create_workspace,
    runner,
)


def test_service_add_and_list_commands_manage_registry(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)

    add_result = runner.invoke(
        app,
        [
            "service",
            "add",
            "api",
            "--path",
            str(service_path),
            "--purpose",
            "主服务",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    list_result = runner.invoke(
        app,
        ["service", "list", "--workspace-root", str(tmp_path)],
    )

    assert add_result.exit_code == 0
    assert "updated services/registry.yaml" in add_result.output
    assert list_result.exit_code == 0
    assert "service api" in list_result.output
    assert str(service_path) in list_result.output


def test_service_add_dry_run_does_not_write_registry(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)

    result = runner.invoke(
        app,
        [
            "service",
            "add",
            "api",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
            "--dry-run",
        ],
    )
    list_result = runner.invoke(
        app,
        ["service", "list", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "dry-run services/registry.yaml" in result.output
    assert "api" not in list_result.output


def test_service_update_command_changes_registry(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)
    runner.invoke(
        app,
        [
            "service",
            "add",
            "api",
            "--path",
            str(service_path),
            "--purpose",
            "旧用途",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        [
            "service",
            "update",
            "api",
            "--purpose",
            "新用途",
            "--notes",
            "新备注",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    context_result = runner.invoke(
        app,
        ["service", "context", "api", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "updated services/registry.yaml" in result.output
    assert "用途：新用途" in context_result.output
    assert "备注：新备注" in context_result.output


def test_service_delete_command_removes_registry_entry(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)
    runner.invoke(
        app,
        [
            "service",
            "add",
            "api",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        ["service", "delete", "api", "--workspace-root", str(tmp_path)],
    )
    list_result = runner.invoke(
        app,
        ["service", "list", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "updated services/registry.yaml" in result.output
    assert "api" not in list_result.output


def test_service_status_command_reports_non_git_path(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "plain"
    service_path.mkdir(parents=True)
    runner.invoke(
        app,
        [
            "service",
            "add",
            "plain",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        ["service", "status", "plain", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert f"plain path={service_path}" in result.output
    assert "exists=True git_state=not_git" in result.output


def test_service_context_command_reports_entry_gaps(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "plain"
    service_path.mkdir(parents=True)
    runner.invoke(
        app,
        [
            "service",
            "add",
            "plain",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        ["service", "context", "plain", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "服务：plain" in result.output
    assert f"路径：{service_path}" in result.output
    assert "状态：empty_dir | Git：not_git | 可见文件：0" in result.output
    assert "入口候选：none" in result.output
    assert "阻断：empty_service_dir" in result.output
    assert "提醒：not_git,no_entry_candidates" in result.output
    assert "gaps=" not in result.output


def test_service_context_command_reports_git_scope_and_existing_changes(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "web"
    service_path.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=service_path, check=True, capture_output=True, text=True)
    (service_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    runner.invoke(
        app,
        [
            "service",
            "add",
            "web",
            "--path",
            str(service_path),
            "--purpose",
            "前端服务。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        ["service", "context", "web", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "服务：web" in result.output
    assert "用途：前端服务。" in result.output
    assert "状态：non_empty_dir | Git：git | 可见文件：1" in result.output
    assert "入口候选：package.json" in result.output
    assert "Git 范围：git_status=service_path,service_relpath=." in result.output
    assert "已有变更：dirty=0 untracked=1" in result.output
    assert "阻断：" not in result.output


def test_service_context_command_can_emit_json_for_task_context(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "web"
    service_path.mkdir(parents=True)
    (service_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    (service_path / "src").mkdir()
    runner.invoke(
        app,
        [
            "service",
            "add",
            "web",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        ["service", "context", "web", "--format", "json", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["name"] == "web"
    assert payload["path_state"] == "non_empty_dir"
    assert payload["resolved_path"] == str(service_path)
    assert "package.json" in payload["entry_candidates"]
    assert "src/" in payload["entry_candidates"]
    assert "no_entry_candidates" not in payload["gaps"]
    assert payload["hard_gaps"] == []
    assert payload["warnings"] == ["not_git"]


def test_service_context_command_rejects_unknown_service(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        ["service", "context", "missing-service", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert "unknown_service: missing-service" in combined_output(result)
