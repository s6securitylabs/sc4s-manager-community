import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.test_paths import (
    default_coverage_file,
    default_pytest_cache_dir,
    default_test_venv_dir,
)


def test_default_test_venv_dir_uses_uid_scoped_path_when_writable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(os, "getuid", lambda: 4242)

    venv_dir = default_test_venv_dir()

    assert venv_dir == tmp_path / "sc4s-manager-test-venv-4242"


def test_default_test_venv_dir_falls_back_when_preferred_path_is_unwritable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    stale = tmp_path / "sc4s-manager-test-venv-4242"
    stale.mkdir()
    stale.chmod(0o500)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(os, "getuid", lambda: 4242)

    venv_dir = default_test_venv_dir()

    assert venv_dir.is_dir()
    assert venv_dir.parent == tmp_path
    assert venv_dir != stale
    assert venv_dir.name.startswith("sc4s-manager-test-venv-4242.")


def test_default_pytest_cache_dir_falls_back_when_preferred_path_is_unwritable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    stale = tmp_path / "sc4s-manager-pytest-cache-4242"
    stale.mkdir()
    stale.chmod(0o500)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(os, "getuid", lambda: 4242)

    cache_dir = default_pytest_cache_dir()

    assert cache_dir.is_dir()
    assert cache_dir.parent == tmp_path
    assert cache_dir != stale
    assert cache_dir.name.startswith("sc4s-manager-pytest-cache-4242.")


def test_default_coverage_file_falls_back_when_preferred_path_is_unwritable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    stale = tmp_path / "sc4s-manager.coverage-4242"
    stale.write_text("stale coverage")
    stale.chmod(0o400)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(os, "getuid", lambda: 4242)

    coverage_file = default_coverage_file()

    assert coverage_file.parent == tmp_path
    assert coverage_file != stale
    assert not coverage_file.exists()
    assert coverage_file.name.startswith("sc4s-manager.coverage-4242.")
