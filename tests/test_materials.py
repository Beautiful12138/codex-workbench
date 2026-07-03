from __future__ import annotations

from pathlib import Path

import pytest

import codex_workbench.materials as materials_module
from codex_workbench.errors import ErrorCode, WorkbenchError
from codex_workbench.io import read_yaml_with_version, write_yaml_atomic
from codex_workbench.materials import add_material, read_material_registry


def create_workspace(root: Path) -> None:
    (root / "services").mkdir()
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CURRENT.md").write_text("# CURRENT\n", encoding="utf-8")
    (root / "services" / "registry.yaml").write_text(
        "schema_version: '0.1'\nservices: []\n",
        encoding="utf-8",
    )
    (root / "docs" / "inbox").mkdir(parents=True)
    write_yaml_atomic(root / "docs" / "inbox" / "materials.yaml", {"schema_version": "0.1", "materials": []})


def test_add_material_rejects_stale_materials_registry_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_workspace(tmp_path)
    materials_path = tmp_path / "docs" / "inbox" / "materials.yaml"
    stale_snapshot = read_yaml_with_version(materials_path)
    write_yaml_atomic(
        materials_path,
        {
            "schema_version": "0.1",
            "materials": [
                {
                    "id": "MAT-001",
                    "title": "已有材料",
                    "source": "user",
                    "received_at": "2026-07-01",
                    "summary": "另一个会话写入。",
                }
            ],
        },
    )

    def read_stale_snapshot(path: Path):
        if path == materials_path:
            return stale_snapshot
        return read_yaml_with_version(path)

    monkeypatch.setattr(materials_module, "read_yaml_with_version", read_stale_snapshot)

    with pytest.raises(WorkbenchError) as exc_info:
        add_material(
            tmp_path,
            material_id="MAT-002",
            title="新材料",
            source="user",
            summary="基于旧快照写入。",
            received_at="2026-07-01",
        )

    assert exc_info.value.code is ErrorCode.CONCURRENT_UPDATE
    registry = read_material_registry(tmp_path)
    assert [material.id for material in registry.materials] == ["MAT-001"]
