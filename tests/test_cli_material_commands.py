from __future__ import annotations

from pathlib import Path

import yaml

from codex_workbench.cli import app
from tests.cli_test_support import (
    combined_output,
    create_workspace,
    runner,
    write_requirement,
)


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
    assert (
        tmp_path / "docs" / "active" / "REQ-20260702-001-TASK-20260702-001" / "task.yaml"
    ).exists()


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
