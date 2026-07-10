from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_public_facades_stay_focused() -> None:
    limits = {"index.py": 220, "packages.py": 220}
    oversized = {
        filename: _line_count(ROOT / "src" / "codex_workbench" / filename)
        for filename, limit in limits.items()
        if _line_count(ROOT / "src" / "codex_workbench" / filename) > limit
    }

    assert oversized == {}


def test_runtime_modules_stay_within_reviewable_size() -> None:
    oversized = {
        path.relative_to(ROOT).as_posix(): _line_count(path)
        for path in sorted((ROOT / "src" / "codex_workbench").glob("*.py"))
        if _line_count(path) > 700
    }

    assert oversized == {}


def test_cli_test_modules_stay_within_reviewable_size() -> None:
    oversized = {
        path.relative_to(ROOT).as_posix(): _line_count(path)
        for path in sorted((ROOT / "tests").glob("test_cli*.py"))
        if _line_count(path) > 1_200
    }

    assert oversized == {}
