from __future__ import annotations

import os
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from .errors import ErrorCode, WorkbenchError


@dataclass(frozen=True)
class WriteResult:
    path: Path
    dry_run: bool
    changed: bool


@dataclass(frozen=True)
class VersionedText:
    path: Path
    content: str
    version: str


@dataclass(frozen=True)
class VersionedYaml:
    path: Path
    data: Any
    version: str


def read_text_utf8(path: str | Path) -> str:
    target = Path(path)
    try:
        return target.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkbenchError(
            ErrorCode.IO_ERROR,
            f"读取 UTF-8 文件失败：{target}",
            exit_code=1,
        ) from exc


def read_text_with_version(path: str | Path) -> VersionedText:
    target = Path(path)
    try:
        raw = target.read_bytes()
        return VersionedText(path=target, content=raw.decode("utf-8"), version=_content_version(raw))
    except UnicodeDecodeError as exc:
        raise WorkbenchError(
            ErrorCode.PARSE_ERROR,
            f"UTF-8 解码失败：{target}",
            exit_code=2,
        ) from exc
    except OSError as exc:
        raise WorkbenchError(
            ErrorCode.IO_ERROR,
            f"读取 UTF-8 文件失败：{target}",
            exit_code=1,
        ) from exc


def write_text_utf8_atomic(
    path: str | Path,
    content: str,
    *,
    dry_run: bool = False,
    expected_version: str | None = None,
    create_only: bool = False,
) -> WriteResult:
    target = Path(path)
    if dry_run:
        return WriteResult(path=target, dry_run=True, changed=False)

    temp_path: Path | None = None

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with _target_write_lock(target):
            _assert_write_precondition(target, expected_version=expected_version, create_only=create_only)
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{target.name}.",
                suffix=".tmp",
                dir=str(target.parent),
                text=True,
            )
            temp_path = Path(temp_name)
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
            os.replace(temp_path, target)
    except OSError as exc:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
        raise WorkbenchError(
            ErrorCode.IO_ERROR,
            f"原子写入文件失败：{target}",
            exit_code=1,
        ) from exc

    return WriteResult(path=target, dry_run=False, changed=True)


def read_yaml(path: str | Path) -> Any:
    target = Path(path)
    try:
        with target.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise WorkbenchError(
            ErrorCode.PARSE_ERROR,
            f"YAML 解析失败：{target}",
            exit_code=2,
        ) from exc
    except OSError as exc:
        raise WorkbenchError(
            ErrorCode.IO_ERROR,
            f"读取 YAML 文件失败：{target}",
            exit_code=1,
        ) from exc
    return {} if data is None else data


def read_yaml_with_version(path: str | Path) -> VersionedYaml:
    snapshot = read_text_with_version(path)
    try:
        data = yaml.safe_load(snapshot.content)
    except yaml.YAMLError as exc:
        raise WorkbenchError(
            ErrorCode.PARSE_ERROR,
            f"YAML 解析失败：{snapshot.path}",
            exit_code=2,
        ) from exc
    return VersionedYaml(path=snapshot.path, data={} if data is None else data, version=snapshot.version)


def write_yaml_atomic(
    path: str | Path,
    data: Any,
    *,
    dry_run: bool = False,
    expected_version: str | None = None,
    create_only: bool = False,
) -> WriteResult:
    try:
        content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    except yaml.YAMLError as exc:
        raise WorkbenchError(
            ErrorCode.PARSE_ERROR,
            f"YAML 序列化失败：{path}",
            exit_code=2,
        ) from exc
    return write_text_utf8_atomic(
        path,
        content,
        dry_run=dry_run,
        expected_version=expected_version,
        create_only=create_only,
    )


def rollback_text_files_if_unchanged(
    expected_contents: Mapping[Path, str],
    *,
    dry_run: bool = False,
) -> None:
    if dry_run:
        return
    parents = []
    for path, expected in reversed(tuple(expected_contents.items())):
        if path.exists() and _text_file_matches(path, expected):
            path.unlink()
        parents.append(path.parent)
    for parent in sorted(set(parents), key=lambda item: len(item.parts), reverse=True):
        try:
            parent.rmdir()
        except OSError:
            pass


def _content_version(raw: bytes) -> str:
    return sha256(raw).hexdigest()


class _target_write_lock:
    def __init__(self, target: Path, *, timeout_seconds: float = 5.0, stale_seconds: float = 120.0) -> None:
        self.lock_path = target.with_name(f".{target.name}.lock")
        self.timeout_seconds = timeout_seconds
        self.stale_seconds = stale_seconds

    def __enter__(self) -> None:
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return
            except FileExistsError as exc:
                if self._try_remove_stale_lock():
                    continue
                if time.monotonic() >= deadline:
                    raise WorkbenchError(
                        ErrorCode.CONCURRENT_UPDATE,
                        f"write_lock_busy: {self.lock_path}",
                        exit_code=2,
                    ) from exc
                time.sleep(0.05)
            except OSError as exc:
                raise WorkbenchError(
                    ErrorCode.IO_ERROR,
                    f"创建写入锁失败：{self.lock_path}",
                    exit_code=1,
                ) from exc

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
        except OSError as unlink_exc:
            raise WorkbenchError(
                ErrorCode.IO_ERROR,
                f"释放写入锁失败：{self.lock_path}",
                exit_code=1,
            ) from unlink_exc

    def _try_remove_stale_lock(self) -> bool:
        try:
            age = time.time() - self.lock_path.stat().st_mtime
        except FileNotFoundError:
            return True
        except OSError:
            return False
        if age < self.stale_seconds:
            return False
        try:
            self.lock_path.unlink()
            return True
        except OSError:
            return False


def _text_file_matches(path: Path, expected: str) -> bool:
    try:
        return read_text_utf8(path) == expected
    except WorkbenchError:
        return False


def _assert_write_precondition(
    target: Path,
    *,
    expected_version: str | None,
    create_only: bool,
) -> None:
    if create_only and target.exists():
        raise WorkbenchError(
            ErrorCode.ALREADY_EXISTS,
            f"already_exists: {target}",
            exit_code=2,
        )
    if expected_version is None:
        return
    try:
        current_version = _content_version(target.read_bytes())
    except FileNotFoundError:
        current_version = ""
    except OSError as exc:
        raise WorkbenchError(
            ErrorCode.IO_ERROR,
            f"读取写入前版本失败：{target}",
            exit_code=1,
        ) from exc
    if current_version != expected_version:
        raise WorkbenchError(
            ErrorCode.CONCURRENT_UPDATE,
            f"concurrent_update: {target} changed; refresh context and retry",
            exit_code=2,
        )
