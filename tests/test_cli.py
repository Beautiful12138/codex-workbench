from __future__ import annotations

import importlib
import json
import os
import pkgutil
import subprocess
import sys
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


def _workspace_context_section(output: str, start: str, end: str) -> str:
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


def test_version_command_prints_package_name() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.output.strip() == "codex-workbench 1.0.0"


def test_cli_entrypoint_is_thin_and_registers_command_modules() -> None:
    cli_path = Path(__file__).resolve().parents[1] / "src" / "codex_workbench" / "cli.py"
    assert len(cli_path.read_text(encoding="utf-8").splitlines()) <= 220

    command_package = importlib.import_module("codex_workbench.cli_commands")
    discovered_modules = {
        module.name
        for module in pkgutil.iter_modules(command_package.__path__)
        if not module.name.startswith("_")
    }
    assert {
        "archive",
        "common",
        "evidence",
        "index_doctor",
        "materials",
        "records",
        "requirement_task",
        "reusable",
        "schema_workspace",
        "services",
    }.issubset(discovered_modules)

    registered_groups = {group.name for group in app.registered_groups}
    assert {
        "schema",
        "workspace",
        "requirement",
        "task",
        "service",
        "material",
        "discovery",
        "intake",
        "evidence",
        "validation",
        "handoff",
        "action",
        "change",
        "decision",
        "suspicion",
        "index",
        "doctor",
        "archive",
        "reusable-memory",
    }.issubset(registered_groups)


def test_schema_list_command_lists_core_models() -> None:
    result = runner.invoke(app, ["schema", "list"])

    assert result.exit_code == 0
    assert "TaskState" in result.output
    assert "WorkspaceState" in result.output
    assert "ChangeRecordState" in result.output
    assert "SuspicionState" in result.output


