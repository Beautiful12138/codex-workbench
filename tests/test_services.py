from __future__ import annotations

from pathlib import Path

import yaml

import codex_workbench.services as services_module
import pytest
from codex_workbench.errors import ErrorCode, WorkbenchError
from codex_workbench.io import read_yaml_with_version, write_yaml_atomic
from codex_workbench.models import ServiceRegistry
from codex_workbench.services import (
    CommandResult,
    add_service,
    delete_service,
    read_service_registry,
    service_context,
    service_status,
    update_service,
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


def test_add_service_rejects_stale_registry_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_workspace(tmp_path)
    registry_path = tmp_path / "services" / "registry.yaml"
    stale_snapshot = read_yaml_with_version(registry_path)
    write_yaml_atomic(
        registry_path,
        {
            "schema_version": "0.1",
            "services": [{"name": "api", "local_path": str(tmp_path / "repos" / "api")}],
        },
    )

    def read_stale_snapshot(path: Path):
        if path == registry_path:
            return stale_snapshot
        return read_yaml_with_version(path)

    monkeypatch.setattr(services_module, "read_yaml_with_version", read_stale_snapshot)

    with pytest.raises(WorkbenchError) as exc_info:
        add_service(tmp_path, name="web", local_path=tmp_path / "repos" / "web")

    assert exc_info.value.code is ErrorCode.CONCURRENT_UPDATE
    registry = read_service_registry(tmp_path)
    assert [service.name for service in registry.services] == ["api"]


def test_update_service_changes_only_supplied_fields(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    old_path = tmp_path / "repos" / "api"
    new_path = tmp_path / "repos" / "api-v2"
    old_path.mkdir(parents=True)
    new_path.mkdir(parents=True)
    add_service(tmp_path, name="api", local_path=old_path, purpose="旧用途", notes="旧备注")

    result = update_service(
        tmp_path,
        name="api",
        local_path=new_path,
        purpose="新用途",
    )
    registry = read_service_registry(tmp_path)

    assert result.dry_run is False
    assert registry.services[0].name == "api"
    assert registry.services[0].local_path == str(new_path)
    assert registry.services[0].purpose == "新用途"
    assert registry.services[0].notes == "旧备注"


def test_update_service_dry_run_does_not_write_registry(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)
    add_service(tmp_path, name="api", local_path=service_path, purpose="旧用途")

    result = update_service(tmp_path, name="api", purpose="新用途", dry_run=True)
    registry = read_service_registry(tmp_path)

    assert result.dry_run is True
    assert registry.services[0].purpose == "旧用途"


def test_delete_service_removes_only_target_service(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    api_path = tmp_path / "repos" / "api"
    web_path = tmp_path / "repos" / "web"
    api_path.mkdir(parents=True)
    web_path.mkdir(parents=True)
    add_service(tmp_path, name="api", local_path=api_path)
    add_service(tmp_path, name="web", local_path=web_path)

    result = delete_service(tmp_path, name="api")
    registry = read_service_registry(tmp_path)

    assert result.dry_run is False
    assert [service.name for service in registry.services] == ["web"]


def test_delete_service_dry_run_does_not_write_registry(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)
    add_service(tmp_path, name="api", local_path=service_path)

    result = delete_service(tmp_path, name="api", dry_run=True)
    registry = read_service_registry(tmp_path)

    assert result.dry_run is True
    assert [service.name for service in registry.services] == ["api"]


def test_service_status_reports_missing_and_non_git_paths(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    non_git_path = tmp_path / "repos" / "plain"
    non_git_path.mkdir(parents=True)
    add_service(tmp_path, name="plain", local_path=non_git_path)
    add_service(tmp_path, name="missing", local_path=tmp_path / "repos" / "missing")

    plain_status = service_status(tmp_path, "plain")
    missing_status = service_status(tmp_path, "missing")
    missing_context = service_context(tmp_path, "missing")

    assert plain_status.exists is True
    assert plain_status.git_state == "not_git"
    assert missing_status.exists is False
    assert missing_status.git_state == "missing"
    assert missing_context.gaps == ("path_missing",)
    assert missing_context.hard_gaps == ("path_missing",)
    assert missing_context.warnings == ()


def test_service_status_uses_pathspec_ignores_for_file_count(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "plain"
    service_path.mkdir(parents=True)
    (service_path / ".gitignore").write_text("node_modules/\n*.pyc\n", encoding="utf-8")
    (service_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (service_path / "node_modules").mkdir()
    (service_path / "node_modules" / "large.js").write_text("ignored\n", encoding="utf-8")
    (service_path / ".venv").mkdir()
    (service_path / ".venv" / "python.exe").write_text("ignored\n", encoding="utf-8")
    (service_path / "venv").mkdir()
    (service_path / "venv" / "python.exe").write_text("ignored\n", encoding="utf-8")
    (service_path / "__pycache__").mkdir()
    (service_path / "__pycache__" / "app.pyc").write_text("ignored\n", encoding="utf-8")
    (service_path / "cached.pyc").write_text("ignored\n", encoding="utf-8")
    add_service(tmp_path, name="plain", local_path=service_path)

    status = service_status(tmp_path, "plain")

    assert status.visible_file_count == 2


def test_service_status_caps_visible_file_count_for_large_service_tree(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "large"
    service_path.mkdir(parents=True)
    for index in range(250):
        (service_path / f"file-{index}.txt").write_text("visible\n", encoding="utf-8")
    add_service(tmp_path, name="large", local_path=service_path)

    status = service_status(tmp_path, "large")

    assert status.visible_file_count == 200
    assert status.visible_file_count_limit_reached is True
    assert status.path_state == "non_empty_dir"


def test_git_status_uses_only_read_only_commands(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "repo"
    service_path.mkdir(parents=True)
    add_service(tmp_path, name="repo", local_path=service_path)
    commands: list[tuple[str, ...]] = []

    def fake_runner(args: list[str], cwd: Path) -> CommandResult:
        commands.append(tuple(args))
        if args == ["git", "rev-parse", "--is-inside-work-tree"]:
            assert cwd == service_path
            return CommandResult(returncode=0, stdout="true\n", stderr="")
        if args == ["git", "rev-parse", "--show-toplevel"]:
            assert cwd == service_path
            return CommandResult(returncode=0, stdout=f"{service_path}\n", stderr="")
        if args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            assert cwd == service_path
            return CommandResult(returncode=0, stdout="main\n", stderr="")
        if args == ["git", "rev-parse", "--short", "HEAD"]:
            assert cwd == service_path
            return CommandResult(returncode=0, stdout="abc1234\n", stderr="")
        if args == ["git", "--no-optional-locks", "status", "--porcelain=v1", "--", "."]:
            assert cwd == service_path
            return CommandResult(returncode=0, stdout=" M src/app.py\n?? notes.md\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")

    status = service_status(tmp_path, "repo", run_command=fake_runner)

    forbidden = {"clone", "checkout", "switch", "commit", "push", "worktree"}
    assert status.git_state == "git"
    assert status.branch == "main"
    assert status.head == "abc1234"
    assert status.git_root == service_path
    assert status.service_relpath == "."
    assert status.git_status_scope == "service_path"
    assert status.dirty_count == 1
    assert status.untracked_count == 1
    assert ("git", "--no-optional-locks", "status", "--porcelain=v1", "--", ".") in commands
    assert all(forbidden.isdisjoint(command) for command in commands)


def test_git_status_is_scoped_to_service_subdirectory(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    repo_root = tmp_path / "repos" / "mono"
    service_path = repo_root / "services" / "api"
    service_path.mkdir(parents=True)
    add_service(tmp_path, name="api", local_path=service_path)
    commands: list[tuple[tuple[str, ...], Path]] = []

    def fake_runner(args: list[str], cwd: Path) -> CommandResult:
        commands.append((tuple(args), cwd))
        if args == ["git", "rev-parse", "--is-inside-work-tree"]:
            assert cwd == service_path
            return CommandResult(returncode=0, stdout="true\n", stderr="")
        if args == ["git", "rev-parse", "--show-toplevel"]:
            assert cwd == service_path
            return CommandResult(returncode=0, stdout=f"{repo_root}\n", stderr="")
        if args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            assert cwd == repo_root
            return CommandResult(returncode=0, stdout="main\n", stderr="")
        if args == ["git", "rev-parse", "--short", "HEAD"]:
            assert cwd == repo_root
            return CommandResult(returncode=0, stdout="abc1234\n", stderr="")
        if args == [
            "git",
            "--no-optional-locks",
            "status",
            "--porcelain=v1",
            "--",
            "services/api",
        ]:
            assert cwd == repo_root
            return CommandResult(returncode=0, stdout=" M services/api/app.py\n?? services/api/new.py\n", stderr="")
        raise AssertionError(f"unexpected command: {args} cwd={cwd}")

    status = service_status(tmp_path, "api", run_command=fake_runner)

    assert status.git_state == "git"
    assert status.git_root == repo_root
    assert status.service_relpath == "services/api"
    assert status.git_status_scope == "service_path"
    assert status.dirty_count == 1
    assert status.untracked_count == 1
    assert (
        (
            "git",
            "--no-optional-locks",
            "status",
            "--porcelain=v1",
            "--",
            "services/api",
        ),
        repo_root,
    ) in commands


def test_git_status_failure_reports_git_error_instead_of_clean_status(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)
    add_service(tmp_path, name="api", local_path=service_path)

    def fake_runner(args: list[str], cwd: Path) -> CommandResult:
        if args == ["git", "rev-parse", "--is-inside-work-tree"]:
            return CommandResult(returncode=0, stdout="true\n", stderr="")
        if args == ["git", "rev-parse", "--show-toplevel"]:
            return CommandResult(returncode=0, stdout=f"{service_path}\n", stderr="")
        if args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return CommandResult(returncode=0, stdout="main\n", stderr="")
        if args == ["git", "rev-parse", "--short", "HEAD"]:
            return CommandResult(returncode=0, stdout="abc1234\n", stderr="")
        if args == ["git", "--no-optional-locks", "status", "--porcelain=v1", "--", "."]:
            return CommandResult(returncode=128, stdout="", stderr="fatal: status failed")
        raise AssertionError(f"unexpected command: {args} cwd={cwd}")

    status = service_status(tmp_path, "api", run_command=fake_runner)
    context = service_context(tmp_path, "api", run_command=fake_runner)

    assert status.git_state == "git_error"
    assert status.git_error == "git_status_failed"
    assert status.dirty_count == 0
    assert status.untracked_count == 0
    assert "git_status_failed" in context.gaps


def test_unresolved_service_relpath_does_not_fall_back_to_worktree_status(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_path = tmp_path / "repos" / "api"
    service_path.mkdir(parents=True)
    add_service(tmp_path, name="api", local_path=service_path)
    commands: list[tuple[str, ...]] = []

    def fake_runner(args: list[str], cwd: Path) -> CommandResult:
        commands.append(tuple(args))
        if args == ["git", "rev-parse", "--is-inside-work-tree"]:
            return CommandResult(returncode=0, stdout="true\n", stderr="")
        if args == ["git", "rev-parse", "--show-toplevel"]:
            return CommandResult(returncode=0, stdout=f"{tmp_path / 'other-root'}\n", stderr="")
        raise AssertionError(f"unexpected command: {args} cwd={cwd}")

    status = service_status(tmp_path, "api", run_command=fake_runner)
    context = service_context(tmp_path, "api", run_command=fake_runner)

    assert status.git_state == "git_error"
    assert status.git_error == "service_relpath_unresolved"
    assert ("git", "--no-optional-locks", "status", "--porcelain=v1") not in commands
    assert "service_relpath_unresolved" in context.gaps


def test_file_service_path_does_not_run_git_with_file_cwd(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    service_file = tmp_path / "repos" / "service.txt"
    service_file.parent.mkdir(parents=True)
    service_file.write_text("not a service directory\n", encoding="utf-8")
    add_service(tmp_path, name="file-service", local_path=service_file)

    def fail_runner(args: list[str], cwd: Path) -> CommandResult:
        raise AssertionError(f"git should not run for file service paths: {args} cwd={cwd}")

    status = service_status(tmp_path, "file-service", run_command=fail_runner)
    context = service_context(tmp_path, "file-service", run_command=fail_runner)

    assert status.exists is True
    assert status.path_state == "file"
    assert status.git_state == "not_git"
    assert "service_path_is_file" in context.gaps


def test_service_context_reports_path_state_entry_candidates_and_gaps(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    empty_path = tmp_path / "repos" / "empty"
    node_path = tmp_path / "repos" / "web"
    empty_path.mkdir(parents=True)
    node_path.mkdir(parents=True)
    (node_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    (node_path / "src").mkdir()
    add_service(tmp_path, name="empty", local_path=empty_path)
    add_service(tmp_path, name="web", local_path=node_path)

    empty_context = service_context(tmp_path, "empty")
    web_context = service_context(tmp_path, "web")

    assert empty_context.registry_state == "registered"
    assert empty_context.path_state == "empty_dir"
    assert empty_context.gaps == ("empty_service_dir", "not_git", "no_entry_candidates")
    assert empty_context.hard_gaps == ("empty_service_dir",)
    assert empty_context.warnings == ("not_git", "no_entry_candidates")
    assert web_context.path_state == "non_empty_dir"
    assert "package.json" in web_context.entry_candidates
    assert "src/" in web_context.entry_candidates
    assert "no_entry_candidates" not in web_context.gaps
    assert web_context.hard_gaps == ()
    assert web_context.warnings == ("not_git",)
