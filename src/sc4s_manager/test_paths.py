from __future__ import annotations

import os
import tempfile
from pathlib import Path


TMPDIR_ENV = "TMPDIR"


def _tmp_root(tmp_root: str | Path | None = None) -> Path:
    return Path(tmp_root) if tmp_root is not None else Path(tempfile.gettempdir())


def _user_id(user_id: int | None = None) -> int:
    return os.getuid() if user_id is None else user_id


def _dir_is_writable(path: Path) -> bool:
    if path.exists():
        return path.is_dir() and os.access(path, os.W_OK | os.X_OK)
    return os.access(path.parent, os.W_OK | os.X_OK)


def _file_is_writable(path: Path) -> bool:
    if path.exists():
        return path.is_file() and os.access(path, os.W_OK)
    return os.access(path.parent, os.W_OK | os.X_OK)


def _user_scoped_dir_name(stem: str, user_id: int) -> str:
    return f"{stem}-{user_id}"


def default_test_venv_dir(*, tmp_root: str | Path | None = None, user_id: int | None = None) -> Path:
    root = _tmp_root(tmp_root)
    uid = _user_id(user_id)
    preferred = root / _user_scoped_dir_name("sc4s-manager-test-venv", uid)
    if _dir_is_writable(preferred):
        return preferred
    return Path(tempfile.mkdtemp(prefix=f"sc4s-manager-test-venv-{uid}.", dir=str(root)))


def default_pytest_cache_dir(*, tmp_root: str | Path | None = None, user_id: int | None = None) -> Path:
    root = _tmp_root(tmp_root)
    uid = _user_id(user_id)
    preferred = root / _user_scoped_dir_name("sc4s-manager-pytest-cache", uid)
    if _dir_is_writable(preferred):
        return preferred
    return Path(tempfile.mkdtemp(prefix=f"sc4s-manager-pytest-cache-{uid}.", dir=str(root)))


def default_coverage_file(*, tmp_root: str | Path | None = None, user_id: int | None = None) -> Path:
    root = _tmp_root(tmp_root)
    uid = _user_id(user_id)
    preferred = root / f"sc4s-manager.coverage-{uid}"
    if _file_is_writable(preferred):
        return preferred
    fd, fallback = tempfile.mkstemp(prefix=f"sc4s-manager.coverage-{uid}.", dir=str(root))
    os.close(fd)
    fallback_path = Path(fallback)
    fallback_path.unlink(missing_ok=True)
    return fallback_path
