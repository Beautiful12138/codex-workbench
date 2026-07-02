from __future__ import annotations

from pathlib import Path

from .errors import ErrorCode, WorkbenchError


def validate_package_ref(package_ref: str) -> str:
    cleaned = package_ref.strip()
    parts = Path(cleaned).parts
    if (
        not cleaned
        or cleaned != package_ref
        or parts != (cleaned,)
        or cleaned == "."
        or cleaned == ".."
    ):
        raise WorkbenchError(
            ErrorCode.VALIDATION_ERROR,
            f"invalid_package_ref: {package_ref}",
            exit_code=2,
        )
    return cleaned
