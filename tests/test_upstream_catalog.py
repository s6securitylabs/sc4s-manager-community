import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.upstream_catalog import (
    build_catalogues,
    build_drift_report,
    catalog_main,
    load_existing_catalogues,
    sync_upstream_catalogue,
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def fake_upstream_tree(root: Path, *, asa_contents: str = "asa-v1", include_postfilter: bool = True) -> None:
    write(root / "package/etc/conf.d/conflib/syslog/app-syslog-cisco_asa.conf", asa_contents + "\n")
    write(root / "package/etc/conf.d/conflib/netsource/app-netsource-vmware_vsphere.conf", "netsource\n")
    if include_postfilter:
        write(root / "package/etc/conf.d/conflib/post-filter/app-postfilter-cisco_asa-noise.conf", "drop debug\n")
    write(root / "package/etc/conf.d/destinations/d_hec_fmt.conf", "destination\n")
    write(root / "docs/sources/vendor/Cisco/asa/index.md", "# Cisco ASA\n")
    write(root / "package/lite/etc/addons/paloalto_panos/lite-panos.conf", "lite\n")


def test_catalog_main_writes_deterministic_json_and_tsv(tmp_path: Path, capsys) -> None:
    upstream_root = tmp_path / "upstream"
    fake_upstream_tree(upstream_root)
    output_dir = tmp_path / "out"
    generated_at = "2026-05-27T13:00:00Z"

    exit_code = catalog_main(
        [
            "--upstream-root",
            str(upstream_root),
            "--output-dir",
            str(output_dir),
            "--repo-url",
            "https://example.invalid/sc4s.git",
            "--requested-ref",
            "v1.2.3",
            "--resolved-commit",
            "abc123",
            "--generated-at",
            generated_at,
        ]
    )

    assert exit_code == 0
    payload = json.loads((output_dir / "sc4s-inbuilt.json").read_text())
    assert payload["origin"] == "sc4s-inbuilt"
    assert payload["upstream"] == {
        "repo_url": "https://example.invalid/sc4s.git",
        "requested_ref": "v1.2.3",
        "resolved_commit": "abc123",
        "generated_at": generated_at,
        "artifact_count": 5,
    }
    assert [artifact["artifact_path"] for artifact in payload["artifacts"]] == [
        "docs/sources/vendor/Cisco/asa/index.md",
        "package/etc/conf.d/conflib/netsource/app-netsource-vmware_vsphere.conf",
        "package/etc/conf.d/conflib/post-filter/app-postfilter-cisco_asa-noise.conf",
        "package/etc/conf.d/conflib/syslog/app-syslog-cisco_asa.conf",
        "package/etc/conf.d/destinations/d_hec_fmt.conf",
    ]
    assert payload["artifacts"][0]["source_id"] == "cisco_asa"
    assert payload["artifacts"][0]["vendor"] == "cisco"
    assert payload["artifacts"][0]["product"] == "asa"

    lite_payload = json.loads((output_dir / "sc4s-inbuilt-lite.json").read_text())
    assert lite_payload["artifacts"][0]["source_id"] == "paloalto_panos"
    assert lite_payload["artifacts"][0]["artifact_type"] == "lite_addon"

    with (output_dir / "sc4s-inbuilt.tsv").open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["artifact_path"] == "docs/sources/vendor/Cisco/asa/index.md"
    assert rows[-1]["artifact_type"] == "destination"

    stdout = json.loads(capsys.readouterr().out)
    assert stdout["catalogues"]["sc4s-inbuilt"]["json"].endswith("sc4s-inbuilt.json")

    second = build_catalogues(
        upstream_root,
        repo_url="https://example.invalid/sc4s.git",
        requested_ref="v1.2.3",
        resolved_commit="abc123",
        generated_at=generated_at,
    )
    assert second == load_existing_catalogues(output_dir)


def test_build_drift_report_detects_added_removed_and_changed_artifacts(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    fake_upstream_tree(first_root)
    fake_upstream_tree(second_root, asa_contents="asa-v2", include_postfilter=False)
    write(second_root / "package/etc/conf.d/conflib/syslog/app-syslog-fortinet_fortigate.conf", "forti\n")

    previous = build_catalogues(first_root, repo_url="repo", requested_ref="old", resolved_commit="111", generated_at="2026-05-27T13:00:00Z")
    current = build_catalogues(second_root, repo_url="repo", requested_ref="new", resolved_commit="222", generated_at="2026-05-27T14:00:00Z")
    drift = build_drift_report(previous, current)

    assert drift["summary"] == {"added": 1, "removed": 1, "changed": 1}
    assert drift["added"][0]["artifact_path"] == "package/etc/conf.d/conflib/syslog/app-syslog-fortinet_fortigate.conf"
    assert drift["removed"][0]["artifact_path"] == "package/etc/conf.d/conflib/post-filter/app-postfilter-cisco_asa-noise.conf"
    assert drift["changed"][0]["artifact_path"] == "package/etc/conf.d/conflib/syslog/app-syslog-cisco_asa.conf"
    assert drift["changed"][0]["before"]["sha256"] != drift["changed"][0]["after"]["sha256"]


def test_sync_upstream_catalogue_writes_drift_outputs_and_preserves_packs(tmp_path: Path, monkeypatch) -> None:
    manager_root = tmp_path / "manager"
    cache_dir = tmp_path / "cache"
    output_dir = tmp_path / "generated"
    write(manager_root / "packs/example/pack.json", '{"id":"example"}\n')
    fake_upstream_tree(cache_dir)

    def fake_refresh(cache_dir_arg: Path, repo_url: str, ref: str, refresh_cache: bool) -> str:
        assert cache_dir_arg == cache_dir
        assert repo_url == "https://example.invalid/sc4s.git"
        assert ref == "v1.2.3"
        assert refresh_cache is True
        return "commit-one"

    monkeypatch.setattr("sc4s_manager.upstream_catalog.refresh_upstream_cache", fake_refresh)

    result_one = sync_upstream_catalogue(
        manager_root=manager_root,
        cache_dir=cache_dir,
        output_dir=output_dir,
        repo_url="https://example.invalid/sc4s.git",
        ref="v1.2.3",
        refresh_cache=True,
        generated_at="2026-05-27T13:00:00Z",
    )
    assert result_one["drift_report"]["summary"] == {"added": 6, "removed": 0, "changed": 0}
    assert json.loads((output_dir / "drift-report.json").read_text())["summary"]["added"] == 6
    assert "Added: 6" in (output_dir / "drift-report.md").read_text()
    before_pack = (manager_root / "packs/example/pack.json").read_text()

    fake_upstream_tree(cache_dir, asa_contents="asa-v2", include_postfilter=False)
    postfilter = cache_dir / "package/etc/conf.d/conflib/post-filter/app-postfilter-cisco_asa-noise.conf"
    if postfilter.exists():
        postfilter.unlink()
    write(cache_dir / "package/etc/conf.d/conflib/syslog/app-syslog-fortinet_fortigate.conf", "forti\n")

    def fake_refresh_two(cache_dir_arg: Path, repo_url: str, ref: str, refresh_cache: bool) -> str:
        return "commit-two"

    monkeypatch.setattr("sc4s_manager.upstream_catalog.refresh_upstream_cache", fake_refresh_two)

    result_two = sync_upstream_catalogue(
        manager_root=manager_root,
        cache_dir=cache_dir,
        output_dir=output_dir,
        repo_url="https://example.invalid/sc4s.git",
        ref="v2.0.0",
        refresh_cache=False,
        generated_at="2026-05-27T14:00:00Z",
    )
    assert result_two["resolved_commit"] == "commit-two"
    assert result_two["drift_report"]["summary"] == {"added": 1, "removed": 1, "changed": 1}
    assert (manager_root / "packs/example/pack.json").read_text() == before_pack
