from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pathspec import GitIgnoreSpec

from .errors import ErrorCode, WorkbenchError
from .io import read_yaml, read_yaml_with_version, write_yaml_atomic
from .models import ServiceEntry, ServiceRegistry
from .workspace import resolve_workspace_path


DEFAULT_IGNORE_PATTERNS = (
    ".git/",
    ".venv/",
    "venv/",
    "__pycache__/",
    "node_modules/",
)
VISIBLE_FILE_COUNT_LIMIT = 200
HARD_SERVICE_GAPS = {
    "path_missing",
    "empty_service_dir",
    "service_path_is_file",
}


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
    path_state: str = "missing"
    branch: str | None = None
    head: str | None = None
    git_root: Path | None = None
    service_relpath: str | None = None
    git_status_scope: str | None = None
    git_error: str | None = None
    dirty_count: int = 0
    untracked_count: int = 0
    visible_file_count: int = 0
    visible_file_count_limit_reached: bool = False


@dataclass(frozen=True)
class ServiceContext:
    name: str
    registry_state: str
    raw_path: str | None
    purpose: str | None
    notes: str | None
    resolved_path: Path | None
    path_state: str
    visible_file_count: int
    git_state: str
    git_root: Path | None = None
    service_relpath: str | None = None
    git_status_scope: str | None = None
    git_error: str | None = None
    branch: str | None = None
    head: str | None = None
    dirty_count: int = 0
    untracked_count: int = 0
    entry_candidates: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    visible_file_count_limit_reached: bool = False

    @property
    def hard_gaps(self) -> tuple[str, ...]:
        return tuple(gap for gap in self.gaps if gap in HARD_SERVICE_GAPS)

    @property
    def warnings(self) -> tuple[str, ...]:
        hard_gaps = set(self.hard_gaps)
        return tuple(gap for gap in self.gaps if gap not in hard_gaps)


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
    snapshot = read_yaml_with_version(registry_path)
    registry = ServiceRegistry.model_validate(snapshot.data)
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
        expected_version=snapshot.version,
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
    visible_file_count_limit_reached = visible_file_count >= VISIBLE_FILE_COUNT_LIMIT
    path_state = _path_state(path, visible_file_count)
    if path_state == "file":
        return ServiceStatus(
            name=name,
            path=path,
            exists=True,
            git_state="not_git",
            path_state=path_state,
            visible_file_count=visible_file_count,
            visible_file_count_limit_reached=visible_file_count_limit_reached,
        )
    runner = run_command or _run_command
    inside = runner(["git", "rev-parse", "--is-inside-work-tree"], path)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return ServiceStatus(
            name=name,
            path=path,
            exists=True,
            git_state="not_git",
            path_state=path_state,
            visible_file_count=visible_file_count,
            visible_file_count_limit_reached=visible_file_count_limit_reached,
        )

    git_root_result = runner(["git", "rev-parse", "--show-toplevel"], path)
    if git_root_result.returncode != 0 or not git_root_result.stdout.strip():
        return ServiceStatus(
            name=name,
            path=path,
            exists=True,
            git_state="git_error",
            path_state=path_state,
            git_error="git_root_unresolved",
            visible_file_count=visible_file_count,
            visible_file_count_limit_reached=visible_file_count_limit_reached,
        )

    git_root = Path(git_root_result.stdout.strip()).expanduser().resolve()
    service_relpath = _service_relpath(path, git_root)
    if service_relpath is None:
        return ServiceStatus(
            name=name,
            path=path,
            exists=True,
            git_state="git_error",
            path_state=path_state,
            git_root=git_root,
            git_error="service_relpath_unresolved",
            visible_file_count=visible_file_count,
            visible_file_count_limit_reached=visible_file_count_limit_reached,
        )
    branch = runner(["git", "rev-parse", "--abbrev-ref", "HEAD"], git_root)
    head = runner(["git", "rev-parse", "--short", "HEAD"], git_root)
    status_args = ["git", "--no-optional-locks", "status", "--porcelain=v1"]
    status_cwd = git_root
    git_status_scope = "worktree"
    if service_relpath is not None:
        status_args.extend(["--", service_relpath])
        git_status_scope = "service_path"
    status = runner(status_args, status_cwd)
    if status.returncode != 0:
        return ServiceStatus(
            name=name,
            path=path,
            exists=True,
            git_state="git_error",
            path_state=path_state,
            branch=branch.stdout.strip() or None,
            head=head.stdout.strip() or None,
            git_root=git_root,
            service_relpath=service_relpath,
            git_status_scope=git_status_scope,
            git_error="git_status_failed",
            visible_file_count=visible_file_count,
            visible_file_count_limit_reached=visible_file_count_limit_reached,
        )
    dirty_count, untracked_count = _count_porcelain_status(status.stdout)
    return ServiceStatus(
        name=name,
        path=path,
        exists=True,
        git_state="git",
        path_state=path_state,
        branch=branch.stdout.strip() or None,
        head=head.stdout.strip() or None,
        git_root=git_root,
        service_relpath=service_relpath,
        git_status_scope=git_status_scope,
        dirty_count=dirty_count,
        untracked_count=untracked_count,
        visible_file_count=visible_file_count,
        visible_file_count_limit_reached=visible_file_count_limit_reached,
    )


