from __future__ import annotations

from pathlib import Path

import yaml

from codex_workbench.models import ServiceRegistry
from codex_workbench.services import (
    CommandResult,
    add_service,
    read_service_registry,
    service_status,
)


def create_workspace(root: Path) -> None:
    (root / "services").mkdir()
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "CURRENT.md").write_text("# CURRENT\n", encoding="utf-8")
    (root / "services" / "registry.yaml").write_text(
        "schema_version: '0.1'\nservices: []\n",
        encoding="utf-8",
    )


def test_add_service_writes_schema_valid_registry(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)

    result = add_service(
        tmp_path,
        name="api",
        local_path=service_path,
        purpose="主服务",
        notes="只读状态检查目标",
    )

    registry_path = tmp_path / "services" / "registry.yaml"
    registry = ServiceRegistry.model_validate(yaml.safe_load(registry_path.read_text(encoding="utf-8")))

    assert result.path == registry_path
    assert result.dry_run is False
    assert registry.services[0].name == "api"
    assert registry.services[0].local_path == str(service_path)


def test_add_service_dry_run_does_not_write_registry(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)

    result = add_service(tmp_path, name="api", local_path=service_path, dry_run=True)
    registry = read_service_registry(tmp_path)

    assert result.dry_run is True
    assert registry.services == []


def test_service_status_reports_missing_and_non_git_paths(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    non_git_path = tmp_path / "repos" / "plain"
    non_git_path.mkdir(parents=True)
    add_service(tmp_path, name="plain", local_path=non_git_path)
    add_service(tmp_path, name="missing", local_path=tmp_path / "repos" / "missing")

    plain_status = service_status(tmp_path, "plain")
    missing_status = service_status(tmp_path, "missing")

    assert plain_status.exists is True
    assert plain_status.git_state == "not_git"
    assert missing_status.exists is False
    assert missing_status.git_state == "missing"


def test_service_status_uses_pathspec_ignores_for_file_count(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "plain"
    service_path.mkdir(parents=True)
    (service_path / ".gitignore").write_text("node_modules/\n*.pyc\n", encoding="utf-8")
    (service_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (service_path / "node_modules").mkdir()
    (service_path / "node_modules" / "large.js").write_text("ignored\n", encoding="utf-8")
    (service_path / "cached.pyc").write_text("ignored\n", encoding="utf-8")
    add_service(tmp_path, name="plain", local_path=service_path)

    status = service_status(tmp_path, "plain")

    assert status.visible_file_count == 2


def test_git_status_uses_only_read_only_commands(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "repo"
    service_path.mkdir(parents=True)
    add_service(tmp_path, name="repo", local_path=service_path)
    commands: list[tuple[str, ...]] = []

    def fake_runner(args: list[str], cwd: Path) -> CommandResult:
        commands.append(tuple(args))
        assert cwd == service_path
        if args == ["git", "rev-parse", "--is-inside-work-tree"]:
            return CommandResult(returncode=0, stdout="true\n", stderr="")
        if args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return CommandResult(returncode=0, stdout="main\n", stderr="")
        if args == ["git", "rev-parse", "--short", "HEAD"]:
            return CommandResult(returncode=0, stdout="abc1234\n", stderr="")
        if args == ["git", "--no-optional-locks", "status", "--porcelain=v1"]:
            return CommandResult(returncode=0, stdout=" M src/app.py\n?? notes.md\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")

    status = service_status(tmp_path, "repo", run_command=fake_runner)

    forbidden = {"clone", "checkout", "switch", "commit", "push", "worktree"}
    assert status.git_state == "git"
    assert status.branch == "main"
    assert status.head == "abc1234"
    assert status.dirty_count == 1
    assert status.untracked_count == 1
    assert ("git", "--no-optional-locks", "status", "--porcelain=v1") in commands
    assert all(forbidden.isdisjoint(command) for command in commands)
