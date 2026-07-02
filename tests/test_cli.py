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
    assert "标题、章节和表达方式可按当前任务自由删改" in hint_lines[-1]
    assert "task.yaml" not in hint_lines[-1]


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
    assert result.output.strip() == "codex-workbench 0.1.0"


def test_schema_list_command_lists_core_models() -> None:
    result = runner.invoke(app, ["schema", "list"])

    assert result.exit_code == 0
    assert "TaskState" in result.output
    assert "WorkspaceState" in result.output
    assert "ChangeRecordState" in result.output
    assert "SuspicionState" in result.output


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
            "--risk-acceptance-note",
            "用户确认高风险边界。",
            "--risk-trigger",
            "触发真实数据写入时暂停确认。",
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
    assert full_prepare.exit_code == 0
    assert allowed.exit_code == 0


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
