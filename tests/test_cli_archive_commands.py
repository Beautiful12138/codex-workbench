from __future__ import annotations

from pathlib import Path

import yaml

from codex_workbench.cli import app
from tests.cli_test_support import (
    combined_output,
    create_workspace,
    runner,
)


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
