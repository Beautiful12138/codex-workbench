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
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "services": [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def write_task(
    root: Path,
    *,
    task_id: str = "REQ-20260702-001-TASK-20260702-001",
    stage: str = "in_progress",
    process_level: str = "standard",
    risk_level: str = "standard",
    service_refs: list[str] | None = None,
    implementation: dict[str, object] | None = None,
    working_scope: list[str] | None = None,
    risk_triggers: list[str] | None = None,
    obsolete_reason: str | None = None,
    validation: dict[str, object] | None = None,
    handoff: dict[str, object] | None = None,
) -> Path:
    task_dir = root / "docs" / "active" / task_id
    task_dir.mkdir(parents=True)
    requirement_id = task_id.split("-TASK-", 1)[0] if "-TASK-" in task_id else "REQ-20260702-001"
    payload = {
        "schema_version": "0.1",
        "id": task_id,
        "requirement_id": requirement_id,
        "title": "实现 Doctor",
        "created_at": "2026-07-01T09:00:00+08:00",
        "updated_at": "2026-07-01T09:00:00+08:00",
        "stage": stage,
        "process_level": process_level,
        "risk_level": risk_level,
        "service_refs": service_refs or [],
        "implementation": implementation or {"ready": True, "conclusion": "scoped"},
        "working_scope": working_scope or [],
        "risk_triggers": risk_triggers or [],
        "validation": validation or {"status": "not_started"},
        "handoff": handoff or {"status": "not_required"},
    }
    if obsolete_reason is not None:
        payload["obsolete_reason"] = obsolete_reason
    (task_dir / "task.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    task_md = task_dir / "task.md"
    task_md.write_text(f"# {task_id}\n", encoding="utf-8")
    _upsert_requirement_ref(root, requirement_id, task_id)
    return task_md


def _upsert_requirement_ref(root: Path, requirement_id: str, task_id: str) -> None:
    requirement_dir = root / "docs" / "active" / requirement_id
    requirement_dir.mkdir(parents=True, exist_ok=True)
    requirement_yaml = requirement_dir / "requirement.yaml"
    if requirement_yaml.exists():
        payload = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    else:
        payload = {
            "schema_version": "0.1",
            "id": requirement_id,
            "title": "测试需求",
            "goal": "支撑 doctor 测试。",
            "created_at": "2026-07-01T08:00:00+08:00",
            "updated_at": "2026-07-01T08:00:00+08:00",
            "readiness": {"status": "readable", "confirmed_by_user": True},
            "task_refs": [],
        }
    task_refs = payload.setdefault("task_refs", [])
    if task_id not in task_refs:
        task_refs.append(task_id)
    requirement_yaml.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def write_evidence(
    root: Path,
    *,
    task_id: str = "REQ-20260702-001-TASK-20260702-001",
    evidence_id: str = "EV-REQ-20260702-001-TASK-20260702-001",
    conclusion: str = "passed",
) -> None:
    task_dir = root / "docs" / "active" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "0.1",
        "id": evidence_id,
        "task_id": task_id,
        "conclusion": conclusion,
        "key_outputs": ["本地验证已执行。"],
        "unverified_items": [],
    }
    (task_dir / "evidence.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def combined_output(result) -> str:
    return result.output + getattr(result, "stderr", "")


def snapshot_workspace(root: Path) -> tuple[list[str], dict[str, bytes]]:
    paths = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    contents = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    return paths, contents


def test_doctor_check_clean_workspace_uses_minimal_default_output(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert result.output.strip() == "doctor clean"
    output = combined_output(result).lower()
    assert "warning" not in output
    assert "suggestion" not in output


def test_doctor_check_can_expand_warning_details(tmp_path: Path) -> None:
    create_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "doctor",
            "check",
            "--workspace-root",
            str(tmp_path),
            "--show-warnings",
        ],
    )

    assert result.exit_code == 0
    output = combined_output(result)
    assert "doctor clean" in output
    assert "warning" in output
    assert "docs/generated/index.md" in output


def test_doctor_check_reports_unknown_service_ref_as_blocking(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, service_refs=["missing-service"])

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 1
    output = combined_output(result)
    assert "blocking" in output
    assert "unknown_service_ref" in output
    assert "missing-service" in output


def test_doctor_check_reports_each_unknown_service_ref(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, task_id="REQ-20260702-001-TASK-20260702-001", service_refs=["missing-one"])
    write_task(tmp_path, task_id="REQ-20260702-001-TASK-20260702-002", service_refs=["missing-two"])

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 1
    output = combined_output(result)
    assert "missing-one" in output
    assert "missing-two" in output


def test_doctor_check_blocks_in_progress_without_ready_gate(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, implementation={"ready": False})

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 1
    output = combined_output(result)
    assert "in_progress_gate_blocked" in output
    assert "missing_implementation_ready" in output


def test_doctor_check_blocks_high_risk_in_progress_without_extra_readiness(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, risk_level="high")

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 1
    output = combined_output(result)
    assert "in_progress_gate_blocked" in output
    assert "missing_high_risk_review" in output
    assert "missing_high_risk_implementation_ref" in output
    assert "missing_high_risk_working_scope" in output
    assert "missing_high_risk_triggers" in output
    assert "missing_high_risk_acceptance" in output


def test_doctor_check_blocks_invalid_action_type(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    action_dir = tmp_path / "docs" / "actions"
    action_dir.mkdir(parents=True)
    (action_dir / "ACT-001.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "id": "ACT-001",
                "title": "错误动作类型",
                "updated_at": "2026-07-01",
                "summary": "product_task 不应作为 action note。",
                "action_type": "product_task",
                "side_effect_summary": "no_side_effect",
                "rollback_hint": "no_rollback_needed",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 1
    output = combined_output(result)
    assert "invalid_model" in output
    assert "ActionNoteState" in output


def test_doctor_check_blocks_high_risk_blank_scope_and_triggers(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(
        tmp_path,
        risk_level="high",
        implementation={
            "ready": True,
            "conclusion": "scoped",
            "ref": "implementation.md",
        },
        working_scope=["   "],
        risk_triggers=["   "],
    )

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 1
    output = combined_output(result)
    assert "missing_high_risk_working_scope" in output
    assert "missing_high_risk_triggers" in output


def test_doctor_check_blocks_obsolete_task_without_reason(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, stage="obsolete")

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 1
    output = combined_output(result)
    assert "obsolete_state_invalid" in output
    assert "missing_obsolete_reason" in output


def test_doctor_check_allows_obsolete_task_with_reason(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, stage="obsolete", obsolete_reason="误建任务，已废弃。")

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert result.output.strip() == "doctor clean"


def test_doctor_check_allows_non_passed_evidence_before_done(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(
        tmp_path,
        stage="verification_pending",
        validation={"status": "failed", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001"},
    )
    write_evidence(tmp_path, conclusion="failed")

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 0
    assert result.output.strip() == "doctor clean"


def test_doctor_check_does_not_treat_markdown_keywords_as_findings(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    task_md = write_task(tmp_path)
    task_md.write_text(
        "\n".join(
            [
                "# REQ-20260702-001-TASK-20260702-001",
                "",
                "这是一段普通中文说明，提到了部署、权限、真实数据、token 和 archive。",
                "这些词只是在解释非目标，不应该被 Doctor 当成风险结论。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    runner.invoke(app, ["index", "generate", "--workspace-root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "doctor",
            "check",
            "--workspace-root",
            str(tmp_path),
            "--show-warnings",
            "--show-suggestions",
        ],
    )

    assert result.exit_code == 0
    assert result.output.strip() == "doctor clean"
    output = combined_output(result).lower()
    assert "warning" not in output
    assert "suggestion" not in output


def test_doctor_check_is_read_only(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path)
    before = snapshot_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "doctor",
            "check",
            "--workspace-root",
            str(tmp_path),
            "--show-warnings",
        ],
    )

    assert result.exit_code == 0
    assert snapshot_workspace(tmp_path) == before


def test_doctor_check_blocks_done_task_without_evidence(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_task(tmp_path, stage="done")

    result = runner.invoke(app, ["doctor", "check", "--workspace-root", str(tmp_path)])

    assert result.exit_code == 1
    output = combined_output(result)
    assert "blocking" in output
    assert "validation_not_passed" in output
    assert "missing_evidence" in output
