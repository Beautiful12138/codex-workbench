from __future__ import annotations

from pathlib import Path

import yaml

from codex_workbench.index import check_generated_views, generate_index_views


def create_workspace(root: Path) -> None:
    (root / "services").mkdir()
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CURRENT.md").write_text("# CURRENT\n", encoding="utf-8")
    (root / "services" / "registry.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "services": [
                    {
                        "name": "codex-workbench",
                        "local_path": "D:/Study/codex-workbench",
                        "purpose": "新一代 Workbench 实现目标。",
                    }
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def create_full_index_fixture(root: Path) -> None:
    create_workspace(root)
    write_yaml(
        root / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml",
        {
            "schema_version": "0.1",
            "id": "REQ-20260702-001",
            "title": "构建 Workbench",
            "goal": "让 Codex 可恢复地工作。",
            "created_at": "2026-07-01T09:00:00+08:00",
            "updated_at": "2026-07-01",
            "acceptance": ["index 可重建。"],
            "task_refs": ["REQ-20260702-001-TASK-20260702-001"],
            "readiness": {"status": "readable", "confirmed_by_user": True},
        },
    )
    write_yaml(
        root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml",
        {
            "schema_version": "0.1",
            "id": "REQ-20260702-001-TASK-20260702-001",
            "requirement_id": "REQ-20260702-001",
            "title": "生成索引",
            "created_at": "2026-07-01T09:30:00+08:00",
            "updated_at": "2026-07-01T10:00:00+08:00",
            "stage": "in_progress",
            "process_level": "standard",
            "risk_level": "standard",
            "impact_profile": {
                "action": "code_change",
                "component_signals": ["python"],
                "environment": "local",
                "data_effect": "none",
                "external_effect": "none",
                "blast_radius": "single_service",
                "reversibility": "git_revert",
                "contract_change": False,
                "security_or_permission": False,
                "verification_confidence": "local_testable",
            },
            "service_refs": ["codex-workbench"],
            "validation": {"status": "passed", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001"},
            "handoff": {"status": "waiting_user_validation"},
        },
    )
    write_yaml(
        root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "evidence.yaml",
        {
            "schema_version": "0.1",
            "id": "EV-REQ-20260702-001-TASK-20260702-001",
            "task_id": "REQ-20260702-001-TASK-20260702-001",
            "conclusion": "passed",
            "key_outputs": ["python -m pytest passed", "full evidence body must stay out"],
            "unverified_items": [],
        },
    )
    (root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "review.md").write_text(
        "# REQ-20260702-001-TASK-20260702-001 评审\n\n有评审内容。\n",
        encoding="utf-8",
    )
    (root / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "implementation.md").write_text(
        "# REQ-20260702-001-TASK-20260702-001 实现说明\n\n有实现内容。\n",
        encoding="utf-8",
    )
    write_yaml(
        root / "docs" / "inbox" / "materials.yaml",
        {
            "schema_version": "0.1",
            "materials": [
                {
                    "id": "MAT-001",
                    "title": "思想文件",
                    "source": "用户提供",
                    "received_at": "2026-07-01",
                    "summary": "生成视图边界。",
                    "sensitivity": "low",
                    "original_location": "D:/private/raw/philosophy.md",
                }
            ],
        },
    )
    write_yaml(
        root / "docs" / "inbox" / "DISC-001" / "discovery.yaml",
        {
            "schema_version": "0.1",
            "id": "DISC-001",
            "title": "发现",
            "material_refs": ["MAT-001"],
            "updated_at": "2026-07-01",
        },
    )
    write_yaml(
        root / "docs" / "actions" / "ACT-001.yaml",
        {
            "schema_version": "0.1",
            "id": "ACT-001",
            "title": "记录辅助动作",
            "updated_at": "2026-07-01",
            "summary": "动作摘要。",
            "action_type": "maintenance_action",
            "side_effect_summary": "no_side_effect",
            "rollback_hint": "no_rollback_needed",
        },
    )
    write_yaml(
        root / "docs" / "changes" / "CHG-001.yaml",
        {
            "schema_version": "0.1",
            "id": "CHG-001",
            "title": "记录范围变化",
            "updated_at": "2026-07-01",
            "change_kind": "scope_change",
            "changed_area": "acceptance",
            "reason": "验收口径变化。",
            "impact": "需要更新任务边界。",
            "handling": "先记录变更。",
        },
    )
    write_yaml(
        root / "docs" / "decisions" / "DEC-001.yaml",
        {
            "schema_version": "0.1",
            "id": "DEC-001",
            "title": "记录长期决策",
            "updated_at": "2026-07-01",
            "cold_path_reason": "影响后续任务。",
            "context": "统一口径。",
            "decision": "使用 generated view。",
            "impact": "后续复用。",
        },
    )
    write_yaml(
        root / "docs" / "suspicions" / "SUS-001.yaml",
        {
            "schema_version": "0.1",
            "id": "SUS-001",
            "title": "记录疑点",
            "updated_at": "2026-07-01",
            "location_or_subject": "src/demo.py",
            "confirmed_facts": ["发现不一致现象。"],
            "ai_inferences": ["需要后续复核。"],
            "current_task_impact": "不影响当前任务。",
            "suggested_handling": "后续单独评估。",
        },
    )


def test_generate_index_views_rebuilds_generated_outputs_without_source_writes(tmp_path: Path) -> None:
    create_full_index_fixture(tmp_path)
    source_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    before_source = source_yaml.read_text(encoding="utf-8")

    result = generate_index_views(tmp_path, dry_run=False)

    index_path = tmp_path / "docs" / "generated" / "index.md"
    recovery_path = tmp_path / "docs" / "generated" / "recovery.md"
    current_path = tmp_path / "CURRENT.md"
    index_text = index_path.read_text(encoding="utf-8")
    recovery_text = recovery_path.read_text(encoding="utf-8")
    current_text = current_path.read_text(encoding="utf-8")
    assert result.paths == (current_path, index_path, recovery_path)
    assert "# CURRENT" in current_text
    assert "| 最近更新 | 需求 | 任务 | 阶段 | 风险 | 影响面 | 缺口 | 包内容 | 验证 | 下一步 |" in current_text
    assert "REQ-20260702-001-TASK-20260702-001" in current_text
    assert "standard/standard" in current_text
    assert "code_change local data=none" in current_text
    assert "review, implementation, evidence" in current_text
    assert "generated view; YAML remains the source of truth" in index_text
    assert "| 需求 | 标题 | readiness | 任务数 | 最近更新 |" in index_text
    assert "| REQ-20260702-001 | 构建 Workbench | readable | 1 | 2026-07-01 |" in index_text
    assert "| 需求 | 任务 | 标题 | 阶段 | 风险 | 影响面 | 缺口 | 包内容 | 验证 | 最近更新 | 下一步 |" in index_text
    assert "| REQ-20260702-001 | REQ-20260702-001-TASK-20260702-001 | 生成索引 | in_progress | standard/standard | code_change local data=none external=none radius=single_service rollback=git_revert | none | review, implementation, evidence | passed | 2026-07-01T10:00:00+08:00 | - |" in index_text
    assert "`codex-workbench`" in index_text
    assert "ACT-001" in index_text
    assert "CHG-001" in index_text
    assert "DEC-001" in index_text
    assert "SUS-001" in index_text
    assert "## 续接队列" in recovery_text
    assert "REQ-20260702-001-TASK-20260702-001" in recovery_text
    assert "impact=code_change local data=none" in recovery_text
    assert "gaps=none" in recovery_text
    assert "full evidence body must stay out" not in recovery_text
    assert "D:/private/raw/philosophy.md" not in index_text
    assert source_yaml.read_text(encoding="utf-8") == before_source


def test_generate_index_views_dry_run_does_not_write_generated_files(tmp_path: Path) -> None:
    create_full_index_fixture(tmp_path)

    result = generate_index_views(tmp_path, dry_run=True)

    assert result.dry_run is True
    assert (tmp_path / "CURRENT.md").read_text(encoding="utf-8") == "# CURRENT\n"
    assert not (tmp_path / "docs" / "generated" / "index.md").exists()
    assert not (tmp_path / "docs" / "generated" / "recovery.md").exists()
    assert "REQ-20260702-001-TASK-20260702-001" in result.index_text
    assert "## 续接队列" in result.recovery_text


def test_generated_views_show_risk_gaps_without_expanding_profile(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_yaml(
        tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml",
        {
            "schema_version": "0.1",
            "id": "REQ-20260702-001",
            "title": "风险缺口需求",
            "goal": "展示风险缺口。",
            "created_at": "2026-07-01T09:00:00+08:00",
            "updated_at": "2026-07-01",
            "task_refs": ["REQ-20260702-001-TASK-20260702-001"],
            "readiness": {"status": "readable", "confirmed_by_user": True},
        },
    )
    write_yaml(
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml",
        {
            "schema_version": "0.1",
            "id": "REQ-20260702-001-TASK-20260702-001",
            "requirement_id": "REQ-20260702-001",
            "title": "缺少风险画像",
            "created_at": "2026-07-01T09:30:00+08:00",
            "updated_at": "2026-07-01T10:00:00+08:00",
            "stage": "ready",
            "process_level": "standard",
            "risk_level": "standard",
            "validation": {"status": "not_started"},
        },
    )

    result = generate_index_views(tmp_path, dry_run=True)

    assert "missing_impact_profile" in result.current_text
    assert "missing_impact_profile" in result.index_text
    assert "missing_impact_profile" in result.recovery_text
    assert "impact_profile:" not in result.index_text
    assert "component_signals" not in result.recovery_text


def test_deleted_generated_views_rebuild_byte_stable(tmp_path: Path) -> None:
    create_full_index_fixture(tmp_path)
    first = generate_index_views(tmp_path)
    first_index = first.index_text
    first_recovery = first.recovery_text
    (tmp_path / "docs" / "generated" / "index.md").unlink()
    (tmp_path / "docs" / "generated" / "recovery.md").unlink()

    rebuilt = generate_index_views(tmp_path)

    assert rebuilt.index_text == first_index
    assert rebuilt.recovery_text == first_recovery
    assert (tmp_path / "docs" / "generated" / "index.md").read_text(encoding="utf-8") == first_index
    assert (tmp_path / "docs" / "generated" / "recovery.md").read_text(encoding="utf-8") == first_recovery


def test_check_generated_views_reports_stale_without_rewriting(tmp_path: Path) -> None:
    create_full_index_fixture(tmp_path)
    generate_index_views(tmp_path)
    index_path = tmp_path / "docs" / "generated" / "index.md"
    index_path.write_text("stale generated view\n", encoding="utf-8")

    result = check_generated_views(tmp_path)

    assert result.clean is False
    assert result.status == "stale"
    assert "stale: docs/generated/index.md" in result.messages
    assert index_path.read_text(encoding="utf-8") == "stale generated view\n"


def test_conflict_report_is_returned_and_rendered_without_source_mutation(tmp_path: Path) -> None:
    create_full_index_fixture(tmp_path)
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    task["service_refs"] = ["missing-service"]
    task_yaml.write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False), encoding="utf-8")
    before_source = task_yaml.read_text(encoding="utf-8")

    result = generate_index_views(tmp_path)

    assert result.conflicts == ["unknown_service_ref: REQ-20260702-001-TASK-20260702-001 -> missing-service"]
    assert "unknown_service_ref: REQ-20260702-001-TASK-20260702-001 -> missing-service" in result.index_text
    assert task_yaml.read_text(encoding="utf-8") == before_source


def test_path_id_mismatch_is_reported_as_conflict(tmp_path: Path) -> None:
    create_full_index_fixture(tmp_path)
    task_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    task = yaml.safe_load(task_yaml.read_text(encoding="utf-8"))
    task["id"] = "REQ-20260702-001-TASK-20260702-999"
    task_yaml.write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = generate_index_views(tmp_path, dry_run=True)

    assert "task_id_mismatch: path=REQ-20260702-001-TASK-20260702-001 yaml=REQ-20260702-001-TASK-20260702-999" in result.conflicts


def test_task_requirement_mismatch_is_reported_as_conflict(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_yaml(
        tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml",
        {
            "schema_version": "0.1",
            "id": "REQ-20260702-001",
            "title": "需求一",
            "goal": "测试任务归属。",
            "acceptance": ["归属冲突可见。"],
            "task_refs": ["REQ-20260702-001-TASK-20260702-001"],
        },
    )
    write_yaml(
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml",
        {
            "schema_version": "0.1",
            "id": "REQ-20260702-001-TASK-20260702-001",
            "requirement_id": "REQ-OTHER",
            "title": "错绑任务",
            "stage": "draft",
            "validation": {"status": "not_started"},
        },
    )

    result = generate_index_views(tmp_path, dry_run=True)

    assert (
        "task_requirement_mismatch: REQ-20260702-001 -> REQ-20260702-001-TASK-20260702-001 requirement_id=REQ-OTHER"
        in result.conflicts
    )


def test_recovery_groups_active_tasks_by_requirement(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_yaml(
        tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml",
        {
            "schema_version": "0.1",
            "id": "REQ-20260702-001",
            "title": "需求一",
            "goal": "测试恢复分组。",
            "acceptance": ["分组可见。"],
            "task_refs": ["REQ-20260702-001-TASK-20260702-001"],
        },
    )
    write_yaml(
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml",
        {
            "schema_version": "0.1",
            "id": "REQ-20260702-001-TASK-20260702-001",
            "requirement_id": "REQ-20260702-001",
            "title": "实现恢复视图",
            "stage": "in_progress",
            "process_level": "standard",
            "risk_level": "high",
            "next_step": "继续增强 recovery。",
            "service_refs": ["codex-workbench"],
            "blocked": {
                "reason": "等待测试样例确认。",
                "blocked_by": "user",
                "resume_condition": "测试样例确认后继续。",
                "resume_stage": "ready",
            },
            "validation": {"status": "partial", "evidence_ref": "EV-REQ-20260702-001-TASK-20260702-001"},
        },
    )

    result = generate_index_views(tmp_path, dry_run=True)

    assert "## 续接队列" in result.recovery_text
    assert "- requirement `REQ-20260702-001` 需求一" in result.recovery_text
    assert "task `REQ-20260702-001-TASK-20260702-001` 实现恢复视图 [in_progress]" in result.recovery_text
    assert "risk=high/process=standard" in result.recovery_text
    assert "next=继续增强 recovery。" in result.recovery_text
    assert "blocked=等待测试样例确认。" in result.recovery_text
    assert "validation=partial evidence=EV-REQ-20260702-001-TASK-20260702-001" in result.recovery_text


def test_bad_yaml_is_reported_as_conflict_instead_of_raising(tmp_path: Path) -> None:
    create_full_index_fixture(tmp_path)
    bad_yaml = tmp_path / "docs" / "actions" / "BROKEN.yaml"
    bad_yaml.write_text("id: [broken\n", encoding="utf-8")

    result = generate_index_views(tmp_path, dry_run=True)

    assert any(message.startswith("invalid_yaml: docs/actions/BROKEN.yaml") for message in result.conflicts)


def test_recovery_view_is_bounded_and_uses_material_output_allowlist(tmp_path: Path) -> None:
    create_full_index_fixture(tmp_path)
    materials = yaml.safe_load((tmp_path / "docs" / "inbox" / "materials.yaml").read_text("utf-8"))
    materials["materials"][0]["summary"] = "summary with token=abc123 should be hidden"
    (tmp_path / "docs" / "inbox" / "materials.yaml").write_text(
        yaml.safe_dump(materials, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    extra_task_ids = [f"REQ-20260702-001-TASK-20260702-{index:03d}" for index in range(2, 12)]
    requirement_yaml = tmp_path / "docs" / "active" / "REQ-20260702-001" / "requirement.yaml"
    requirement = yaml.safe_load(requirement_yaml.read_text(encoding="utf-8"))
    requirement["task_refs"].extend(extra_task_ids)
    requirement_yaml.write_text(
        yaml.safe_dump(requirement, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    for index in range(2, 12):
        task_id = f"REQ-20260702-001-TASK-20260702-{index:03d}"
        write_yaml(
            tmp_path / "docs" / "active" / task_id / "task.yaml",
            {
                "schema_version": "0.1",
                "id": task_id,
                "requirement_id": "REQ-20260702-001",
                "title": f"任务 {index}",
                "stage": "in_progress",
                "process_level": "standard",
                "risk_level": "standard",
                "validation": {"status": "not_started"},
            },
        )

    result = generate_index_views(tmp_path, dry_run=True)

    assert len(result.recovery_text.splitlines()) <= 35
    assert "and 6 more active tasks" in result.recovery_text
    assert "token=abc123" not in result.index_text
    assert "[redacted]" in result.index_text


def test_generate_index_views_lists_archive_without_polluting_recovery(
    tmp_path: Path,
) -> None:
    create_workspace(tmp_path)
    write_yaml(
        tmp_path / "docs" / "archive" / "1.0.0" / "archive.yaml",
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
            "entries": [
                {
                    "schema_version": "0.1",
                    "id": "ARCHIVE-1.0.0-REQ-20260702-001",
                    "version": "1.0.0",
                    "source_kind": "requirement",
                    "source_id": "REQ-20260702-001",
                    "source_path": "docs/active/REQ-20260702-001",
                    "archive_path": "docs/archive/1.0.0/REQ-20260702-001",
                    "reason": "requirement_version_archive",
                    "archived_at": "2026-07-01",
                },
                {
                    "schema_version": "0.1",
                    "id": "ARCHIVE-1.0.0-REQ-20260702-001-TASK-20260702-001",
                    "version": "1.0.0",
                    "source_kind": "task",
                    "source_id": "REQ-20260702-001-TASK-20260702-001",
                    "source_path": "docs/active/REQ-20260702-001-TASK-20260702-001",
                    "archive_path": "docs/archive/1.0.0/REQ-20260702-001-TASK-20260702-001",
                    "reason": "requirement_task_version_archive",
                    "archived_at": "2026-07-01",
                },
            ],
        },
    )

    result = generate_index_views(tmp_path, dry_run=True)

    assert "## Archive" in result.index_text
    assert (
        "`1.0.0` archived_at=2026-07-01 requirements=REQ-20260702-001 entries=REQ-20260702-001, REQ-20260702-001-TASK-20260702-001"
        in result.index_text
    )
    assert "REQ-20260702-001" not in result.recovery_text
    assert "REQ-20260702-001-TASK-20260702-001" not in result.recovery_text


def test_generate_index_views_reports_invalid_archive_manifest(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    write_yaml(
        tmp_path / "docs" / "archive" / "1.0.0" / "archive.yaml",
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
    )

    result = generate_index_views(tmp_path, dry_run=True)

    assert "invalid_archive_manifest: docs/archive/1.0.0/archive.yaml" in result.conflicts
    assert "`1.0.0`" not in result.index_text
