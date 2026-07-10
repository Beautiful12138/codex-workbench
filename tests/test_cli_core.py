from __future__ import annotations

import importlib
import os
import pkgutil
import subprocess
import sys
from pathlib import Path

import yaml

from codex_workbench.cli import app
from tests.cli_test_support import (
    combined_output,
    create_task_via_cli,
    create_workspace,
    runner,
    workspace_context_section,
    write_requirement,
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


def add_project_services(tmp_path: Path, project: str, names: list[str]) -> None:
    for name in names:
        service_path = tmp_path / "repos" / name
        service_path.mkdir(parents=True)
        result = runner.invoke(
            app,
            [
                "service",
                "add",
                name,
                "--path",
                str(service_path),
                "--project",
                project,
                "--workspace-root",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0


def test_workspace_context_lists_ungrouped_service_names_without_details(tmp_path: Path) -> None:
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
    assert "登记项目：0" in result.output
    overview = workspace_context_section(
        result.output,
        "## 项目与服务概览",
        "## 任务焦点",
    )
    assert "- 未分组：1 个服务" in overview
    assert "  - web-dashboard" in overview
    assert "路径：" not in overview
    assert "任务引用：" not in overview
    assert "registry_only" not in overview
    assert "non_empty_dir" not in result.output
    assert "入口：package.json" not in result.output
    assert "## 当前服务" not in result.output
    assert f"路径：{service_path}" not in result.output


def test_workspace_context_groups_all_service_names_without_details(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_names = [f"studio-service-{index:02d}" for index in range(1, 24)]
    add_project_services(tmp_path, "studioV3", service_names)
    ungrouped_path = tmp_path / "repos" / "standalone"
    ungrouped_path.mkdir(parents=True)
    runner.invoke(
        app,
        [
            "service",
            "add",
            "standalone",
            "--path",
            str(ungrouped_path),
            "--purpose",
            "不应出现在默认概览的用途",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    result = runner.invoke(app, ["workspace", "context", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "登记项目：1" in result.output
    overview = workspace_context_section(
        result.output,
        "## 项目与服务概览",
        "## 任务焦点",
    )
    assert "- studioV3：23 个服务" in overview
    assert "- 未分组：1 个服务" in overview
    for name in [*service_names, "standalone"]:
        assert f"  - {name}" in overview
    assert "and " not in overview
    assert "路径：" not in overview
    assert "用途：" not in overview
    assert "Git：" not in overview
    assert "registry_only" not in overview


def test_workspace_context_filters_project_and_ungrouped_services(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    add_project_services(tmp_path, "studioV3", ["api", "worker"])
    standalone_path = tmp_path / "repos" / "standalone"
    standalone_path.mkdir(parents=True)
    runner.invoke(
        app,
        [
            "service",
            "add",
            "standalone",
            "--path",
            str(standalone_path),
            "--workspace-root",
            str(tmp_path),
        ],
    )

    grouped = runner.invoke(
        app,
        [
            "workspace",
            "context",
            "--project",
            "studioV3",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    ungrouped = runner.invoke(
        app,
        ["workspace", "context", "--ungrouped", "--workspace-root", str(tmp_path)],
    )

    assert grouped.exit_code == 0
    grouped_overview = workspace_context_section(
        grouped.output,
        "## 项目与服务概览",
        "## 任务焦点",
    )
    assert "  - api" in grouped_overview
    assert "  - worker" in grouped_overview
    assert "standalone" not in grouped_overview
    assert ungrouped.exit_code == 0
    ungrouped_overview = workspace_context_section(
        ungrouped.output,
        "## 项目与服务概览",
        "## 任务焦点",
    )
    assert "  - standalone" in ungrouped_overview
    assert "  - api" not in ungrouped_overview


def test_workspace_context_rejects_invalid_project_filters(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    conflict = runner.invoke(
        app,
        [
            "workspace",
            "context",
            "--project",
            "studioV3",
            "--ungrouped",
            "--workspace-root",
            str(tmp_path),
        ],
    )
    unknown = runner.invoke(
        app,
        [
            "workspace",
            "context",
            "--project",
            "missing",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert conflict.exit_code == 2
    assert "workspace_project_options_conflict" in combined_output(conflict)
    assert unknown.exit_code == 2
    assert "unknown_project: missing" in combined_output(unknown)


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
    requirement_yaml.write_text(
        yaml.safe_dump(requirement, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
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

    result = runner.invoke(
        app,
        ["workspace", "context", "--check-services", "--workspace-root", str(tmp_path)],
    )

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
    service_overview = workspace_context_section(
        result.output,
        "## 项目与服务概览",
        "## 任务焦点",
    )
    checked_service_overview = workspace_context_section(
        checked_result.output,
        "## 项目与服务概览",
        "## 服务检查",
    )
    assert (
        "- missing-active-service：任务引用：1 | 阻断：unknown_service_ref"
        in service_overview
    )
    assert (
        "- missing-active-service：任务引用：1 | 阻断：unknown_service_ref"
        in checked_service_overview
    )


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

    result = runner.invoke(
        app, ["workspace", "context", "--check-services", "--workspace-root", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "## 项目与服务概览" in result.output
    assert "## 服务检查" in result.output
    assert (
        "- web-dashboard：non_empty_dir | Git：not_git | 入口：package.json | 任务引用：0 | 提醒：not_git"
        in result.output
    )


def test_workspace_context_checks_at_most_five_services_in_selected_project(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    service_names = [f"service-{index}" for index in range(1, 7)]
    add_project_services(tmp_path, "studioV3", service_names)

    result = runner.invoke(
        app,
        [
            "workspace",
            "context",
            "--project",
            "studioV3",
            "--check-services",
            "--workspace-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    overview = workspace_context_section(
        result.output,
        "## 项目与服务概览",
        "## 服务检查",
    )
    checks = workspace_context_section(
        result.output,
        "## 服务检查",
        "## 任务焦点",
    )
    for name in service_names:
        assert f"  - {name}" in overview
    for name in service_names[:5]:
        assert f"- {name}：" in checks
    assert f"- {service_names[5]}：" not in checks
    assert "- and 1 more unchecked services" in checks


def test_workspace_context_groups_waiting_feedback_without_treating_it_as_blocked(
    tmp_path: Path,
) -> None:
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
    requirement_yaml.write_text(
        yaml.safe_dump(requirement, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
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
        task_yaml.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

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
    assert "草稿整理 [draft]" not in workspace_context_section(
        result.output, "等待反馈：", "阻塞："
    )
    assert "草稿整理 [draft]" not in workspace_context_section(result.output, "需确认：", "## 冲突")
    assert "REQ-20260702-001-TASK" not in result.output


def test_workspace_context_subprocess_works_with_documented_pythonpath(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    project_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "codex_workbench",
            "workspace",
            "context",
            "--workspace-root",
            str(tmp_path),
        ],
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
    assert (
        "conflict: unknown_service_ref: REQ-20260702-001-TASK-20260702-001 -> missing-service"
        in combined_output(generate)
    )
    assert check.exit_code != 0
    assert (
        "conflict: unknown_service_ref: REQ-20260702-001-TASK-20260702-001 -> missing-service"
        in combined_output(check)
    )


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
