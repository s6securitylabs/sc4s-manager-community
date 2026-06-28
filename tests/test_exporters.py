import hashlib
import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.exporters import PackExportError, build_pack_export_bundle
from sc4s_manager.packs import load_packs, pack_by_id


def commvault_pack():
    return pack_by_id(load_packs(ROOT / "packs"), "commvault_commcell")


def test_export_bundle_preserves_source_layout_and_manifest_checksums():
    pack = commvault_pack()
    filename, data, manifest = build_pack_export_bundle(pack, pack["pack_dir"], created_at="2026-05-26T00:00:00Z")

    assert filename == "commvault_commcell-0.1.0.zip"
    assert manifest["pack_id"] == "commvault_commcell"
    assert manifest["pack_version"] == pack["version"]
    assert manifest["schema_version"] == "0.1"
    assert manifest["created_at"] == "2026-05-26T00:00:00Z"

    with zipfile.ZipFile(BytesIO(data)) as bundle:
        names = set(bundle.namelist())
        assert "manifest.json" in names
        for artifact in pack["export_artifacts"]:
            assert artifact["source_path"] in names
        zip_manifest = json.loads(bundle.read("manifest.json"))
        assert zip_manifest == manifest
        exported = {entry["source_path"]: entry for entry in manifest["artifacts"]}
        for artifact in pack["export_artifacts"]:
            payload = bundle.read(artifact["source_path"])
            entry = exported[artifact["source_path"]]
            assert entry["target_path"] == artifact["target_path"]
            assert entry["kind"] == artifact["kind"]
            assert entry["sha256"] == hashlib.sha256(payload).hexdigest()
            assert entry["rendered"] is artifact["rendered"]
            assert entry["contains_secrets"] is False
            assert entry["required"] is artifact["required"]


def test_export_refuses_unrendered_secret_artifacts():
    pack = commvault_pack()
    pack["export_artifacts"] = [dict(pack["export_artifacts"][0], contains_secrets=True, rendered=False)]

    with pytest.raises(PackExportError, match="contains secrets"):
        build_pack_export_bundle(pack, pack["pack_dir"])


def test_export_allows_rendered_secret_artifacts():
    pack = commvault_pack()
    pack["export_artifacts"] = [dict(pack["export_artifacts"][0], contains_secrets=True, rendered=True)]

    _filename, _data, manifest = build_pack_export_bundle(pack, pack["pack_dir"], created_at="2026-05-26T00:00:00Z")

    assert manifest["artifacts"][0]["contains_secrets"] is True
    assert manifest["artifacts"][0]["rendered"] is True


def test_export_rejects_backslash_traversal_in_source_and_target_paths(tmp_path):
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "safe.txt").write_text("ok")
    pack = {
        "id": "unsafe",
        "version": "0.1.0",
        "schema_version": "0.1",
        "export_artifacts": [
            {
                "source_path": "safe.txt",
                "target_path": "..\\outside.conf",
                "kind": "test",
                "rendered": False,
                "contains_secrets": False,
                "required": True,
            }
        ],
    }

    with pytest.raises(PackExportError, match="relative safe path"):
        build_pack_export_bundle(pack, pack_dir)

    pack["export_artifacts"][0]["source_path"] = "..\\safe.txt"
    pack["export_artifacts"][0]["target_path"] = "safe.txt"

    with pytest.raises(PackExportError, match="relative safe path"):
        build_pack_export_bundle(pack, pack_dir)


def test_export_rejects_windows_absolute_artifact_paths(tmp_path):
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "safe.txt").write_text("ok")
    pack = {
        "id": "unsafe",
        "version": "0.1.0",
        "schema_version": "0.1",
        "export_artifacts": [
            {
                "source_path": "safe.txt",
                "target_path": "C:\\sc4s\\local.conf",
                "kind": "test",
                "rendered": False,
                "contains_secrets": False,
                "required": True,
            }
        ],
    }

    with pytest.raises(PackExportError, match="relative safe path"):
        build_pack_export_bundle(pack, pack_dir)
