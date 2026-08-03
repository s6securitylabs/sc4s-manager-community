from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from sc4s_manager.embedded_library import EMBEDDED_SOURCE_ID, EmbeddedLibraryManager, snapshot_content_sha256


ROOT = Path(__file__).resolve().parents[1]


def manager(tmp_path: Path) -> EmbeddedLibraryManager:
    snapshot = tmp_path / "embedded_library"
    snapshot.mkdir()
    (snapshot / "packs").symlink_to(ROOT / "embedded_library" / "packs", target_is_directory=True)
    (snapshot / "SNAPSHOT.json").write_text((ROOT / "embedded_library" / "SNAPSHOT.json").read_text())
    return EmbeddedLibraryManager(
        root=tmp_path / "sc4s",
        manager_root=tmp_path,
        validate_config=lambda: {"ok": True},
        reload_sc4s=lambda actor: {"ok": True, "actor": actor},
        post_check=lambda: {"ok": True},
        audit=lambda *args: None,
    )


def test_embedded_snapshot_has_every_pinned_source_manifest() -> None:
    snapshot = json.loads((ROOT / "embedded_library" / "SNAPSHOT.json").read_text())
    manifests = sorted((ROOT / "embedded_library" / "packs").glob("*/pack.json"))
    assert snapshot["source_revision"] == "839c21b2e8d2739b84eaf2075cad8a7d9ee0710f"
    assert len(manifests) == snapshot["pack_count"] == 67
    assert snapshot_content_sha256(ROOT / "embedded_library", ROOT / "embedded_library" / "packs") == snapshot["content_sha256"]


def test_committed_embedded_snapshot_tree_matches_declared_source_tree_when_available() -> None:
    """Git tree identity proves byte and mode parity with the pinned source."""
    source_repo = Path(os.environ.get("SECHUB_RESOURCES_REPOSITORY", ROOT.parent / "sechub-resources"))
    if not (source_repo / ".git").exists():
        pytest.skip("pinned SecHub Resources repository is not available")
    snapshot = json.loads((ROOT / "embedded_library" / "SNAPSHOT.json").read_text())

    def git(*args: str, cwd: Path) -> str:
        return subprocess.run(["git", "-C", str(cwd), *args], check=True, text=True, capture_output=True).stdout.strip()

    source_tree = git("rev-parse", f"{snapshot['source_revision']}:packs", cwd=source_repo)
    committed_tree = git("rev-parse", "HEAD:embedded_library/packs", cwd=ROOT)
    assert source_tree == snapshot["source_tree"]
    assert committed_tree == source_tree


def test_catalogue_discovery_and_known_sc4s_splunk_fixture_assets_are_local(tmp_path: Path) -> None:
    library = manager(tmp_path)
    entries = library.catalogue()["entries"]
    assert len(entries) == 67
    assert {"cisco_asa", "pan_panos", "windows_eventlog"} <= {entry["id"] for entry in entries}
    pack = ROOT / "embedded_library" / "packs" / "cisco_asa"
    assert (pack / "sc4s/app_parsers/syslog/app-cisco_asa.conf").is_file()
    assert (pack / "splunk/default/props.conf").is_file()
    assert (pack / "test-events/cisco_asa_test_events.txt").is_file()


def test_local_staging_never_uses_network_and_exposes_provenance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: pytest.fail("offline library attempted network access"))
    library = manager(tmp_path)
    detail = library.entry(EMBEDDED_SOURCE_ID, "cisco_asa")
    staged = library.validate_import(EMBEDDED_SOURCE_ID, "cisco_asa")
    assert detail["entry"]["is_remote"] is False
    assert detail["entry"]["snapshot"]["source_revision"] == "839c21b2e8d2739b84eaf2075cad8a7d9ee0710f"
    assert staged["apply_allowed"] is True
    assert staged["runtime_files"]


def test_malformed_snapshot_metadata_fails_closed(tmp_path: Path) -> None:
    library = manager(tmp_path)
    snapshot = tmp_path / "embedded_library" / "SNAPSHOT.json"
    snapshot.unlink()
    snapshot.write_text("{}")
    with pytest.raises(ValueError, match="snapshot metadata is malformed"):
        library.catalogue()


def test_snapshot_content_hash_fails_closed_when_a_snapshot_file_changes(tmp_path: Path) -> None:
    library = manager(tmp_path)
    snapshot = tmp_path / "embedded_library" / "SNAPSHOT.json"
    metadata = json.loads(snapshot.read_text())
    metadata["content_sha256"] = "0" * 64
    snapshot.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="content hash does not match"):
        library.catalogue()


def test_unsafe_runtime_target_in_snapshot_fails_before_staging(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "embedded_library"
    packs_root = snapshot_root / "packs"
    pack_root = packs_root / "cisco_asa"
    shutil.copytree(ROOT / "embedded_library" / "packs" / "cisco_asa", pack_root)
    metadata = json.loads((ROOT / "embedded_library" / "SNAPSHOT.json").read_text())
    metadata["pack_count"] = 1
    manifest = pack_root / "pack.json"
    pack = json.loads(manifest.read_text())
    runtime = next(item for item in pack["export_artifacts"] if item["target_path"].startswith("local/config/"))
    runtime["target_path"] = "local/config/../../outside.conf"
    manifest.write_text(json.dumps(pack))
    metadata["content_sha256"] = snapshot_content_sha256(snapshot_root, packs_root)
    (snapshot_root / "SNAPSHOT.json").write_text(json.dumps(metadata))
    isolated = EmbeddedLibraryManager(
        root=tmp_path / "sc4s",
        manager_root=tmp_path,
        validate_config=lambda: {"ok": True}, reload_sc4s=lambda actor: {"ok": True}, post_check=lambda: {"ok": True}, audit=lambda *args: None,
    )
    with pytest.raises(ValueError, match="unsafe library target_path"):
        isolated.validate_import(EMBEDDED_SOURCE_ID, "cisco_asa")


def test_remote_source_identifier_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="remote library sources are retired"):
        manager(tmp_path).catalogue("official")


def test_source_health_reports_snapshot_integrity_without_remote_manifest(tmp_path: Path) -> None:
    health = manager(tmp_path).source_health()
    assert health["checks"] == [{"name": "snapshot_integrity", "ok": True}]
    assert "manifest" not in health
    assert health["trust_semantics"]["snapshot_metadata_can_set_local_is_verified"] is False