def service_context(
    workspace_root: str | Path,
    name: str,
    *,
    run_command: RunCommand | None = None,
) -> ServiceContext:
    registry = read_service_registry(workspace_root)
    entry = _find_service(registry, name)
    status = service_status(workspace_root, name, run_command=run_command)
    entry_candidates = _entry_candidates(status.path) if status.path and status.exists else ()
    gaps = _service_context_gaps(status, entry_candidates)
    return ServiceContext(
        name=name,
        registry_state="registered",
        raw_path=entry.local_path,
        purpose=entry.purpose,
        notes=entry.notes,
        resolved_path=status.path,
        path_state=status.path_state,
        visible_file_count=status.visible_file_count,
        git_state=status.git_state,
        git_root=status.git_root,
        service_relpath=status.service_relpath,
        git_status_scope=status.git_status_scope,
        git_error=status.git_error,
        branch=status.branch,
        head=status.head,
        dirty_count=status.dirty_count,
        untracked_count=status.untracked_count,
        entry_candidates=entry_candidates,
        gaps=gaps,
        visible_file_count_limit_reached=status.visible_file_count_limit_reached,
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
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            children = current.iterdir()
        except OSError:
            continue
        for item in children:
            relative = item.relative_to(path).as_posix()
            if item.is_dir():
                if _is_linked_directory(item) or spec.match_file(f"{relative}/") or spec.match_file(relative):
                    continue
                stack.append(item)
                continue
            if not item.is_file() or spec.match_file(relative):
                continue
            count += 1
            if count >= VISIBLE_FILE_COUNT_LIMIT:
                return VISIBLE_FILE_COUNT_LIMIT
    return count


def _is_linked_directory(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _path_state(path: Path, visible_file_count: int) -> str:
    if not path.exists():
        return "missing"
    if path.is_file():
        return "file"
    if visible_file_count == 0:
        return "empty_dir"
    return "non_empty_dir"


def _service_relpath(path: Path, git_root: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(git_root.resolve())
    except ValueError:
        return None
    value = relative.as_posix()
    return value or "."


def _entry_candidates(path: Path | None) -> tuple[str, ...]:
    if path is None or not path.exists() or not path.is_dir():
        return ()
    candidates = (
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "gradlew",
        "go.mod",
        "Cargo.toml",
        "Makefile",
        "Dockerfile",
        "*.sln",
        "package.json",
        "pnpm-lock.yaml",
        "pyproject.toml",
        "requirements.txt",
        "src/",
        "tests/",
        "test/",
        "README.md",
    )
    found: list[str] = []
    for candidate in candidates:
        if "*" in candidate:
            if any(path.glob(candidate)):
                found.append(candidate)
            continue
        target = path / candidate.rstrip("/")
        if target.exists():
            found.append(candidate)
    return tuple(found)


def _service_context_gaps(status: ServiceStatus, entry_candidates: tuple[str, ...]) -> tuple[str, ...]:
    gaps: list[str] = []
    if not status.exists:
        gaps.append("path_missing")
    elif status.path_state == "empty_dir":
        gaps.append("empty_service_dir")
    elif status.path_state == "file":
        gaps.append("service_path_is_file")
    if status.git_state == "not_git":
        gaps.append("not_git")
    elif status.git_state == "git_error":
        gaps.append(status.git_error or "git_error")
    if status.exists and status.path_state != "file" and not entry_candidates:
        gaps.append("no_entry_candidates")
    return tuple(gaps)


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
