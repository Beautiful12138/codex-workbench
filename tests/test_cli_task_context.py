from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from codex_workbench.cli import app
from tests.cli_test_support import (
    combined_output,
    create_task_via_cli,
    create_workspace,
    runner,
    write_requirement,
)


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
        (service_path / "package.json").write_text(
            '{"scripts":{"test":"vitest"}}\n', encoding="utf-8"
        )
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
    assert (
        "关联服务：service-1,service-2,service-3,service-4,service-5（共 7，已检查 5，未检查 2）"
        in result.output
    )
    assert "service-1：non_empty_dir" in result.output
    assert "service-5：non_empty_dir" in result.output
    assert "service-6：non_empty_dir" not in result.output
    assert "还有 2 个关联服务未展开：service-6,service-7" in result.output
    assert "提醒：service_check_limited" in result.output


def test_task_context_service_limit_blocks_code_change_until_explicitly_expanded(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_requirement(tmp_path)
    service_refs: list[str] = []
    for index in range(1, 8):
        service_name = f"service-{index}"
        service_path = tmp_path / "repos" / service_name
        service_path.mkdir(parents=True)
        (service_path / "package.json").write_text(
            '{"scripts":{"test":"vitest"}}\n', encoding="utf-8"
        )
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
    evidence_yaml = (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    )
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
    task["validation"] = {
        "status": "passed",
        "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001",
    }
    task["handoff"] = {"status": "accepted", "note": "用户验收通过。"}
    task_yaml.write_text(
        yaml.safe_dump(task, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    evidence_yaml = (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml"
    )
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
    task_yaml.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    result = runner.invoke(
        app,
        ["task", "context", "实现任务 CLI", "--format", "json", "--workspace-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    context = json.loads(result.output)
    assert context["ability_matrix"]["code_change"]["state"] == "blocked"
    assert "missing_implementation_ready" in context["ability_matrix"]["code_change"]["gaps"]


def test_task_context_treats_missing_entry_candidates_as_warning_not_hard_block(
    tmp_path: Path,
) -> None:
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
    active_task_yaml = (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    )
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
