from __future__ import annotations

import os
from pathlib import Path


def storage_path(root: Path, key: str) -> Path:
    """Resolve a generated storage key inside its configured root."""

    path = root / key
    if path.parent.resolve() != root.resolve():
        raise RuntimeError("Invalid storage key")
    return path


def write_atomic(path: Path, data: bytes) -> None:
    """Write the file completely before exposing it under its final name."""

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.parent / f".{path.name}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def delete_file(path: Path) -> None:
    path.unlink(missing_ok=True)
