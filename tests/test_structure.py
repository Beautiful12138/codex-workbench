from __future__ import annotations

from inspect import isfunction, signature
from pathlib import Path

import codex_workbench.index as index_module
import codex_workbench.packages as packages_module


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


def test_index_facade_exports_only_supported_api() -> None:
    expected = {
        "IndexCheckResult",
        "IndexWriteResult",
        "check_generated_views",
        "generate_index_views",
    }

    assert set(getattr(index_module, "__all__", ())) == expected
    assert not {
        "collect_snapshot",
        "render_current",
        "render_index",
        "render_recovery",
    }.intersection(vars(index_module))


def test_package_facade_return_annotations_hide_private_modules() -> None:
    leaked_annotations = {
        name: str(signature(value).return_annotation)
        for name in packages_module.__all__
        if isfunction(value := getattr(packages_module, name))
        and "package_core." in str(signature(value).return_annotation)
    }

    assert leaked_annotations == {}