def test_workspace_context_reports_baseline_without_generating_views(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    current_path = tmp_path / "CURRENT.md"
    before_current = current_path.read_text(encoding="utf-8")

    result = runner.invoke(app, ["workspace", "context", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "# Workspace Context" in result.output
    assert "不是状态真源；任务事实以 task context、任务包和命令输出为准" in result.output
    assert "工作区状态：baseline" in result.output
    assert "活动任务：none" in result.output
    assert "推荐入口：chat_or_explore" in result.output
    assert "状态写入：默认不写；需要写状态时必须有明确场景和授权，并且只能走 CLI" in result.output
    assert "不生成文件；需要刷新视图时再运行 index generate" in result.output
    assert current_path.read_text(encoding="utf-8") == before_current
    assert not (tmp_path / "docs" / "generated" / "index.md").exists()
    assert not (tmp_path / "docs" / "generated" / "recovery.md").exists()


def test_workspace_context_can_embed_task_context_by_title(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    service_path = tmp_path / "repos" / "web"
    service_path.mkdir(parents=True)
    (service_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    runner.invoke(
        app,
        [
            "service",
            "add",
            "web-dashboard",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )
    create_task_via_cli(tmp_path, ["--service-ref", "web-dashboard"])

    result = runner.invoke(
        app,
        ["workspace", "context", "--task", "实现任务 CLI", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "# Workspace Context" in result.output
    assert "工作区状态：active" in result.output
    assert "活动任务：1" in result.output
    assert "状态写入：默认不写；需要写状态时必须有明确场景和授权，并且只能走 CLI" in result.output
    assert "- 实现任务 CLI [draft]：运行测试。" in result.output
    assert "## 当前任务" in result.output
    assert "当前任务：实现任务 CLI" in result.output
    assert "服务现场" in result.output
    assert f"路径：{service_path}" in result.output
    assert "REQ-20260702-001-TASK" not in result.output


def test_workspace_context_can_embed_service_context(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "web"
    service_path.mkdir(parents=True)
    (service_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    runner.invoke(
        app,
        [
            "service",
            "add",
            "web-dashboard",
            "--path",
            str(service_path),
            "--purpose",
            "前端服务。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    current_path = tmp_path / "CURRENT.md"
    index_path = tmp_path / "docs" / "generated" / "index.md"
    recovery_path = tmp_path / "docs" / "generated" / "recovery.md"
    before_current = current_path.read_text(encoding="utf-8")
    before_index = index_path.read_text(encoding="utf-8")
    before_recovery = recovery_path.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        ["workspace", "context", "--service", "web-dashboard", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "## 当前服务" in result.output
    assert "服务：web-dashboard" in result.output
    assert "用途：前端服务。" in result.output
    assert f"路径：{service_path}" in result.output
    assert "入口候选：package.json" in result.output
    assert current_path.read_text(encoding="utf-8") == before_current
    assert index_path.read_text(encoding="utf-8") == before_index
    assert recovery_path.read_text(encoding="utf-8") == before_recovery


def test_workspace_context_lists_lightweight_service_overview(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "web"
    service_path.mkdir(parents=True)
    (service_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    runner.invoke(
        app,
        [
            "service",
            "add",
            "web-dashboard",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["workspace", "context", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "## 服务概览" in result.output
    assert "- web-dashboard：registry_only | 路径：" in result.output
    assert "任务引用：0" in result.output
    assert "深入：`workspace context --service web-dashboard` 或 `service context web-dashboard`" in result.output
    assert "non_empty_dir" not in result.output
    assert "入口：package.json" not in result.output
    assert "## 当前服务" not in result.output
    assert f"路径：{service_path}" not in result.output


def test_workspace_context_deduplicates_service_refs_from_many_tasks(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    service_path = tmp_path / "repos" / "web"
    service_path.mkdir(parents=True)
    runner.invoke(
        app,
        [
            "service",
            "add",
            "web-dashboard",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )
    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml"
    requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    task_ids = [f"REQ-20260702-001-TASK-20260702-{index:03d}" for index in range(1, 6)]
    requirement["task_refs"] = task_ids
    requirement_yaml.write_text(yaml.safe_dump(requirement, allow_unicode=True, sort_keys=False), encoding="utf-8")
    for index, task_id in enumerate(task_ids, start=1):
        task_dir = tmp_path / "docs" / "active" / task_id
        task_dir.mkdir(parents=True)
        (task_dir / "task.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": "0.1",
                    "id": task_id,
                    "requirement_id": "REQ-20260702-001",
                    "title": f"任务 {index}",
                    "created_at": "2026-07-01T09:00:00+08:00",
                    "updated_at": f"2026-07-01T1{index}:00:00+08:00",
                    "stage": "in_progress",
                    "next_step": "继续。",
                    "service_refs": ["web-dashboard", "web-dashboard"],
                    "validation": {"status": "not_started"},
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

    result = runner.invoke(app, ["workspace", "context", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert result.output.count("- web-dashboard：") == 1
    assert "任务引用：5" in result.output


def test_workspace_context_prioritizes_unknown_active_service_refs(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    for index in range(1, 7):
        service_path = tmp_path / "repos" / f"service-{index}"
        service_path.mkdir(parents=True)
        runner.invoke(
            app,
            [
                "service",
                "add",
                f"service-{index}",
                "--path",
                str(service_path),
                "--workspace-root",
                str(tmp_path),
            ],
        )
    task_dir = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001"
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "REQ-20260702-001-TASK-20260702-001",
                "requirement_id": "REQ-20260702-001",
                "title": "调用缺失服务",
                "created_at": "2026-07-01T09:00:00+08:00",
                "updated_at": "2026-07-01T10:00:00+08:00",
                "stage": "in_progress",
                "next_step": "确认服务登记。",
                "service_refs": ["missing-active-service"],
                "validation": {"status": "not_started"},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["workspace", "context", "--workspace-root", str(tmp_path)])
    checked_result = runner.invoke(
        app,
        ["workspace", "context", "--check-services", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert checked_result.exit_code == 0
    service_overview = _workspace_context_section(result.output, "## 服务概览", "## 任务焦点")
    checked_service_overview = _workspace_context_section(checked_result.output, "## 服务概览", "## 任务焦点")
    assert "- missing-active-service：missing_registry | 任务引用：1 | 阻断：unknown_service_ref" in service_overview
    assert "- missing-active-service：missing_registry | 任务引用：1 | 阻断：unknown_service_ref" in checked_service_overview


def test_workspace_context_can_opt_into_service_checks(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "web"
    service_path.mkdir(parents=True)
    (service_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    runner.invoke(
        app,
        [
            "service",
            "add",
            "web-dashboard",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["workspace", "context", "--check-services", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "## 服务概览" in result.output
    assert "- web-dashboard：non_empty_dir | Git：not_git | 入口：package.json | 任务引用：0 | 提醒：not_git" in result.output


def test_workspace_context_groups_waiting_feedback_without_treating_it_as_blocked(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml"
    requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    task_ids = [
        "REQ-20260702-001-TASK-20260702-001",
        "REQ-20260702-001-TASK-20260702-002",
        "REQ-20260702-001-TASK-20260702-003",
        "REQ-20260702-001-TASK-20260702-004",
    ]
    requirement["task_refs"] = task_ids
    requirement_yaml.write_text(yaml.safe_dump(requirement, allow_unicode=True, sort_keys=False), encoding="utf-8")
    task_payloads = [
        {
            "id": task_ids[0],
            "title": "继续实现入口",
            "stage": "in_progress",
            "next_step": "补充服务概览。",
            "updated_at": "2026-07-01T12:00:00+08:00",
        },
        {
            "id": task_ids[1],
            "title": "发布到测试环境",
            "stage": "verification_pending",
            "next_step": "等待用户测试。",
            "handoff": {"status": "waiting_user_validation", "note": "已交给用户测试。"},
            "updated_at": "2026-07-01T11:00:00+08:00",
        },
        {
            "id": task_ids[2],
            "title": "接入 GitLab webhook",
            "stage": "blocked",
            "next_step": "等待回调地址。",
            "blocked": {
                "reason": "缺少回调地址。",
                "blocked_by": "user",
                "resume_condition": "用户提供回调地址。",
                "resume_stage": "ready",
            },
            "updated_at": "2026-07-01T10:00:00+08:00",
        },
        {
            "id": task_ids[3],
            "title": "草稿整理",
            "stage": "draft",
            "next_step": "确认是否纳入正式任务。",
            "updated_at": "2026-07-01T09:00:00+08:00",
        },
    ]
    for payload in task_payloads:
        payload = {
            "schema_version": "0.1",
            "requirement_id": "REQ-20260702-001",
            "created_at": payload["updated_at"],
            "validation": {"status": "not_started"},
            **payload,
        }
        task_yaml = tmp_path / "docs" / "active" / payload["id"] / "task.yaml"
        task_yaml.parent.mkdir(parents=True)
        task_yaml.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = runner.invoke(app, ["workspace", "context", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "## 任务焦点" in result.output
    assert "可续接：" in result.output
    assert "- 继续实现入口 [in_progress]：补充服务概览。" in result.output
    assert "等待反馈：" in result.output
    assert "- 发布到测试环境 [verification_pending]：等待用户测试。" in result.output
    assert "阻塞：" in result.output
    assert "- 接入 GitLab webhook [blocked]：缺少回调地址。" in result.output
    assert "需确认：" in result.output
    assert "草稿整理 [draft]" not in _workspace_context_section(result.output, "等待反馈：", "阻塞：")
    assert "草稿整理 [draft]" not in _workspace_context_section(result.output, "需确认：", "## 冲突")
    assert "REQ-20260702-001-TASK" not in result.output


def test_workspace_context_subprocess_works_with_documented_pythonpath(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    project_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-m", "codex_workbench", "workspace", "context", "--workspace-root", str(tmp_path)],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "# Workspace Context" in completed.stdout
    assert "工作区状态：baseline" in completed.stdout


def test_index_generate_command_writes_views_and_check_detects_stale(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "实现 index",
            "--user-goal",
            "生成恢复视图。",
            "--done",
            "index 可重建。",
            "--next",
            "运行生成命令。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    generate = runner.invoke(
        app,
        [
            "index",
            "generate",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    clean = runner.invoke(
        app,
        [
            "index",
            "generate",
            "--check",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    (tmp_path / "docs" / "generated" / "index.md").write_text("stale\n", encoding="utf-8")
    stale = runner.invoke(
        app,
        [
            "index",
            "check",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert generate.exit_code == 0
    assert "generated docs/generated/index.md" in generate.output
    assert "generated docs/generated/recovery.md" in generate.output
    assert clean.exit_code == 0
    assert "index clean" in clean.output
    assert stale.exit_code != 0
    assert "stale: docs/generated/index.md" in combined_output(stale)


def test_index_generate_dry_run_does_not_write_views(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = runner.invoke(
        app,
        [
            "index",
            "generate",
            "--workspace-root",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run docs/generated/index.md" in result.output
    assert "REQ-20260702-001" in result.output
    assert not (tmp_path / "docs" / "generated" / "index.md").exists()
    assert not (tmp_path / "docs" / "generated" / "recovery.md").exists()


def test_index_cli_reports_conflicts(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    task_dir = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001"
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "REQ-20260702-001-TASK-20260702-001",
                "requirement_id": "REQ-20260702-001",
                "title": "冲突任务",
                "stage": "in_progress",
                "process_level": "standard",
                "risk_level": "standard",
                "service_refs": ["missing-service"],
                "validation": {"status": "not_started"},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    generate = runner.invoke(
        app,
        [
            "index",
            "generate",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    check = runner.invoke(
        app,
        [
            "index",
            "check",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert generate.exit_code == 0
    assert "conflict: unknown_service_ref: REQ-20260702-001-TASK-20260702-001 -> missing-service" in combined_output(generate)
    assert check.exit_code != 0
    assert "conflict: unknown_service_ref: REQ-20260702-001-TASK-20260702-001 -> missing-service" in combined_output(check)


def test_index_cli_reports_bad_yaml(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    broken = tmp_path / "docs" / "actions" / "BROKEN.yaml"
    broken.parent.mkdir(parents=True)
    broken.write_text("id: [broken\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "index",
            "check",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "conflict: invalid_yaml: docs/actions/BROKEN.yaml" in combined_output(result)


def test_workspace_root_command_discovers_from_nested_path(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    nested = tmp_path / "docs" / "tasks"
    nested.mkdir(parents=True)

    result = runner.invoke(app, ["workspace", "root", "--start", str(nested)])

    assert result.exit_code == 0
    assert Path(result.output.strip()) == tmp_path


def test_workspace_root_command_reports_missing_workspace(tmp_path: Path) -> None:
    result = runner.invoke(app, ["workspace", "root", "--start", str(tmp_path)])

    assert result.exit_code != 0
    assert "workspace_not_found" in combined_output(result)


def test_requirement_create_command_writes_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "requirement",
            "create",
            "REQ-20260702-001",
            "--title",
            "构建轻量 Workbench",
            "--goal",
            "让 Codex 专注用户任务。",
            "--acceptance",
            "可以创建任务包。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code == 0
    assert "created docs/active/REQ-20260702-001/requirement.yaml" in result.output
    assert_markdown_template_hint(result.output)
    assert (tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml").exists()


def test_requirement_create_can_auto_id_and_default_time(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    monkeypatch.setattr(
        "codex_workbench.timeutils.current_timestamp",
        lambda: "2026-07-02T10:30:00+08:00",
    )

    result = runner.invoke(
        app,
        [
            "requirement",
            "create",
            "--title",
            "自动编号需求",
            "--goal",
            "省略 ID 和更新时间也能创建需求。",
            "--acceptance",
            "生成下一个当天需求 ID。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-002" / "requirement.yaml"
    assert result.exit_code == 0, combined_output(result)
    assert "created docs/active/REQ-20260702-002/requirement.yaml" in result.output
    requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    assert requirement["id"] == "REQ-20260702-002"
    assert requirement["created_at"] == "2026-07-02T10:30:00+08:00"
    assert requirement["updated_at"] == "2026-07-02T10:30:00+08:00"


def test_task_create_command_writes_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = runner.invoke(
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
            "--service-ref",
            "codex-workbench",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code == 0
    assert "created docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in result.output
    assert "updated docs/active/REQ-20260702-001/requirement.yaml" in result.output
    assert_markdown_template_hint(result.output)
    task_yaml = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text(
            encoding="utf-8"
        )
    )
    task_md = (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.md").read_text(
        encoding="utf-8"
    )
    assert task_yaml["next_step"] == "运行测试。"
    assert task_yaml["service_refs"] == ["codex-workbench"]
    assert "创建任务包。" not in task_md
    assert "运行测试。" not in task_md


def test_task_create_writes_impact_profile(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "调整本地 SQL",
            "--user-goal",
            "调整本地测试 SQL。",
            "--done",
            "本地测试通过。",
            "--next",
            "准备实现。",
            "--impact-action",
            "code_change",
            "--impact-component",
            "sql",
            "--impact-component",
            "database",
            "--impact-environment",
            "local",
            "--impact-data-effect",
            "none",
            "--impact-external-effect",
            "none",
            "--impact-blast-radius",
            "single_service",
            "--impact-reversibility",
            "git_revert",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "local_testable",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    task_yaml = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert result.exit_code == 0, combined_output(result)
    assert task_yaml["impact_profile"]["action"] == "code_change"
    assert task_yaml["impact_profile"]["component_signals"] == ["sql", "database"]
    assert task_yaml["impact_profile"]["contract_change"] is False
    assert task_yaml["impact_profile"]["verification_confidence"] == "local_testable"


def test_task_create_accepts_test_impact_environment(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = create_task_via_cli(
        tmp_path,
        [
            "--impact-action",
            "code_change",
            "--impact-component",
            "frontend",
            "--impact-environment",
            "test",
            "--impact-data-effect",
            "none",
            "--impact-external-effect",
            "none",
            "--impact-blast-radius",
            "single_service",
            "--impact-reversibility",
            "git_revert",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "local_testable",
        ],
    )

    assert result.exit_code == 0, combined_output(result)
    task_yaml = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert task_yaml["impact_profile"]["environment"] == "test"


def test_task_impact_set_updates_profile_and_records_reason(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    created = create_task_via_cli(tmp_path)
    assert created.exit_code == 0, combined_output(created)

    result = runner.invoke(
        app,
        [
            "task",
            "impact-set",
            "REQ-20260702-001-TASK-20260702-001",
            "--risk-level",
            "standard",
            "--process-level",
            "lightweight",
            "--impact-action",
            "code_change",
            "--impact-component",
            "sql",
            "--impact-environment",
            "local",
            "--impact-data-effect",
            "none",
            "--impact-external-effect",
            "none",
            "--impact-blast-radius",
            "single_service",
            "--impact-reversibility",
            "git_revert",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "local_testable",
            "--risk-trigger",
            "发现真实数据写入时暂停确认。",
            "--reason",
            "读代码后确认只是本地 SQL 查询调整。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    current_text = (tmp_path / "CURRENT.md").read_text(encoding="utf-8")
    index_text = (tmp_path / "docs" / "generated" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, combined_output(result)
    assert task["risk_level"] == "standard"
    assert task["process_level"] == "lightweight"
    assert task["impact_profile"]["action"] == "code_change"
    assert task["impact_profile"]["component_signals"] == ["sql"]
    assert task["risk_triggers"] == ["发现真实数据写入时暂停确认。"]
    assert task["risk_assessment_notes"] == ["读代码后确认只是本地 SQL 查询调整。"]
    assert "实现任务 CLI" in current_text
    assert "standard/lightweight" not in current_text
    assert "code_change local data=none" not in current_text
    assert "standard/lightweight" in index_text
    assert "code_change local data=none" in index_text


def test_task_impact_set_requires_reason(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    created = create_task_via_cli(tmp_path)
    assert created.exit_code == 0, combined_output(created)

    result = runner.invoke(
        app,
        [
            "task",
            "impact-set",
            "REQ-20260702-001-TASK-20260702-001",
            "--risk-level",
            "standard",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "missing_risk_assessment_reason" in combined_output(result)


def test_task_check_blocks_low_micro_real_data_write_profile(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    created = create_task_via_cli(
        tmp_path,
        [
            "--impact-action",
            "data_write",
            "--impact-component",
            "sql",
            "--impact-environment",
            "shared",
            "--impact-data-effect",
            "real_data_write",
            "--impact-external-effect",
            "write",
            "--impact-blast-radius",
            "shared_users",
            "--impact-reversibility",
            "hard",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "integration_required",
        ],
    )
    assert created.exit_code == 0, combined_output(created)
    prepared = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/demo.py",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    assert prepared.exit_code == 0, combined_output(prepared)

    check = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert check.exit_code != 0
    output = combined_output(check)
    assert "impact_profile_requires_risk_escalation" in output
    assert "impact_profile_requires_process_escalation" in output


def test_task_create_can_auto_id_and_default_time(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    existing = create_task_via_cli(tmp_path)
    assert existing.exit_code == 0, combined_output(existing)
    monkeypatch.setattr(
        "codex_workbench.timeutils.current_timestamp",
        lambda: "2026-07-02T10:45:00+08:00",
    )

    result = runner.invoke(
        app,
        [
            "task",
            "create",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "自动编号任务",
            "--user-goal",
            "省略 task ID 和更新时间也能创建任务。",
            "--done",
            "生成所属需求下的下一个当天任务 ID。",
            "--next",
            "继续准备任务。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task_id = "REQ-20260702-001-TASK-20260702-002"
    task_yaml = tmp_path / "docs" / "active" / task_id / "task.yaml"
    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml"
    assert result.exit_code == 0, combined_output(result)
    assert f"created docs/active/{task_id}/task.yaml" in result.output
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    assert task["id"] == task_id
    assert task["created_at"] == "2026-07-02T10:45:00+08:00"
    assert task["updated_at"] == "2026-07-02T10:45:00+08:00"
    assert requirement["task_refs"] == [
        "REQ-20260702-001-TASK-20260702-001",
        task_id,
    ]


def test_task_create_refreshes_current_index_and_recovery(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = create_task_via_cli(tmp_path)

    assert result.exit_code == 0, combined_output(result)
    current_text = (tmp_path / "CURRENT.md").read_text(encoding="utf-8")
    index_text = (tmp_path / "docs" / "generated" / "index.md").read_text(encoding="utf-8")
    recovery_text = (tmp_path / "docs" / "generated" / "recovery.md").read_text(encoding="utf-8")
    assert "REQ-20260702-001-TASK-20260702-001" in current_text
    assert "REQ-20260702-001-TASK-20260702-001" in index_text
    assert "REQ-20260702-001-TASK-20260702-001" in recovery_text


def test_task_create_dry_run_does_not_write_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)

    result = runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in result.output
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001").exists()


def test_task_create_rejects_done_stage(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
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
            "--stage",
            "done",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "final_stage_not_allowed" in combined_output(result)


def test_task_create_rejects_missing_requirement_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "missing_requirement_package: REQ-20260702-001" in combined_output(result)
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001").exists()


def test_task_create_rejects_unconfirmed_requirement_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path, status="intake_draft", confirmed_by_user=False)

    result = runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    output = combined_output(result)
    assert "requirement_not_readable" in output
    assert "missing_user_confirmation" in output
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001").exists()


def test_task_create_rejects_guarded_initial_stage(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
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
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "initial_stage_not_allowed" in combined_output(result)


def test_task_update_packet_preserves_body(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "task",
            "update-packet",
            "REQ-20260702-001-TASK-20260702-001",
            "--next",
            "继续实现 CLI。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "updated docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in result.output
    task_yaml = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text(
            encoding="utf-8"
        )
    )
    task_text = (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.md").read_text(encoding="utf-8")
    assert task_yaml["next_step"] == "继续实现 CLI。"
    assert "## 用户目标" in task_text
    assert "## Current Packet" not in task_text


def test_task_update_packet_rejects_missing_next_step(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "task",
            "update-packet",
            "REQ-20260702-001-TASK-20260702-001",
            "--next",
            " ",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "missing_next_step" in combined_output(result)


def test_task_set_stage_rejects_done_without_evidence(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "done",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "stage_transition_blocked" in combined_output(result)


def test_task_prepare_command_allows_in_progress_without_handwritten_yaml(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)

    before_prepare = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--implementation-ref",
            "implementation.md",
            "--likely-touchpoint",
            "src/codex_workbench/packages.py",
            "--risk-trigger",
            "触发真实数据写入时暂停确认。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    in_progress = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert before_prepare.exit_code != 0
    assert "missing_implementation_ready" in combined_output(before_prepare)
    assert prepare.exit_code == 0
    assert "updated docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in prepare.output
    assert in_progress.exit_code == 0
    assert task["stage"] == "in_progress"
    assert task["implementation"]["ready"] is True
    assert task["implementation"]["conclusion"] == "scoped"
    assert task["working_scope"] == ["src/codex_workbench/cli.py"]
    assert task["risk_triggers"] == ["触发真实数据写入时暂停确认。"]


def test_task_prepare_can_update_impact_profile(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    created = create_task_via_cli(tmp_path)
    assert created.exit_code == 0, combined_output(created)

    prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--risk-level",
            "standard",
            "--process-level",
            "standard",
            "--impact-action",
            "code_change",
            "--impact-component",
            "config",
            "--impact-environment",
            "local",
            "--impact-data-effect",
            "none",
            "--impact-external-effect",
            "none",
            "--impact-blast-radius",
            "single_service",
            "--impact-reversibility",
            "git_revert",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "local_testable",
            "--impact-reason",
            "准备实现时确认只影响本地配置。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task_yaml = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert prepare.exit_code == 0, combined_output(prepare)
    assert task_yaml["risk_level"] == "standard"
    assert task_yaml["process_level"] == "standard"
    assert task_yaml["impact_profile"]["component_signals"] == ["config"]
    assert task_yaml["risk_assessment_notes"] == ["准备实现时确认只影响本地配置。"]


def test_task_prepare_merges_partial_impact_profile_update(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    created = create_task_via_cli(
        tmp_path,
        [
            "--impact-action",
            "analysis",
            "--impact-component",
            "api",
            "--impact-environment",
            "test",
            "--impact-data-effect",
            "read_only",
            "--impact-external-effect",
            "read_only",
            "--impact-blast-radius",
            "single_service",
            "--impact-reversibility",
            "easy_manual",
            "--impact-contract-change",
            "unknown",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "integration_required",
        ],
    )
    assert created.exit_code == 0, combined_output(created)

    prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "projects/customer-api",
            "--impact-contract-change",
            "false",
            "--impact-reason",
            "准备实现时确认不改变接口契约。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task_yaml = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert prepare.exit_code == 0, combined_output(prepare)
    assert task_yaml["impact_profile"] == {
        "action": "analysis",
        "component_signals": ["api"],
        "environment": "test",
        "data_effect": "read_only",
        "external_effect": "read_only",
        "blast_radius": "single_service",
        "reversibility": "easy_manual",
        "contract_change": False,
        "security_or_permission": False,
        "verification_confidence": "integration_required",
    }
    assert task_yaml["risk_assessment_notes"] == ["准备实现时确认不改变接口契约。"]


def test_task_review_and_implementation_create_use_package_local_docs(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)

    review = runner.invoke(
        app,
        [
            "task",
            "review-create",
            "REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    implementation = runner.invoke(
        app,
        [
            "task",
            "implementation-create",
            "REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))

    assert review.exit_code == 0
    assert implementation.exit_code == 0
    assert "updated docs/active/REQ-20260702-001-TASK-20260702-001/review.md" in review.output
    assert "updated docs/active/REQ-20260702-001-TASK-20260702-001/implementation.md" in implementation.output
    assert_markdown_template_hint(review.output)
    assert_markdown_template_hint(implementation.output)
    assert task["review"] == {"status": "pending", "ref": "review.md"}
    assert task["implementation"]["ref"] == "implementation.md"
    review_text = (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "review.md"
    ).read_text(encoding="utf-8")
    implementation_text = (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "implementation.md"
    ).read_text(encoding="utf-8")
    assert review_text.startswith("# REQ-20260702-001-TASK-20260702-001 评审\n")
    assert "## 风险与暂停点" in review_text
    assert implementation_text.startswith("# REQ-20260702-001-TASK-20260702-001 实现说明\n")
    assert "## 验证计划" in implementation_text


def test_task_check_previews_stage_guard_without_writing(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    before_check = task_yaml.read_text(encoding="utf-8")

    blocked = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    assert blocked.exit_code == 1
    assert "task check blocked REQ-20260702-001-TASK-20260702-001 -> in_progress" in blocked.output
    assert "missing_implementation_ready" in blocked.output
    assert task_yaml.read_text(encoding="utf-8") == before_check

    prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    allowed = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert prepare.exit_code == 0
    assert allowed.exit_code == 0
    assert "task check allowed REQ-20260702-001-TASK-20260702-001 -> in_progress" in allowed.output
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    assert task["stage"] == "draft"


def test_task_prepare_high_risk_requires_review_ref_and_risk_acceptance(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path, ["--risk-level", "high"])

    minimal_prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    blocked = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    review_only_prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--implementation-ref",
            "implementation.md",
            "--review-ref",
            "review.md",
            "--risk-acceptance-note",
            "用户确认高风险边界。",
            "--risk-trigger",
            "触发真实数据写入时暂停确认。",
            "--risk-level",
            "high",
            "--process-level",
            "high",
            "--impact-action",
            "data_write",
            "--impact-environment",
            "shared",
            "--impact-data-effect",
            "real_data_write",
            "--impact-external-effect",
            "write",
            "--impact-blast-radius",
            "shared_users",
            "--impact-reversibility",
            "backup_restore",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "integration_required",
            "--impact-reason",
            "高风险任务开工前补齐影响面画像。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    blocked_without_independent_review = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    full_prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--implementation-ref",
            "implementation.md",
            "--review-ref",
            "review.md",
            "--reviewer",
            "subagent",
            "--review-independent",
            "--risk-acceptance-note",
            "用户确认高风险边界。",
            "--risk-trigger",
            "触发真实数据写入时暂停确认。",
            "--risk-level",
            "high",
            "--process-level",
            "high",
            "--impact-action",
            "data_write",
            "--impact-environment",
            "shared",
            "--impact-data-effect",
            "real_data_write",
            "--impact-external-effect",
            "write",
            "--impact-blast-radius",
            "shared_users",
            "--impact-reversibility",
            "backup_restore",
            "--impact-contract-change",
            "false",
            "--impact-security-or-permission",
            "false",
            "--impact-verification-confidence",
            "integration_required",
            "--impact-reason",
            "高风险任务开工前补齐影响面画像。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    allowed = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert minimal_prepare.exit_code == 0
    assert blocked.exit_code != 0
    output = combined_output(blocked)
    assert "missing_high_risk_review" in output
    assert "missing_high_risk_implementation_ref" in output
    assert "missing_high_risk_triggers" in output
    assert "missing_high_risk_acceptance" in output
    assert review_only_prepare.exit_code == 0
    review_only_output = combined_output(blocked_without_independent_review)
    assert blocked_without_independent_review.exit_code != 0
    assert "missing_high_risk_review_reviewer" in review_only_output
    assert "missing_high_risk_independent_review" in review_only_output
    assert full_prepare.exit_code == 0
    assert allowed.exit_code == 0


def test_high_risk_in_progress_requires_impact_profile_even_when_other_facts_exist(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path, ["--risk-level", "high"])
    prepare = runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--implementation-ref",
            "implementation.md",
            "--review-ref",
            "review.md",
            "--reviewer",
            "subagent",
            "--review-independent",
            "--risk-acceptance-note",
            "用户确认高风险边界。",
            "--risk-trigger",
            "触发真实数据写入时暂停确认。",
            "--risk-level",
            "high",
            "--process-level",
            "high",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    blocked = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert prepare.exit_code == 0
    output = combined_output(blocked)
    assert blocked.exit_code != 0
    assert "missing_high_risk_impact_profile" in output
    assert "missing_high_risk_review" not in output
    assert "missing_high_risk_review_reviewer" not in output
    assert "missing_high_risk_independent_review" not in output
    assert "missing_high_risk_implementation_ref" not in output
    assert "missing_high_risk_triggers" not in output
    assert "missing_high_risk_acceptance" not in output


def test_task_set_stage_in_progress_rejects_unknown_service_ref(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path, ["--service-ref", "missing-service"])
    runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "unknown_service_ref: missing-service" in combined_output(result)


def test_task_check_reports_unknown_service_ref_without_writing(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path, ["--service-ref", "missing-service"])
    runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "src/codex_workbench/cli.py",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    before_check = task_yaml.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "unknown_service_ref: missing-service" in result.output
    assert task_yaml.read_text(encoding="utf-8") == before_check


def test_task_check_aggregates_lifecycle_and_service_ref_reasons(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path, ["--service-ref", "missing-service"])

    result = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "missing_implementation_ready" in result.output
    assert "unknown_service_ref: missing-service" in result.output


def test_task_check_done_reports_missing_evidence_record_without_writing(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    task["validation"] = {"status": "passed", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001"}
    task["handoff"] = {"status": "accepted", "note": "用户验收通过。"}
    task_yaml.write_text(yaml.safe_dump(task, sort_keys=False, allow_unicode=True), encoding="utf-8")
    before_check = task_yaml.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "task",
            "check",
            "REQ-20260702-001-TASK-20260702-001",
            "--to",
            "done",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "missing_evidence_record: EV-REQ-20260702-001-TASK-20260702-001" in result.output
    assert task_yaml.read_text(encoding="utf-8") == before_check


def test_task_block_command_records_resume_condition(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)

    result = runner.invoke(
        app,
        [
            "task",
            "block",
            "REQ-20260702-001-TASK-20260702-001",
            "--reason",
            "等待用户确认验收。",
            "--blocked-by",
            "user",
            "--resume-condition",
            "用户补充验收口径。",
            "--resume-stage",
            "ready",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert result.exit_code == 0
    assert task["stage"] == "blocked"
    assert task["blocked"]["blocked_by"] == "user"
    assert task["blocked"]["resume_condition"] == "用户补充验收口径。"


def test_task_set_stage_rejects_obsolete_without_obsolete_workflow(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "obsolete",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "missing_obsolete_reason" in combined_output(result)


def test_task_obsolete_command_sets_stage_with_reason(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)

    result = runner.invoke(
        app,
        [
            "task",
            "obsolete",
            "REQ-20260702-001-TASK-20260702-001",
            "--reason",
            "误建任务，降级为废弃。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert result.exit_code == 0
    assert task["stage"] == "obsolete"
    assert task["obsolete_reason"] == "误建任务，降级为废弃。"


def test_evidence_validation_handoff_commands_allow_done(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    evidence_result = runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    validation_result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    handoff_result = runner.invoke(
        app,
        [
            "handoff",
            "set",
            "REQ-20260702-001-TASK-20260702-001",
            "--status",
            "accepted",
            "--note",
            "用户本地验收通过。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    done_result = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "done",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    task = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text("utf-8")
    )
    assert evidence_result.exit_code == 0
    assert "created docs/active/REQ-20260702-001-TASK-20260702-001/evidence.yaml" in evidence_result.output
    assert validation_result.exit_code == 0
    assert "updated docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in validation_result.output
    assert handoff_result.exit_code == 0
    assert done_result.exit_code == 0
    assert task["stage"] == "done"


def test_evidence_create_dry_run_does_not_write_record(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run docs/active/REQ-20260702-001-TASK-20260702-001/evidence.yaml" in result.output
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml").exists()


def test_evidence_create_requires_explicit_conclusion(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "--conclusion" in combined_output(result)


def test_validation_apply_rejects_missing_evidence_command(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-MISSING",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "missing_evidence_record: EV-MISSING" in combined_output(result)


def test_validation_apply_rejects_status_mismatch(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "failed",
            "--key-output",
            "pytest failed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "validation_status_mismatch" in combined_output(result)


def test_validation_apply_rejects_passed_evidence_with_unverified_items(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "pytest passed",
            "--unverified-item",
            "用户验收未完成。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "evidence_has_unverified_items" in combined_output(result)


def test_done_rechecks_evidence_conclusion_even_if_task_validation_claims_passed(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    evidence_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    evidence_yaml.write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "EV-REQ-20260702-001-TASK-20260702-001",
                "task_id": "REQ-20260702-001-TASK-20260702-001",
                "conclusion": "failed",
                "key_outputs": ["pytest failed"],
                "unverified_items": [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    task["validation"] = {
        "status": "passed",
        "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001",
        "unverified_items": [],
    }
    task["handoff"] = {"status": "accepted", "note": "用户验收通过。"}
    task_yaml.write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "done",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "evidence_not_passed: failed" in combined_output(result)


def test_validation_apply_requires_explicit_status(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "--status" in combined_output(result)


def test_validation_apply_dry_run_does_not_update_task(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
            "--dry-run",
        ],
    )

    task = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text("utf-8")
    )
    assert result.exit_code == 0
    assert "dry-run docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in result.output
    assert task["validation"]["status"] == "not_started"


def test_handoff_set_dry_run_does_not_update_task(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "handoff",
            "set",
            "REQ-20260702-001-TASK-20260702-001",
            "--status",
            "waiting_user_validation",
            "--note",
            "等待用户验收。",
            "--workspace-root",
            str(tmp_path),
            "--dry-run",
        ],
    )

    task = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").read_text("utf-8")
    )
    assert result.exit_code == 0
    assert "dry-run docs/active/REQ-20260702-001-TASK-20260702-001/task.yaml" in result.output
    assert "handoff" not in task


def test_handoff_waiting_blocks_done_command(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    runner.invoke(
        app,
        [
            "evidence",
            "create",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--task-id",
            "REQ-20260702-001-TASK-20260702-001",
            "--conclusion",
            "passed",
            "--key-output",
            "python -m pytest passed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    runner.invoke(
        app,
        [
            "validation",
            "apply",
            "REQ-20260702-001-TASK-20260702-001",
            "--evidence-id",
            "EV-REQ-20260702-001-TASK-20260702-001",
            "--status",
            "passed",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "handoff",
            "set",
            "REQ-20260702-001-TASK-20260702-001",
            "--status",
            "waiting_user_validation",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "done",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "handoff_waiting" in combined_output(result)


def test_task_context_resolves_task_by_title_and_uses_names(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    service_path = tmp_path / "repos" / "empty-web"
    service_path.mkdir(parents=True)
    runner.invoke(
        app,
        [
            "service",
            "add",
            "web-dashboard",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )
    create_task_via_cli(tmp_path, ["--service-ref", "web-dashboard"])

    result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "当前任务：实现任务 CLI" in result.output
    assert "所属需求：构建轻量 Workbench" in result.output
    assert "REQ-20260702-001-TASK" not in result.output
    assert "可以改代码：不可以" in result.output
    assert "ability code_change=" not in result.output
    assert "service web-dashboard" not in result.output
    assert "missing_implementation_ready" in result.output
    assert "服务现场" in result.output
    assert "web-dashboard：empty_dir" in result.output
    assert f"路径：{service_path}" in result.output
    assert "阻断：empty_service_dir" in result.output
    assert "提醒：not_git,no_entry_candidates" in result.output
    assert "empty_service_dir" in result.output
    assert "no_entry_candidates" in result.output
    assert "下一步建议" in result.output


def test_task_context_text_warns_when_service_has_existing_git_changes(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    service_path = tmp_path / "repos" / "web"
    service_path.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=service_path, check=True, capture_output=True, text=True)
    (service_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    runner.invoke(
        app,
        [
            "service",
            "add",
            "web-dashboard",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )
    create_task_via_cli(tmp_path, ["--service-ref", "web-dashboard"])

    result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "web-dashboard：non_empty_dir | Git：git" in result.output
    assert f"路径：{service_path}" in result.output
    assert "Git 范围：git_status=service_path,service_relpath=." in result.output
    assert "已有变更：dirty=0 untracked=1" in result.output


def test_task_context_json_reports_ability_matrix_and_service_context(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    service_path = tmp_path / "repos" / "web-dashboard"
    service_path.mkdir(parents=True)
    (service_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    (service_path / "src").mkdir()
    runner.invoke(
        app,
        [
            "service",
            "add",
            "web-dashboard",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )
    create_task_via_cli(tmp_path, ["--service-ref", "web-dashboard"])
    runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "实现 web-dashboard 页面修复。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--format", "json", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["task"]["title"] == "实现任务 CLI"
    assert payload["requirement"]["title"] == "构建轻量 Workbench"
    assert payload["ability_matrix"]["read_only"]["state"] == "allowed"
    assert payload["ability_matrix"]["write_state"]["state"] == "cli_only"
    assert payload["ability_matrix"]["code_change"]["state"] == "allowed"
    assert payload["ability_matrix"]["claim_done"]["state"] == "blocked"
    assert "validation_not_passed" in payload["ability_matrix"]["claim_done"]["gaps"]
    assert payload["services"][0]["name"] == "web-dashboard"
    assert payload["services"][0]["path_state"] == "non_empty_dir"
    assert payload["services"][0]["visible_file_count"] == 1
    assert payload["services"][0]["visible_file_count_limit_reached"] is False
    assert "git_status_scope" in payload["services"][0]
    assert "dirty_count" in payload["services"][0]
    assert "untracked_count" in payload["services"][0]
    assert payload["services"][0]["hard_gaps"] == []
    assert payload["services"][0]["warnings"] == ["not_git"]
    assert "package.json" in payload["services"][0]["entry_candidates"]


def test_task_context_deduplicates_and_limits_batch_service_refs(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    service_refs: list[str] = []
    for index in range(1, 8):
        service_name = f"service-{index}"
        service_path = tmp_path / "repos" / service_name
        service_path.mkdir(parents=True)
        (service_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
        service_refs.extend(["--service-ref", service_name])
        runner.invoke(
            app,
            [
                "service",
                "add",
                service_name,
                "--path",
                str(service_path),
                "--workspace-root",
                str(tmp_path),
            ],
        )
    create_task_via_cli(tmp_path, ["--service-ref", "service-1", *service_refs])

    result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "关联服务：service-1,service-2,service-3,service-4,service-5（共 7，已检查 5，未检查 2）" in result.output
    assert "service-1：non_empty_dir" in result.output
    assert "service-5：non_empty_dir" in result.output
    assert "service-6：non_empty_dir" not in result.output
    assert "还有 2 个关联服务未展开：service-6,service-7" in result.output
    assert "提醒：service_check_limited" in result.output


def test_task_context_service_limit_blocks_code_change_until_explicitly_expanded(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    service_refs: list[str] = []
    for index in range(1, 8):
        service_name = f"service-{index}"
        service_path = tmp_path / "repos" / service_name
        service_path.mkdir(parents=True)
        (service_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
        service_refs.extend(["--service-ref", service_name])
        runner.invoke(
            app,
            [
                "service",
                "add",
                service_name,
                "--path",
                str(service_path),
                "--workspace-root",
                str(tmp_path),
            ],
        )
    create_task_via_cli(tmp_path, service_refs)
    runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "修改多服务任务。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    default_result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--format", "json", "--workspace-root", str(tmp_path)],
    )
    expanded_result = runner.invoke(
        app,
        [
            "task",
            "context",
            "实现任务 CLI",
            "--format",
            "json",
            "--service-check-limit",
            "10",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert default_result.exit_code == 0
    default_context = json.loads(default_result.output)
    assert default_context["ability_matrix"]["code_change"]["state"] == "blocked"
    assert "service_check_limited" in default_context["ability_matrix"]["code_change"]["gaps"]
    assert default_context["unchecked_service_refs"] == ["service-6", "service-7"]
    assert expanded_result.exit_code == 0
    expanded_context = json.loads(expanded_result.output)
    assert expanded_context["ability_matrix"]["code_change"]["state"] == "allowed"
    assert expanded_context["unchecked_service_refs"] == []


def test_task_context_does_not_expand_evidence_body_or_write_files(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    evidence_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    evidence_payload = {
        "schema_version": "0.1",
        "id": "EV-REQ-20260702-001-TASK-20260702-001",
        "task_id": "REQ-20260702-001-TASK-20260702-001",
        "conclusion": "passed",
        "key_outputs": ["full evidence body with token=abc123 must stay out"],
        "unverified_items": [],
    }
    evidence_yaml.write_text(
        yaml.safe_dump(evidence_payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    before_task = task_yaml.read_text(encoding="utf-8")
    before_evidence = evidence_yaml.read_text(encoding="utf-8")

    text_result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--workspace-root", str(tmp_path)],
    )
    json_result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--format", "json", "--workspace-root", str(tmp_path)],
    )

    assert text_result.exit_code == 0
    assert json_result.exit_code == 0
    assert "token=abc123" not in text_result.output
    assert "full evidence body" not in text_result.output
    assert "token=abc123" not in json_result.output
    assert "full evidence body" not in json_result.output
    assert task_yaml.read_text(encoding="utf-8") == before_task
    assert evidence_yaml.read_text(encoding="utf-8") == before_evidence


def test_task_context_distinguishes_ready_to_mark_done_from_claiming_done(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    task["validation"] = {"status": "passed", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001"}
    task["handoff"] = {"status": "accepted", "note": "用户验收通过。"}
    task_yaml.write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False), encoding="utf-8")
    evidence_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    evidence_yaml.write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "EV-REQ-20260702-001-TASK-20260702-001",
                "task_id": "REQ-20260702-001-TASK-20260702-001",
                "conclusion": "passed",
                "key_outputs": ["验证通过。"],
                "unverified_items": [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "可以标记完成：需先标记" in result.output
    assert "可以声明完成：可以" not in result.output


def test_task_context_rechecks_current_gate_even_when_stage_is_in_progress(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    payload = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    payload["stage"] = "in_progress"
    task_yaml.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--format", "json", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    context = json.loads(result.output)
    assert context["ability_matrix"]["code_change"]["state"] == "blocked"
    assert "missing_implementation_ready" in context["ability_matrix"]["code_change"]["gaps"]


def test_task_context_treats_missing_entry_candidates_as_warning_not_hard_block(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    service_path = tmp_path / "repos" / "custom-service"
    service_path.mkdir(parents=True)
    (service_path / "service.custom").write_text("custom runtime\n", encoding="utf-8")
    runner.invoke(
        app,
        [
            "service",
            "add",
            "custom-service",
            "--path",
            str(service_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )
    create_task_via_cli(tmp_path, ["--service-ref", "custom-service"])
    runner.invoke(
        app,
        [
            "task",
            "prepare",
            "REQ-20260702-001-TASK-20260702-001",
            "--working-scope",
            "修改 custom-service。",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "task",
            "set-stage",
            "REQ-20260702-001-TASK-20260702-001",
            "--stage",
            "in_progress",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--format", "json", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    context = json.loads(result.output)
    assert context["ability_matrix"]["code_change"]["state"] == "allowed"
    assert "no_entry_candidates" in context["ability_matrix"]["code_change"]["warnings"]
    assert context["services"][0]["hard_gaps"] == []
    assert context["services"][0]["warnings"] == ["not_git", "no_entry_candidates"]


def test_task_context_rejects_explicit_task_path_when_directory_id_mismatches_yaml(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    original_dir = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001"
    mismatched_dir = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-999"
    original_dir.rename(mismatched_dir)

    result = runner.invoke(
        app,
        [
            "task",
            "context",
            str(mismatched_dir / "task.yaml"),
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    assert "task_path_id_mismatch" in combined_output(result)


def test_task_context_rejects_requirement_path_id_mismatch(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml"
    requirement_payload = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    requirement_payload["id"] = "REQ-20260702-999"
    requirement_yaml.write_text(
        yaml.safe_dump(requirement_payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert "requirement_path_id_mismatch" in combined_output(result)


def test_task_context_accepts_task_yaml_path(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"

    result = runner.invoke(
        app,
        ["task", "context", str(task_yaml), "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "当前任务：实现任务 CLI" in result.output
    assert "所属需求：构建轻量 Workbench" in result.output
    assert "REQ-20260702-001-TASK" not in result.output


def test_task_context_rejects_missing_task_yaml_path(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    missing_path = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"

    result = runner.invoke(
        app,
        ["task", "context", str(missing_path), "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert "task_path_missing" in combined_output(result)


def test_task_context_rejects_task_yaml_path_outside_active_packages(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    create_task_via_cli(tmp_path)
    task_dir = tmp_path / "docs" / "archive" / "REQ-20260702-001-TASK-20260702-001"
    task_dir.mkdir(parents=True)
    active_task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    archived_task_yaml = task_dir / "task.yaml"
    archived_task_yaml.write_text(active_task_yaml.read_text(encoding="utf-8"), encoding="utf-8")

    result = runner.invoke(
        app,
        ["task", "context", str(archived_task_yaml), "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert "task_path_not_active" in combined_output(result)


def test_task_context_rejects_unsupported_format_before_loading_workspace(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["task", "context", "不存在的任务", "--format", "yaml", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 2
    output = combined_output(result)
    assert "unsupported_format: yaml" in output
    assert "task_not_found" not in output
    assert "workspace_marker_missing" not in output


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


def test_material_add_and_list_commands_manage_inbox_registry(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    add_result = runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    list_result = runner.invoke(app, ["material", "list", "--workspace-root", str(tmp_path)])

    assert add_result.exit_code == 0
    assert "updated docs/inbox/materials.yaml" in add_result.output
    assert list_result.exit_code == 0
    assert "material MAT-001 思想文件" in list_result.output
    registry = yaml.safe_load((tmp_path / "docs" / "inbox" / "materials.yaml").read_text("utf-8"))
    assert registry["materials"][0]["committable_original"] is False


def test_material_add_dry_run_does_not_write_registry(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run docs/inbox/materials.yaml" in result.output
    assert not (tmp_path / "docs" / "inbox" / "materials.yaml").exists()


def test_discovery_create_records_layered_knowledge(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        [
            "discovery",
            "create",
            "DISC-001",
            "--title",
            "材料边界发现",
            "--material-ref",
            "MAT-001",
            "--observation",
            "inbox 材料尚未成熟。",
            "--inference",
            "需要 intake 确认后才能创建正式任务。",
            "--question",
            "是否确认进入 v1 范围？",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code == 0
    assert "created docs/inbox/DISC-001/discovery.yaml" in result.output
    discovery = yaml.safe_load(
        (tmp_path / "docs" / "inbox" / "DISC-001" / "discovery.yaml").read_text("utf-8")
    )
    assert discovery["material_refs"] == ["MAT-001"]
    assert discovery["knowledge"]["system_observations"] == ["inbox 材料尚未成熟。"]
    assert discovery["knowledge"]["ai_inferences"] == ["需要 intake 确认后才能创建正式任务。"]
    assert discovery["knowledge"]["questions_for_user"] == ["是否确认进入 v1 范围？"]


def test_intake_create_confirm_then_task_create(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "discovery",
            "create",
            "DISC-001",
            "--title",
            "材料边界发现",
            "--material-ref",
            "MAT-001",
            "--observation",
            "inbox 材料尚未成熟。",
            "--inference",
            "需要 intake 确认后才能创建正式任务。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    create_result = runner.invoke(
        app,
        [
            "intake",
            "create",
            "REQ-20260702-001",
            "--title",
            "构建轻量 Workbench",
            "--goal",
            "让 Codex 专注用户任务。",
            "--acceptance",
            "可以创建任务包。",
            "--material-ref",
            "MAT-001",
            "--discovery-ref",
            "DISC-001",
            "--confirmed-fact",
            "用户确认 v1 不做 Web UI。",
            "--inference",
            "材料需要先转成 intake 草案。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml"
    assert create_result.exit_code == 0
    draft = yaml.safe_load(requirement_yaml.read_text("utf-8"))
    assert draft["readiness"]["status"] == "intake_draft"
    assert draft["readiness"]["confirmed_by_user"] is False
    assert draft["readiness"]["material_refs"] == ["MAT-001"]
    assert draft["readiness"]["discovery_refs"] == ["DISC-001"]

    blocked_task = runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    confirm_result = runner.invoke(
        app,
        [
            "intake",
            "confirm",
            "REQ-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-02",
        ],
    )
    allowed_task = runner.invoke(
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
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    confirmed = yaml.safe_load(requirement_yaml.read_text("utf-8"))
    assert blocked_task.exit_code != 0
    assert "requirement_not_readable" in combined_output(blocked_task)
    assert confirm_result.exit_code == 0
    assert "updated docs/active/REQ-20260702-001/requirement.yaml" in confirm_result.output
    assert confirmed["readiness"]["status"] == "readable"
    assert confirmed["readiness"]["confirmed_by_user"] is True
    assert confirmed["updated_at"] == "2026-07-02"
    assert allowed_task.exit_code == 0
    assert (tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml").exists()


def test_intake_create_can_auto_id_and_default_time(tmp_path: Path, monkeypatch) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    monkeypatch.setattr(
        "codex_workbench.timeutils.current_timestamp",
        lambda: "2026-07-02T11:00:00+08:00",
    )

    result = runner.invoke(
        app,
        [
            "intake",
            "create",
            "--title",
            "自动编号 intake",
            "--goal",
            "省略需求 ID 和更新时间也能创建 intake 草案。",
            "--acceptance",
            "生成下一个当天需求 ID。",
            "--material-ref",
            "MAT-001",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml"
    assert result.exit_code == 0, combined_output(result)
    assert "created docs/active/REQ-20260702-001/requirement.yaml" in result.output
    requirement = yaml.safe_load(requirement_yaml.read_text("utf-8"))
    assert requirement["id"] == "REQ-20260702-001"
    assert requirement["created_at"] == "2026-07-02T11:00:00+08:00"
    assert requirement["updated_at"] == "2026-07-02T11:00:00+08:00"


def test_intake_confirm_rejects_plain_requirement_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "requirement",
            "create",
            "REQ-20260702-001",
            "--title",
            "普通需求",
            "--goal",
            "验证普通 requirement 不能直接确认。",
            "--acceptance",
            "必须被拒绝。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "intake",
            "confirm",
            "REQ-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml"
    requirement = yaml.safe_load(requirement_yaml.read_text("utf-8"))
    assert result.exit_code != 0
    assert "intake_not_confirmable" in combined_output(result)
    assert "readiness" not in requirement


def test_intake_confirm_rejects_draft_without_source_refs(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path, status="intake_draft", confirmed_by_user=False)

    result = runner.invoke(
        app,
        [
            "intake",
            "confirm",
            "REQ-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml"
    requirement = yaml.safe_load(requirement_yaml.read_text("utf-8"))
    assert result.exit_code != 0
    assert "missing_intake_source_refs" in combined_output(result)
    assert requirement["readiness"]["status"] == "intake_draft"
    assert requirement["readiness"]["confirmed_by_user"] is False


def test_intake_create_rejects_invalid_discovery_ref(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    discovery_dir = tmp_path / "docs" / "inbox" / "DISC-FAKE"
    discovery_dir.mkdir(parents=True)
    (discovery_dir / "discovery.yaml").write_text("not: a discovery\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "intake",
            "create",
            "REQ-20260702-001",
            "--title",
            "伪造 discovery",
            "--goal",
            "验证 discovery 引用必须可解析。",
            "--acceptance",
            "必须被拒绝。",
            "--discovery-ref",
            "DISC-FAKE",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "invalid_discovery_ref: DISC-FAKE" in combined_output(result)
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001").exists()


def test_intake_create_rejects_discovery_without_material_refs(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    discovery_dir = tmp_path / "docs" / "inbox" / "DISC-EMPTY"
    discovery_dir.mkdir(parents=True)
    (discovery_dir / "discovery.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "DISC-EMPTY",
                "title": "空材料引用",
                "material_refs": [],
                "updated_at": "2026-07-01",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "intake",
            "create",
            "REQ-20260702-001",
            "--title",
            "空 discovery",
            "--goal",
            "验证 discovery 必须来自材料。",
            "--acceptance",
            "必须被拒绝。",
            "--discovery-ref",
            "DISC-EMPTY",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "discovery_without_material_refs: DISC-EMPTY" in combined_output(result)
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001").exists()


def test_intake_confirm_rejects_discovery_whose_material_was_removed(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "discovery",
            "create",
            "DISC-001",
            "--title",
            "材料边界发现",
            "--material-ref",
            "MAT-001",
            "--observation",
            "inbox 材料尚未成熟。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    runner.invoke(
        app,
        [
            "intake",
            "create",
            "REQ-20260702-001",
            "--title",
            "构建轻量 Workbench",
            "--goal",
            "让 Codex 专注用户任务。",
            "--acceptance",
            "可以创建任务包。",
            "--discovery-ref",
            "DISC-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    (tmp_path / "docs" / "inbox" / "materials.yaml").write_text(
        "schema_version: '0.1'\nmaterials: []\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "intake",
            "confirm",
            "REQ-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    requirement = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml").read_text("utf-8")
    )
    assert result.exit_code != 0
    assert "unknown_material_ref: MAT-001" in combined_output(result)
    assert requirement["readiness"]["status"] == "intake_draft"
    assert requirement["readiness"]["confirmed_by_user"] is False


def test_intake_confirm_rejects_requirement_id_path_traversal(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    archived_req = tmp_path / "docs" / "archive" / "REQ-X"
    archived_req.mkdir(parents=True)
    (archived_req / "requirement.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "REQ-X",
                "title": "归档需求",
                "goal": "不应被 active confirm 修改。",
                "acceptance": ["必须保持未确认。"],
                "readiness": {
                    "status": "intake_draft",
                    "confirmed_by_user": False,
                    "material_refs": ["MAT-001"],
                    "discovery_refs": [],
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "intake",
            "confirm",
            "../archive/REQ-X",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-02",
        ],
    )

    requirement = yaml.safe_load((archived_req / "requirement.yaml").read_text("utf-8"))
    assert result.exit_code != 0
    assert "invalid_package_ref: ../archive/REQ-X" in combined_output(result)
    assert requirement["readiness"]["status"] == "intake_draft"
    assert requirement["readiness"]["confirmed_by_user"] is False


def test_intake_create_rejects_discovery_ref_path_traversal(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    archived_disc = tmp_path / "docs" / "archive" / "DISC-X"
    archived_disc.mkdir(parents=True)
    (archived_disc / "discovery.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "DISC-X",
                "title": "归档 discovery",
                "material_refs": ["MAT-001"],
                "updated_at": "2026-07-01",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "intake",
            "create",
            "REQ-20260702-001",
            "--title",
            "路径穿越 discovery",
            "--goal",
            "验证 discovery ref 不能越过 inbox。",
            "--acceptance",
            "必须被拒绝。",
            "--discovery-ref",
            "../archive/DISC-X",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "invalid_package_ref: ../archive/DISC-X" in combined_output(result)
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001").exists()


def test_intake_confirm_rejects_dot_requirement_id(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    (tmp_path / "docs" / "active").mkdir(parents=True, exist_ok=True)
    root_requirement = tmp_path / "docs" / "active" / "requirement.yaml"
    root_requirement.write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "REQ-DOT",
                "title": "根层需求",
                "goal": "不应被点号引用修改。",
                "acceptance": ["必须保持未确认。"],
                "readiness": {
                    "status": "intake_draft",
                    "confirmed_by_user": False,
                    "material_refs": ["MAT-001"],
                    "discovery_refs": [],
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "intake",
            "confirm",
            ".",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-02",
        ],
    )

    requirement = yaml.safe_load(root_requirement.read_text("utf-8"))
    assert result.exit_code != 0
    assert "invalid_package_ref: ." in combined_output(result)
    assert requirement["readiness"]["status"] == "intake_draft"
    assert requirement["readiness"]["confirmed_by_user"] is False


def test_intake_create_rejects_dot_discovery_ref(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    root_discovery = tmp_path / "docs" / "inbox" / "discovery.yaml"
    root_discovery.parent.mkdir(parents=True, exist_ok=True)
    root_discovery.write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "DISC-DOT",
                "title": "根层 discovery",
                "material_refs": ["MAT-001"],
                "updated_at": "2026-07-01",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "intake",
            "create",
            "REQ-20260702-001",
            "--title",
            "点号 discovery",
            "--goal",
            "验证 discovery ref 不能是点号。",
            "--acceptance",
            "必须被拒绝。",
            "--discovery-ref",
            ".",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "invalid_package_ref: ." in combined_output(result)
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001").exists()


def test_discovery_create_dry_run_does_not_write_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        [
            "discovery",
            "create",
            "DISC-001",
            "--title",
            "材料边界发现",
            "--material-ref",
            "MAT-001",
            "--observation",
            "inbox 材料尚未成熟。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run docs/inbox/DISC-001/discovery.yaml" in result.output
    assert not (tmp_path / "docs" / "inbox" / "DISC-001").exists()


def test_intake_create_dry_run_does_not_write_package(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(
        app,
        [
            "intake",
            "create",
            "REQ-20260702-001",
            "--title",
            "构建轻量 Workbench",
            "--goal",
            "让 Codex 专注用户任务。",
            "--acceptance",
            "可以创建任务包。",
            "--material-ref",
            "MAT-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run docs/active/REQ-20260702-001/requirement.yaml" in result.output
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001").exists()


def test_intake_confirm_dry_run_does_not_change_readiness(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    runner.invoke(
        app,
        [
            "material",
            "add",
            "MAT-001",
            "--title",
            "思想文件",
            "--source",
            "用户提供的本地 Markdown",
            "--summary",
            "描述 Workbench 的材料、发现和 intake 边界。",
            "--received-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    runner.invoke(
        app,
        [
            "intake",
            "create",
            "REQ-20260702-001",
            "--title",
            "构建轻量 Workbench",
            "--goal",
            "让 Codex 专注用户任务。",
            "--acceptance",
            "可以创建任务包。",
            "--material-ref",
            "MAT-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    result = runner.invoke(
        app,
        [
            "intake",
            "confirm",
            "REQ-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-02",
            "--dry-run",
        ],
    )

    requirement = yaml.safe_load(
        (tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml").read_text("utf-8")
    )
    assert result.exit_code == 0
    assert "dry-run docs/active/REQ-20260702-001/requirement.yaml" in result.output
    assert requirement["readiness"]["status"] == "intake_draft"
    assert requirement["readiness"]["confirmed_by_user"] is False
    assert requirement["updated_at"] == "2026-07-01"


def test_action_create_writes_machine_record_and_does_not_touch_task(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "保持旁路动作独立",
            "--user-goal",
            "动作记录不污染任务状态。",
            "--done",
            "action note 不支撑验证。",
            "--next",
            "创建动作记录。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    before_task = task_yaml.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "记录一次辅助动作",
            "--summary",
            "只记录动作，不支撑验证。",
            "--action-type",
            "maintenance_action",
            "--status",
            "partial",
            "--authorization",
            "用户确认本地维护动作。",
            "--target",
            "docs/generated",
            "--result",
            "已完成局部整理。",
            "--related-ref",
            "REQ-20260702-001-TASK-20260702-001",
            "--side-effect-summary",
            "no_side_effect",
            "--rollback-hint",
            "no_rollback_needed",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    action_yaml = tmp_path / "docs" / "actions" / "ACT-001.yaml"
    action_md = tmp_path / "docs" / "actions" / "ACT-001.md"
    assert result.exit_code == 0
    action = yaml.safe_load(action_yaml.read_text(encoding="utf-8"))
    assert "created docs/actions/ACT-001.yaml" in result.output
    assert "created docs/actions/ACT-001.md" in result.output
    assert action["id"] == "ACT-001"
    assert action["summary"] == "只记录动作，不支撑验证。"
    assert action["action_type"] == "maintenance_action"
    assert action["status"] == "partial"
    assert action["authorization"] == "用户确认本地维护动作。"
    assert action["target"] == "docs/generated"
    assert action["result"] == "已完成局部整理。"
    assert action["related_refs"] == ["REQ-20260702-001-TASK-20260702-001"]
    action_md_text = action_md.read_text(encoding="utf-8")
    assert action_md_text.startswith("# ACT-001 记录一次辅助动作\n")
    assert "## 操作记录" in action_md_text
    assert "只记录动作，不支撑验证。" not in action_md_text
    assert task_yaml.read_text(encoding="utf-8") == before_task


def test_action_create_rejects_product_task_action_type(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "错误动作类型",
            "--summary",
            "product_task 应进入正式 task，不应写 action note。",
            "--action-type",
            "product_task",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "validation_error" in combined_output(result)


def test_action_create_accepts_ops_and_ephemeral_action_types(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    for action_id, action_type in [
        ("ACT-OPS", "ops_action"),
        ("ACT-CHECK", "ephemeral_check"),
    ]:
        result = runner.invoke(
            app,
            [
                "action",
                "create",
                action_id,
                "--title",
                "记录非任务动作",
                "--summary",
                "只记录动作，不支撑验证。",
                "--action-type",
                action_type,
                "--workspace-root",
                str(tmp_path),
                "--updated-at",
                "2026-07-01",
            ],
        )

        action_yaml = yaml.safe_load(
            (tmp_path / "docs" / "actions" / f"{action_id}.yaml").read_text(
                encoding="utf-8"
            )
        )
        assert result.exit_code == 0
        assert action_yaml["action_type"] == action_type
        assert action_yaml["status"] == "executed"


def test_action_create_rejects_invalid_status(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "错误动作状态",
            "--summary",
            "动作状态必须可枚举。",
            "--action-type",
            "maintenance_action",
            "--status",
            "unknown",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert result.exit_code != 0
    assert "validation_error" in combined_output(result)


def test_change_classify_keeps_implementation_adjustment_lightweight(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "change",
            "classify",
            "--kind",
            "implementation_adjustment",
            "--summary",
            "只改局部文案。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "implementation_adjustment" in result.output
    assert "no_formal_change_record" in result.output
    assert not (tmp_path / "docs" / "changes").exists()


def test_change_classify_keeps_scope_clarification_lightweight(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "change",
            "classify",
            "--kind",
            "scope_clarification",
            "--summary",
            "用户澄清文案口径，但目标不变。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "scope_clarification" in result.output
    assert "requires_change_record=false" in result.output
    assert "scope_alignment_required" in result.output
    assert not (tmp_path / "docs" / "changes").exists()


def test_change_classify_requires_record_for_scope_change(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "change",
            "classify",
            "--kind",
            "scope_change",
            "--summary",
            "验收口径发生变化。",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "scope_change" in result.output
    assert "requires_change_record=true" in result.output
    assert "change_control_required" in result.output


def test_change_create_writes_formal_change_record(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "change",
            "create",
            "CHG-001",
            "--title",
            "记录验收变化",
            "--changed-area",
            "acceptance",
            "--reason",
            "用户改变验收口径。",
            "--impact",
            "需要更新任务边界。",
            "--handling",
            "先记录变更，再继续实现。",
            "--related-ref",
            "REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    change_yaml = tmp_path / "docs" / "changes" / "CHG-001.yaml"
    change_md = tmp_path / "docs" / "changes" / "CHG-001.md"
    assert result.exit_code == 0
    change = yaml.safe_load(change_yaml.read_text(encoding="utf-8"))
    assert "created docs/changes/CHG-001.yaml" in result.output
    assert "created docs/changes/CHG-001.md" in result.output
    assert change["id"] == "CHG-001"
    assert change["change_kind"] == "scope_change"
    assert change["changed_area"] == "acceptance"
    assert change["related_refs"] == ["REQ-20260702-001-TASK-20260702-001"]
    assert change["reason"] == "用户改变验收口径。"
    change_text = change_md.read_text(encoding="utf-8")
    assert change_text.startswith("# CHG-001 记录验收变化\n")
    assert "## 新口径" in change_text
    assert "用户改变验收口径。" not in change_text


def test_decision_create_writes_cold_path_record(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "decision",
            "create",
            "DEC-001",
            "--title",
            "记录长期决策",
            "--cold-path-reason",
            "影响多个后续任务。",
            "--context",
            "需要统一记录工具的机器真源。",
            "--decision",
            "四类记录使用 YAML 作为机器真源。",
            "--impact",
            "后续 CLI 和模板按该口径实现。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    decision_yaml = tmp_path / "docs" / "decisions" / "DEC-001.yaml"
    decision_md = tmp_path / "docs" / "decisions" / "DEC-001.md"
    assert result.exit_code == 0
    decision = yaml.safe_load(decision_yaml.read_text(encoding="utf-8"))
    assert decision["id"] == "DEC-001"
    assert decision["cold_path_reason"] == "影响多个后续任务。"
    assert decision["decision"] == "四类记录使用 YAML 作为机器真源。"
    decision_text = decision_md.read_text(encoding="utf-8")
    assert decision_text.startswith("# DEC-001 记录长期决策\n")
    assert "## 取舍" in decision_text
    assert "影响多个后续任务。" not in decision_text


def test_suspicion_create_records_clue_without_touching_task(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    runner.invoke(
        app,
        [
            "task",
            "create",
            "REQ-20260702-001-TASK-20260702-001",
            "--requirement-id",
            "REQ-20260702-001",
            "--title",
            "保持疑点独立",
            "--user-goal",
            "疑点记录不授权修改。",
            "--done",
            "任务状态不被疑点记录改变。",
            "--next",
            "记录疑点。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    before_task = task_yaml.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "suspicion",
            "create",
            "SUS-001",
            "--title",
            "记录疑点",
            "--location",
            "src/demo.py",
            "--fact",
            "发现不一致现象。",
            "--inference",
            "可能需要后续复核。",
            "--assumption",
            "当前证据不足以修改。",
            "--current-task-impact",
            "不影响当前任务。",
            "--suggested-handling",
            "后续单独评估。",
            "--related-ref",
            "REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    suspicion_yaml = tmp_path / "docs" / "suspicions" / "SUS-001.yaml"
    suspicion_md = tmp_path / "docs" / "suspicions" / "SUS-001.md"
    assert result.exit_code == 0
    suspicion = yaml.safe_load(suspicion_yaml.read_text(encoding="utf-8"))
    assert suspicion["id"] == "SUS-001"
    assert suspicion["confirmed_facts"] == ["发现不一致现象。"]
    assert suspicion["ai_inferences"] == ["可能需要后续复核。"]
    assert suspicion["current_task_impact"] == "不影响当前任务。"
    assert suspicion["suggested_handling"] == "后续单独评估。"
    suspicion_text = suspicion_md.read_text(encoding="utf-8")
    assert suspicion_text.startswith("# SUS-001 记录疑点\n")
    assert "## 不确定点" in suspicion_text
    assert "后续单独评估。" not in suspicion_text
    assert task_yaml.read_text(encoding="utf-8") == before_task


def test_action_create_dry_run_duplicate_and_bad_ref_guards(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    dry_run = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "记录动作",
            "--summary",
            "只记录动作。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
            "--dry-run",
        ],
    )
    assert dry_run.exit_code == 0
    assert "dry-run docs/actions/ACT-001.yaml" in dry_run.output
    assert not (tmp_path / "docs" / "actions" / "ACT-001.yaml").exists()

    created = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "记录动作",
            "--summary",
            "只记录动作。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    duplicate = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-001",
            "--title",
            "记录动作",
            "--summary",
            "只记录动作。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    bad_ref = runner.invoke(
        app,
        [
            "action",
            "create",
            "ACT-002",
            "--title",
            "记录动作",
            "--summary",
            "只记录动作。",
            "--related-ref",
            "TASK/001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )

    assert created.exit_code == 0
    assert duplicate.exit_code != 0
    assert "already_exists: docs/actions/ACT-001.yaml" in combined_output(duplicate)
    assert bad_ref.exit_code != 0
    assert "invalid_package_ref: TASK/001" in combined_output(bad_ref)


def test_change_decision_suspicion_negative_guards(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    change_dry_run = runner.invoke(
        app,
        [
            "change",
            "create",
            "CHG-001",
            "--title",
            "记录范围变化",
            "--changed-area",
            "acceptance",
            "--reason",
            "验收口径变化。",
            "--impact",
            "需要更新任务边界。",
            "--handling",
            "先记录变更再继续。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
            "--dry-run",
        ],
    )
    assert change_dry_run.exit_code == 0
    assert "dry-run docs/changes/CHG-001.yaml" in change_dry_run.output
    assert not (tmp_path / "docs" / "changes" / "CHG-001.yaml").exists()

    decision_create = runner.invoke(
        app,
        [
            "decision",
            "create",
            "DEC-001",
            "--title",
            "记录长期决策",
            "--cold-path-reason",
            "影响多个后续任务。",
            "--context",
            "需要统一记录口径。",
            "--decision",
            "采用冷路径记录。",
            "--impact",
            "后续任务复用该口径。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    decision_duplicate = runner.invoke(
        app,
        [
            "decision",
            "create",
            "DEC-001",
            "--title",
            "记录长期决策",
            "--cold-path-reason",
            "影响多个后续任务。",
            "--context",
            "需要统一记录口径。",
            "--decision",
            "采用冷路径记录。",
            "--impact",
            "后续任务复用该口径。",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    assert decision_create.exit_code == 0
    assert decision_duplicate.exit_code != 0
    assert "already_exists: docs/decisions/DEC-001.yaml" in combined_output(decision_duplicate)

    suspicion_bad_ref = runner.invoke(
        app,
        [
            "suspicion",
            "create",
            "SUS-001",
            "--title",
            "记录疑点",
            "--location",
            "src/demo.py",
            "--fact",
            "发现不一致现象。",
            "--inference",
            "可能需要后续复核。",
            "--current-task-impact",
            "不影响当前任务。",
            "--suggested-handling",
            "后续单独评估。",
            "--related-ref",
            "../REQ-20260702-001-TASK-20260702-001",
            "--workspace-root",
            str(tmp_path),
            "--updated-at",
            "2026-07-01",
        ],
    )
    assert suspicion_bad_ref.exit_code != 0
    assert "invalid_package_ref: ../REQ-20260702-001-TASK-20260702-001" in combined_output(suspicion_bad_ref)


def write_archive_ready_requirement(root: Path) -> None:
    requirement_dir = root / "docs" / "active" / "REQ-20260702-001"
    requirement_dir.mkdir(parents=True)
    (requirement_dir / "requirement.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "REQ-20260702-001",
                "title": "完成版本",
                "goal": "形成可归档版本。",
                "created_at": "2026-07-01T09:00:00+08:00",
                "updated_at": "2026-07-01T09:00:00+08:00",
                "readiness": {"status": "readable", "confirmed_by_user": True},
                "task_refs": ["REQ-20260702-001-TASK-20260702-001"],
                "confirmations": [
                    {
                        "type": "requirement_closure",
                        "source": "user",
                        "note": "用户确认需求关闭。",
                    }
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (requirement_dir / "requirement.md").write_text("# REQ-20260702-001\n", encoding="utf-8")


def write_archive_ready_task(root: Path) -> None:
    task_dir = root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001"
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "REQ-20260702-001-TASK-20260702-001",
                "requirement_id": "REQ-20260702-001",
                "title": "完成验证",
                "created_at": "2026-07-01T09:30:00+08:00",
                "updated_at": "2026-07-01T10:00:00+08:00",
                "stage": "done",
                "process_level": "standard",
                "risk_level": "standard",
                "validation": {
                    "status": "passed",
                    "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001",
                    "unverified_items": [],
                },
                "handoff": {"status": "accepted", "note": "用户验收通过。"},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (task_dir / "task.md").write_text("# REQ-20260702-001-TASK-20260702-001\n", encoding="utf-8")
    (task_dir / "evidence.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "EV-REQ-20260702-001-TASK-20260702-001",
                "task_id": "REQ-20260702-001-TASK-20260702-001",
                "conclusion": "passed",
                "key_outputs": ["pytest passed"],
                "unverified_items": [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_archive_preflight_cli_checks_without_writing(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_archive_ready_requirement(tmp_path)
    write_archive_ready_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "archive",
            "preflight",
            "1.0.0",
            "--requirement-id",
            "REQ-20260702-001",
            "--authorization-note",
            "用户确认版本可以归档。",
            "--archived-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "archive preflight clean" in result.output
    assert "warning generated_view_missing" in result.output
    assert not (tmp_path / "docs" / "archive" / "1.0.0" / "archive.yaml").exists()


def test_archive_version_cli_dry_run_does_not_write(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_archive_ready_requirement(tmp_path)
    write_archive_ready_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "archive",
            "version",
            "1.0.0",
            "--requirement-id",
            "REQ-20260702-001",
            "--authorization-note",
            "用户确认版本可以归档。",
            "--archived-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run docs/archive/1.0.0/archive.yaml" in result.output
    assert not (tmp_path / "docs" / "archive" / "1.0.0" / "archive.yaml").exists()


def test_archive_version_cli_requires_authorization_note(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_archive_ready_requirement(tmp_path)
    write_archive_ready_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "archive",
            "version",
            "1.0.0",
            "--requirement-id",
            "REQ-20260702-001",
            "--archived-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "missing_archive_authorization" in combined_output(result)


def test_archive_version_cli_moves_active_packages(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_archive_ready_requirement(tmp_path)
    write_archive_ready_task(tmp_path)

    result = runner.invoke(
        app,
        [
            "archive",
            "version",
            "1.0.0",
            "--requirement-id",
            "REQ-20260702-001",
            "--authorization-note",
            "用户确认版本可以归档。",
            "--archived-at",
            "2026-07-01",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "archived docs/archive/1.0.0/archive.yaml" in result.output
    assert not (tmp_path / "docs" / "active" / "REQ-20260702-001").exists()
    assert (tmp_path / "docs" / "archive" / "1.0.0" / "REQ-20260702-001").exists()


def test_archive_list_cli_reads_cold_history_on_demand(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    archive_dir = tmp_path / "docs" / "archive" / "1.0.0"
    archive_dir.mkdir(parents=True)
    (archive_dir / "archive.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "version": "1.0.0",
                "archived_at": "2026-07-01",
                "requirement_ids": ["REQ-20260702-001"],
                "authorization": {
                    "type": "archive_authorization",
                    "source": "user",
                    "note": "用户确认版本可以归档。",
                },
                "entries": [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["archive", "list", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "`1.0.0` archived_at=2026-07-01 requirements=REQ-20260702-001" in result.output


def test_archive_list_cli_rejects_manifest_with_wrong_authorization_type(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    archive_dir = tmp_path / "docs" / "archive" / "1.0.0"
    archive_dir.mkdir(parents=True)
    (archive_dir / "archive.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "version": "1.0.0",
                "archived_at": "2026-07-01",
                "requirement_ids": ["REQ-20260702-001"],
                "authorization": {
                    "type": "acceptance_confirmation",
                    "source": "user",
                    "note": "这只是验收，不是归档授权。",
                },
                "entries": [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["archive", "list", "--workspace-root", str(tmp_path)])

    assert result.exit_code != 0
    assert "invalid_archive_manifest: docs/archive/1.0.0/archive.yaml" in combined_output(result)
