from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pathspec import GitIgnoreSpec

from .errors import ErrorCode, WorkbenchError
from .io import read_yaml, write_yaml_atomic
from .models import ServiceEntry, ServiceRegistry
from .workspace import resolve_workspace_path


DEFAULT_IGNORE_PATTERNS = (
    ".git/",
    ".venv/",
    "venv/",
    "__pycache__/",
    "node_modules/",
)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    path: Path | None
    exists: bool
    git_state: str
    branch: str | None = None
    head: str | None = None
    dirty_count: int = 0
    untracked_count: int = 0
    visible_file_count: int = 0


RunCommand = Callable[[list[str], Path], CommandResult]


def read_service_registry(workspace_root: str | Path) -> ServiceRegistry:
    return ServiceRegistry.model_validate(read_yaml(_registry_path(workspace_root)))


def add_service(
    workspace_root: str | Path,
    *,
    name: str,
    local_path: str | Path,
    purpose: str | None = None,
    notes: str | None = None,
    dry_run: bool = False,
):
    registry_path = _registry_path(workspace_root)
    registry = read_service_registry(workspace_root)
    _ensure_unique_service_name(registry, name)

    entry = ServiceEntry(
        name=name,
        local_path=str(Path(local_path)),
        purpose=purpose,
        notes=notes,
    )
    services = list(registry.services)
    services.append(entry)

    updated = ServiceRegistry(
        schema_version=registry.schema_version,
        services=services,
        notes=registry.notes,
    )
    return write_yaml_atomic(
        registry_path,
        updated.model_dump(mode="json", exclude_none=True),
        dry_run=dry_run,
    )


def service_status(
    workspace_root: str | Path,
    name: str,
    *,
    run_command: RunCommand | None = None,
) -> ServiceStatus:
    registry = read_service_registry(workspace_root)
    entry = _find_service(registry, name)
    path = _service_path(workspace_root, entry)
    if path is None or not path.exists():
        return ServiceStatus(name=name, path=path, exists=False, git_state="missing")

    visible_file_count = _visible_file_count(path)
    runner = run_command or _run_command
    inside = runner(["git", "rev-parse", "--is-inside-work-tree"], path)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return ServiceStatus(
            name=name,
            path=path,
            exists=True,
            git_state="not_git",
            visible_file_count=visible_file_count,
        )

    branch = runner(["git", "rev-parse", "--abbrev-ref", "HEAD"], path)
    head = runner(["git", "rev-parse", "--short", "HEAD"], path)
    status = runner(["git", "--no-optional-locks", "status", "--porcelain=v1"], path)
    dirty_count, untracked_count = _count_porcelain_status(status.stdout)
    return ServiceStatus(
        name=name,
        path=path,
        exists=True,
        git_state="git",
        branch=branch.stdout.strip() or None,
        head=head.stdout.strip() or None,
        dirty_count=dirty_count,
        untracked_count=untracked_count,
        visible_file_count=visible_file_count,
    )


def _registry_path(workspace_root: str | Path) -> Path:
    return resolve_workspace_path(workspace_root, "services/registry.yaml")


def _ensure_unique_service_name(registry: ServiceRegistry, name: str) -> None:
    existing = {entry.name for entry in registry.services}
    if name in existing:
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"service_already_exists: {name}",
            exit_code=2,
        )


def _find_service(registry: ServiceRegistry, name: str) -> ServiceEntry:
    for entry in registry.services:
        if entry.name == name:
            return entry
    raise WorkbenchError(
        ErrorCode.VALIDATION_ERROR,
        f"unknown_service: {name}",
        exit_code=2,
    )


def _service_path(workspace_root: str | Path, entry: ServiceEntry) -> Path | None:
    if not entry.local_path:
        return None
    raw_path = Path(entry.local_path).expanduser()
    if raw_path.is_absolute():
        return raw_path.resolve()
    return (Path(workspace_root).expanduser().resolve() / raw_path).resolve()


def _visible_file_count(path: Path) -> int:
    if not path.is_dir():
        return 1
    spec = GitIgnoreSpec.from_lines(_ignore_patterns(path))
    count = 0
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(path).as_posix()
        if spec.match_file(relative):
            continue
        count += 1
    return count


def _ignore_patterns(path: Path) -> list[str]:
    patterns = list(DEFAULT_IGNORE_PATTERNS)
    gitignore = path / ".gitignore"
    if gitignore.exists():
        patterns.extend(gitignore.read_text(encoding="utf-8").splitlines())
    return patterns


def _run_command(args: list[str], cwd: Path) -> CommandResult:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _count_porcelain_status(output: str) -> tuple[int, int]:
    dirty_count = 0
    untracked_count = 0
    for line in output.splitlines():
        if line.startswith("??"):
            untracked_count += 1
        elif line.strip():
            dirty_count += 1
    return dirty_count, untracked_count
