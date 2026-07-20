import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIBRARY_PATH = ROOT / "src" / "sc4s_manager" / "library.py"


def load_library() -> Any:
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location("sc4s_library_test", LIBRARY_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_bundle(entry_id: str = "pan_panos", version: str = "1.2.3") -> bytes:
    config_bytes = b"filter f_test { netmask(\"10.0.0.0/24\"); };\n"
    context_bytes = b"f_test,sc4s_vendor_product,paloalto_panos\n"
    env_bytes = b"SC4S_DEST_SPLUNK_HEC_DEFAULT_URL=https://example.invalid\n"
    readme_bytes = b"reference only\n"
    manifest = {
        "pack_id": entry_id,
        "pack_version": version,
        "schema_version": "1.0.0",
        "artifacts": [
            {
                "kind": "config",
                "source_path": "local/config/app_parsers/panos.conf",
                "target_path": "local/config/app_parsers/panos.conf",
                "sha256": load_library().sha256_bytes(config_bytes),
            },
            {
                "kind": "context",
                "source_path": "local/context/vendor_product_by_source.csv",
                "target_path": "local/context/vendor_product_by_source.csv",
                "sha256": load_library().sha256_bytes(context_bytes),
            },
            {
                "kind": "env",
                "source_path": "env_file.d/panos.env",
                "target_path": "env_file.d/panos.env",
                "sha256": load_library().sha256_bytes(env_bytes),
            },
            {
                "kind": "docs",
                "source_path": "README.md",
                "target_path": "README.md",
                "sha256": load_library().sha256_bytes(readme_bytes),
            },
        ],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("local/config/app_parsers/panos.conf", config_bytes)
        zf.writestr("local/context/vendor_product_by_source.csv", context_bytes)
        zf.writestr("env_file.d/panos.env", env_bytes)
        zf.writestr("README.md", readme_bytes)
    return buf.getvalue()


def build_bundle_with_invalid_pack(entry_id: str = "pan_panos", version: str = "1.2.3") -> bytes:
    bundle = build_bundle(entry_id=entry_id, version=version)
    buf = io.BytesIO()
    invalid_pack = {
        "schema_version": "0.1",
        "id": entry_id,
        "version": version,
        "provenance": {
            "origin": "sc4s-" + "n" + "ext-extra",
            "pack_class": "sc4s-" + "n" + "ext-extra",
            "source": {},
            "curation": {},
        },
    }
    with zipfile.ZipFile(io.BytesIO(bundle)) as src, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        manifest = json.loads(src.read("manifest.json"))
        pack_bytes = json.dumps(invalid_pack, sort_keys=True).encode()
        manifest["artifacts"].append({
            "kind": "pack_manifest",
            "source_path": "pack.json",
            "target_path": "pack.json",
            "sha256": load_library().sha256_bytes(pack_bytes),
        })
        dst.writestr("manifest.json", json.dumps(manifest, indent=2))
        for info in src.infolist():
            if info.filename == "manifest.json":
                continue
            dst.writestr(info, src.read(info.filename))
        dst.writestr("pack.json", pack_bytes)
    return buf.getvalue()


class LibraryTests(unittest.TestCase):
    def test_apply_live_state_requires_explicit_post_check_success(self):
        mod = load_library()
        state = mod.apply_live_state({"ok": True}, {"ok": True}, {})
        self.assertEqual(state["apply_state"], "applied")
        self.assertEqual(state["live_state"], "unknown")

    def test_apply_live_state_marks_live_for_explicit_post_check_ok(self):
        mod = load_library()
        state = mod.apply_live_state({"ok": True}, {"ok": True}, {"ok": True})
        self.assertEqual(state["apply_state"], "applied")
        self.assertEqual(state["live_state"], "live")

    def test_apply_live_state_reload_failure_remains_not_live(self):
        mod = load_library()
        state = mod.apply_live_state({"ok": True}, {"ok": False, "error": "reload failed"}, {"ok": True})
        self.assertEqual(state["apply_state"], "applied_reload_failed")
        self.assertEqual(state["live_state"], "not_live")

    def test_sources_expose_official_default_and_legacy_fallback_metadata(self):
        mod = load_library()
        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(root=Path(d) / "sc4s", manager_root=Path(d) / "manager")
            payload = manager.sources()
            self.assertEqual(payload["sources"][0]["source_id"], "official")
            self.assertEqual(
                payload["sources"][0]["catalogue_url"],
                "https://sechub.s6ops.com/data/catalogue.json",
            )

    def test_sync_rejects_non_https_catalogue_url(self):
        mod = load_library()
        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(
                root=Path(d) / "sc4s",
                manager_root=Path(d) / "manager",
                sources=[{
                    "source_id": "bad",
                    "catalogue_url": "http://example.invalid/catalogue.json",
                    "manifest_url": "https://example.invalid/manifest.json",
                    "enabled": True,
                }],
            )
            with self.assertRaises(ValueError):
                manager.sync_source("bad")

    def test_default_fetch_json_rejects_redirects(self):
        mod = load_library()
        source = dict(mod.DEFAULT_SOURCES[0])

        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
            def geturl(self):
                return "https://evil.example/catalogue.json"
            def read(self, _limit):
                return b'{"entries": []}'

        class FakeOpener:
            def open(self, url, timeout):
                return FakeResponse()

        with patch.object(mod.urllib.request, "build_opener", return_value=FakeOpener()):
            with self.assertRaises(ValueError):
                mod._default_fetch_json(source["catalogue_url"], source, mod.MAX_JSON_BYTES)

    def test_sync_persists_catalogue_cache_and_source_metadata(self):
        mod = load_library()
        catalogue = {
            "entries": [
                {
                    "id": "pan_panos",
                    "display_name": "Palo Alto PAN-OS",
                    "vendor": "Palo Alto",
                    "product": "PAN-OS",
                    "version": "1.2.3",
                    "download_available": True,
                }
            ]
        }
        manifest = {"downloads": []}
        calls: list[str] = []

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            calls.append(url)
            if url.endswith("catalogue.json"):
                return catalogue
            if url.endswith("manifest.json"):
                return manifest
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(root=Path(d) / "sc4s", manager_root=Path(d) / "manager", fetch_json=fetch_json)
            result = manager.sync_source("official")
            self.assertEqual(result["entry_count"], 1)
            self.assertEqual(len(calls), 2)
            cached_catalogue = json.loads((manager.library_dir / "catalogue" / "official.json").read_text())
            self.assertEqual(cached_catalogue["entries"][0]["id"], "pan_panos")
            sources_state = json.loads((manager.library_dir / "sources.json").read_text())
            self.assertIn("official", sources_state["sources"])
            self.assertEqual(sources_state["sources"]["official"]["entry_count"], 1)

    def test_validate_import_creates_runtime_plan_and_reference_staging(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "version": "1.2.3",
            "display_name": "Palo Alto PAN-OS",
            "vendor": "Palo Alto",
            "product": "PAN-OS",
            "capabilities": ["parsing"],
            "artifacts": [],
            "download": {
                "filename": "pan_panos-1.2.3.zip",
                "url": "https://sechub.s6ops.com/downloads/pan_panos-1.2.3.zip",
            },
        }
        bundle = build_bundle()
        detail["download"]["sha256"] = mod.sha256_bytes(bundle)
        manifest = {
            "downloads": [
                {
                    "filename": "pan_panos-1.2.3.zip",
                    "pack_id": "pan_panos",
                    "version": "1.2.3",
                    "sha256": detail["download"]["sha256"],
                }
            ]
        }

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            if url.endswith("catalogue.json"):
                return {"entries": [{"id": "pan_panos", "download_available": True}]}
            if url.endswith("manifest.json"):
                return manifest
            if url.endswith("entries/pan_panos.json"):
                return detail
            raise AssertionError(url)

        def fetch_bytes(url: str, source: dict[str, Any], max_bytes: int) -> bytes:
            self.assertTrue(url.endswith("pan_panos-1.2.3.zip"))
            return bundle

        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(
                root=Path(d) / "sc4s",
                manager_root=Path(d) / "manager",
                fetch_json=fetch_json,
                fetch_bytes=fetch_bytes,
            )
            manager.sync_source("official")
            result = manager.validate_import("official", "pan_panos")
            self.assertTrue(result["apply_allowed"])
            self.assertFalse(result["reference_only"])
            self.assertEqual({item["target_path"] for item in result["runtime_files"]}, {
                "local/config/app_parsers/panos.conf",
                "local/context/vendor_product_by_source.csv",
            })
            self.assertEqual({item["target_path"] for item in result["reference_files"]}, {
                "env_file.d/panos.env",
                "README.md",
            })
            runtime_plan = json.loads((manager.imports_dir / result["import_id"] / "runtime-plan.json").read_text())
            self.assertEqual(len(runtime_plan["artifacts"]), 2)
            self.assertTrue((manager.imports_dir / result["import_id"] / "reference" / "env_file.d" / "panos.env").exists())
            record = json.loads((manager.imports_dir / result["import_id"] / "record.json").read_text())
            self.assertEqual(record["entry_id"], "pan_panos")
            self.assertTrue(record["pack_validation"]["skipped"])
            self.assertIn("pack.json", record["pack_validation"]["reason"])

    def test_validate_import_rejects_invalid_embedded_pack_manifest(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "version": "1.2.3",
            "display_name": "Palo Alto PAN-OS",
            "vendor": "Palo Alto",
            "product": "PAN-OS",
            "capabilities": ["parsing"],
            "artifacts": [],
            "download": {
                "filename": "pan_panos-1.2.3.zip",
                "url": "https://sechub.s6ops.com/downloads/pan_panos-1.2.3.zip",
            },
        }
        bundle = build_bundle_with_invalid_pack()
        detail["download"]["sha256"] = mod.sha256_bytes(bundle)

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            if url.endswith("catalogue.json"):
                return {"entries": [{"id": "pan_panos", "download_available": True}]}
            if url.endswith("manifest.json"):
                return {"downloads": []}
            if url.endswith("entries/pan_panos.json"):
                return detail
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(
                root=Path(d) / "sc4s",
                manager_root=Path(d) / "manager",
                fetch_json=fetch_json,
                fetch_bytes=lambda url, source, max_bytes: bundle,
            )
            manager.sync_source("official")
            with self.assertRaisesRegex(ValueError, "pack .* missing required fields"):
                manager.validate_import("official", "pan_panos")

    def test_download_bundle_caches_verified_zip_without_creating_import_record(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "version": "1.2.3",
            "display_name": "Palo Alto PAN-OS",
            "vendor": "Palo Alto",
            "product": "PAN-OS",
            "capabilities": ["parsing"],
            "artifacts": [],
            "download": {
                "filename": "pan_panos-1.2.3.zip",
                "url": "https://sechub.s6ops.com/downloads/pan_panos-1.2.3.zip",
            },
        }
        bundle = build_bundle()
        detail["download"]["sha256"] = mod.sha256_bytes(bundle)

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            if url.endswith("catalogue.json"):
                return {"entries": [{"id": "pan_panos", "download_available": True}]}
            if url.endswith("manifest.json"):
                return {"downloads": []}
            if url.endswith("entries/pan_panos.json"):
                return detail
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(
                root=Path(d) / "sc4s",
                manager_root=Path(d) / "manager",
                fetch_json=fetch_json,
                fetch_bytes=lambda url, source, max_bytes: bundle,
            )
            manager.sync_source("official")
            result = manager.download_bundle("official", "pan_panos")
            self.assertTrue(result["ok"])
            self.assertEqual(result["download"]["filename"], "pan_panos-1.2.3.zip")
            self.assertEqual(result["verification"]["artifact_count"], 4)
            self.assertTrue((manager.downloads_dir / "official" / "pan_panos-1.2.3.zip").exists())
            self.assertEqual(manager.list_imports(), {"imports": []})

    def test_download_bundle_rejects_malicious_filename_without_outside_write(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "version": "1.2.3",
            "display_name": "Palo Alto PAN-OS",
            "vendor": "Palo Alto",
            "product": "PAN-OS",
            "capabilities": ["parsing"],
            "artifacts": [],
            "download": {
                "filename": "../../../escape.zip",
                "url": "https://sechub.s6ops.com/downloads/pan_panos-1.2.3.zip",
            },
        }
        bundle = build_bundle()
        detail["download"]["sha256"] = mod.sha256_bytes(bundle)

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            if url.endswith("catalogue.json"):
                return {"entries": [{"id": "pan_panos", "download_available": True}]}
            if url.endswith("manifest.json"):
                return {"downloads": []}
            if url.endswith("entries/pan_panos.json"):
                return detail
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(
                root=Path(d) / "sc4s",
                manager_root=Path(d) / "manager",
                fetch_json=fetch_json,
                fetch_bytes=lambda url, source, max_bytes: bundle,
            )
            manager.sync_source("official")
            with self.assertRaisesRegex(ValueError, "download filename"):
                manager.download_bundle("official", "pan_panos")
            self.assertFalse(any(Path(d).rglob("escape.zip")))

    def test_entry_rejects_malicious_entry_id_without_outside_cache_write(self):
        mod = load_library()
        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(
                root=Path(d) / "sc4s",
                manager_root=Path(d) / "manager",
                fetch_json=lambda url, source, max_bytes: (_ for _ in ()).throw(AssertionError(url)),
            )
            for bad_entry_id in ("../../escape", "pan/panos"):
                with self.assertRaisesRegex(ValueError, "entry_id"):
                    manager.entry("official", bad_entry_id, refresh=True)
            self.assertFalse(any(Path(d).rglob("escape.json")))

    def test_inspect_bundle_rejects_manifest_pack_id_mismatch(self):
        mod = load_library()
        bundle = build_bundle(entry_id="pan_panos")
        detail = {"id": "other_pack", "version": "1.2.3"}
        with self.assertRaisesRegex(ValueError, "pack_id mismatch"):
            mod.inspect_bundle(bundle, detail)

    def test_apply_import_rolls_back_when_validation_fails(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "version": "1.2.3",
            "display_name": "Palo Alto PAN-OS",
            "vendor": "Palo Alto",
            "product": "PAN-OS",
            "capabilities": ["parsing"],
            "artifacts": [],
            "download": {
                "filename": "pan_panos-1.2.3.zip",
                "url": "https://sechub.s6ops.com/downloads/pan_panos-1.2.3.zip",
            },
        }
        bundle = build_bundle()
        detail["download"]["sha256"] = mod.sha256_bytes(bundle)

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            if url.endswith("catalogue.json"):
                return {"entries": [{"id": "pan_panos", "download_available": True}]}
            if url.endswith("manifest.json"):
                return {"downloads": []}
            if url.endswith("entries/pan_panos.json"):
                return detail
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "sc4s"
            target = root / "local" / "config" / "app_parsers" / "panos.conf"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("before\n")
            manager = mod.LibraryManager(
                root=root,
                manager_root=Path(d) / "manager",
                fetch_json=fetch_json,
                fetch_bytes=lambda url, source, max_bytes: bundle,
                validate_config=lambda: {"ok": False, "error": "syntax broken"},
            )
            manager.sync_source("official")
            validated = manager.validate_import("official", "pan_panos")
            applied = manager.apply_import(validated["import_id"], actor="tester", apply=True)
            self.assertFalse(applied["ok"])
            self.assertTrue(applied["rolled_back"])
            self.assertEqual(target.read_text(), "before\n")
            self.assertEqual(applied["validation"]["error"], "syntax broken")

    def test_apply_import_success_returns_post_checks_and_control(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "version": "1.2.3",
            "display_name": "Palo Alto PAN-OS",
            "vendor": "Palo Alto",
            "product": "PAN-OS",
            "capabilities": ["parsing"],
            "artifacts": [],
            "download": {
                "filename": "pan_panos-1.2.3.zip",
                "url": "https://sechub.s6ops.com/downloads/pan_panos-1.2.3.zip",
            },
        }
        bundle = build_bundle()
        detail["download"]["sha256"] = mod.sha256_bytes(bundle)
        reload_calls: list[str] = []

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            if url.endswith("catalogue.json"):
                return {"entries": [{"id": "pan_panos", "download_available": True}]}
            if url.endswith("manifest.json"):
                return {"downloads": []}
            if url.endswith("entries/pan_panos.json"):
                return detail
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "sc4s"
            manager = mod.LibraryManager(
                root=root,
                manager_root=Path(d) / "manager",
                fetch_json=fetch_json,
                fetch_bytes=lambda url, source, max_bytes: bundle,
                validate_config=lambda: {"ok": True, "checked": True},
                reload_sc4s=lambda actor: reload_calls.append(actor) or {"ok": True, "reloaded": True},
                post_check=lambda: {"docker": {"running": True}, "health": {"ok": True}, "ports": {"tcp": {"listener_active": True}}},
            )
            manager.sync_source("official")
            validated = manager.validate_import("official", "pan_panos")
            applied = manager.apply_import(validated["import_id"], actor="tester", apply=True)
            self.assertTrue(applied["ok"])
            self.assertFalse(applied["rolled_back"])
            self.assertEqual(reload_calls, ["tester"])
            self.assertIn("local/config/app_parsers/panos.conf", applied["changed_targets"])
            self.assertTrue((root / "local" / "context" / "vendor_product_by_source.csv").exists())
            self.assertTrue(applied["post_check"]["health"]["ok"])
            self.assertEqual(applied["apply_state"], "applied")
            self.assertEqual(applied["live_state"], "live")
            imports = manager.list_imports()["imports"]
            self.assertEqual(imports[0]["last_apply"]["control"], {"ok": True, "reloaded": True})
            self.assertTrue(imports[0]["last_apply"]["post_check"]["health"]["ok"])
            self.assertEqual(imports[0]["last_apply"]["apply_state"], "applied")
            self.assertEqual(imports[0]["last_apply"]["live_state"], "live")

    def test_apply_import_restores_files_and_runtime_when_reload_fails(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "version": "1.2.3",
            "display_name": "Palo Alto PAN-OS",
            "vendor": "Palo Alto",
            "product": "PAN-OS",
            "capabilities": ["parsing"],
            "artifacts": [],
            "download": {
                "filename": "pan_panos-1.2.3.zip",
                "url": "https://sechub.s6ops.com/downloads/pan_panos-1.2.3.zip",
            },
        }
        bundle = build_bundle()
        detail["download"]["sha256"] = mod.sha256_bytes(bundle)

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            if url.endswith("catalogue.json"):
                return {"entries": [{"id": "pan_panos", "download_available": True}]}
            if url.endswith("manifest.json"):
                return {"downloads": []}
            if url.endswith("entries/pan_panos.json"):
                return detail
            raise AssertionError(url)

        reload_calls: list[str] = []
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "sc4s"
            target = root / "local" / "config" / "app_parsers" / "panos.conf"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("before\n")
            manager = mod.LibraryManager(
                root=root,
                manager_root=Path(d) / "manager",
                fetch_json=fetch_json,
                fetch_bytes=lambda url, source, max_bytes: bundle,
                validate_config=lambda: {"ok": True},
                reload_sc4s=lambda actor: reload_calls.append(actor) or ({"ok": False, "error": "reload failed"} if len(reload_calls) == 1 else {"ok": True, "reloaded": True}),
                post_check=lambda: {"health": {"ok": True}},
            )
            manager.sync_source("official")
            validated = manager.validate_import("official", "pan_panos")
            applied = manager.apply_import(validated["import_id"], actor="tester", apply=True)
            self.assertFalse(applied["ok"])
            self.assertEqual(applied["control"], {"ok": False, "error": "reload failed"})
            self.assertTrue(applied["rolled_back"])
            self.assertEqual(target.read_text(), "before\n")
            self.assertEqual(reload_calls, ["tester", "tester"])
            self.assertEqual(applied["rollback_runtime"], {"ok": True, "reloaded": True})
            self.assertEqual(applied["live_state"], "not_live")
            last_apply = manager.list_imports()["imports"][0]["last_apply"]
            self.assertEqual(last_apply["control"], applied["control"])
            self.assertEqual(last_apply["rollback_runtime"], applied["rollback_runtime"])
            self.assertEqual(last_apply["live_state"], "not_live")

    def test_post_check_failure_detects_explicit_negative_runtime_evidence(self):
        mod = load_library()
        self.assertTrue(mod._post_check_failed({"docker": {"running": False}, "health": {"ok": True}}))
        self.assertTrue(mod._post_check_failed({"control_provider": {"ok": False}, "health": {"ok": True}}))
        self.assertTrue(mod._post_check_failed({"ports": {"tcp": {"enabled": True, "listener_active": False}}}))
        self.assertFalse(mod._post_check_failed({"ports": {"tls": {"enabled": False, "listener_active": False}}}))
        self.assertFalse(mod._post_check_failed({"docker": {"running": True}, "health": {"ok": True}}))

    def test_atomic_json_write_preserves_mode_and_replaces_content(self):
        mod = load_library()
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "state.json"
            target.write_text('{"before": true}\n')
            target.chmod(0o640)
            mod.atomic_write_json(target, {"after": True})
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)
            self.assertEqual(json.loads(target.read_text()), {"after": True})

    def test_source_health_checks_catalogue_manifest_entry_bundle_and_sidecars(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "version": "1.2.3",
            "display_name": "Palo Alto PAN-OS",
            "vendor": "Palo Alto",
            "product": "PAN-OS",
            "capabilities": ["parsing"],
            "artifacts": [],
            "download": {
                "filename": "pan_panos-1.2.3.zip",
                "url": "https://sechub.s6ops.com/downloads/pan_panos-1.2.3.zip",
            },
        }
        bundle = build_bundle()
        detail["download"]["sha256"] = mod.sha256_bytes(bundle)
        manifest = {"downloads": [{"filename": "pan_panos-1.2.3.zip", "sha256": detail["download"]["sha256"]}]}

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            if url.endswith("catalogue.json"):
                return {"entries": [{"id": "pan_panos", "download_available": True}]}
            if url.endswith("manifest.json"):
                return manifest
            if url.endswith("entries/pan_panos.json"):
                return detail
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(
                root=Path(d) / "sc4s",
                manager_root=Path(d) / "manager",
                fetch_json=fetch_json,
                fetch_bytes=lambda url, source, max_bytes: bundle,
            )
            health = manager.source_health("official")
            self.assertTrue(health["overall_ok"])
            self.assertEqual({check["name"] for check in health["checks"]}, {"catalogue", "manifest", "sample_entry", "sample_bundle"})
            self.assertEqual(health["catalogue"]["entry_count"], 1)
            self.assertEqual(health["manifest"]["download_count"], 1)
            self.assertTrue(health["sample_bundle"]["ok"])
            self.assertGreaterEqual(len(health["sample_bundle"]["sidecars"]), 1)
            self.assertTrue(health["trust_semantics"]["remote_labels_are_advisory"])

    def test_source_health_reports_controlled_checksum_error(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "version": "1.2.3",
            "display_name": "Palo Alto PAN-OS",
            "vendor": "Palo Alto",
            "product": "PAN-OS",
            "capabilities": ["parsing"],
            "artifacts": [],
            "download": {
                "filename": "pan_panos-1.2.3.zip",
                "url": "https://sechub.s6ops.com/downloads/pan_panos-1.2.3.zip",
                "sha256": "0" * 64,
            },
        }
        bundle = build_bundle()

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            if url.endswith("catalogue.json"):
                return {"entries": [{"id": "pan_panos", "download_available": True}]}
            if url.endswith("manifest.json"):
                return {"downloads": [{"filename": "pan_panos-1.2.3.zip", "sha256": "0" * 64}]}
            if url.endswith("entries/pan_panos.json"):
                return detail
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(
                root=Path(d) / "sc4s",
                manager_root=Path(d) / "manager",
                fetch_json=fetch_json,
                fetch_bytes=lambda url, source, max_bytes: bundle,
            )
            health = manager.source_health("official")
            self.assertFalse(health["overall_ok"])
            self.assertEqual(health["sample_bundle"]["error_code"], "checksum_mismatch")
            self.assertIn("Do not apply", health["sample_bundle"]["next_action"])

    def test_classify_library_exceptions_are_operator_actionable(self):
        mod = load_library()
        cases = {
            "Name or service not known": "dns_failure",
            "HTTP 403 Forbidden from Cloudflare": "http_forbidden_or_bot_policy",
            "HTTP 404 not found": "http_not_found",
            "downloads manifest missing requested bundle": "manifest_missing",
            "library zip sha256 mismatch": "checksum_mismatch",
            "library download too large": "bundle_too_large",
            "unsafe archive traversal member": "unsafe_archive_member",
            "library catalogue must contain an entries list": "schema_contract_mismatch",
            "timed out while fetching": "timeout",
        }
        for message, code in cases.items():
            classified = mod.classify_library_exception(ValueError(message))
            self.assertEqual(classified["code"], code, message)
            self.assertTrue(classified["next_action"])

    def test_remote_metadata_cannot_set_local_verified_state(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "is_verified": True,
            "validated_pack": True,
            "quality_score": 100,
            "validation": {"state": "validated", "evidence": "looks-real.json"},
        }
        remote = mod.remote_trust_summary(detail)
        local = mod.local_verification_summary(detail.get("validation"))
        self.assertTrue(remote["remote_is_verified"])
        self.assertTrue(remote["advisory_only"])
        self.assertFalse(remote["local_is_verified"])
        self.assertFalse(local["is_verified"])
        self.assertEqual(local["state"], "unverified")
        self.assertFalse(local["remote_metadata_can_verify"])

    def test_apply_import_for_reference_only_bundle_is_a_safe_noop(self):
        mod = load_library()
        detail = {
            "id": "pan_panos",
            "version": "1.2.3",
            "display_name": "Palo Alto PAN-OS",
            "vendor": "Palo Alto",
            "product": "PAN-OS",
            "capabilities": ["parsing"],
            "artifacts": [],
            "download": {
                "filename": "pan_panos-1.2.3.zip",
                "url": "https://sechub.s6ops.com/downloads/pan_panos-1.2.3.zip",
            },
        }
        bundle = build_bundle()
        detail["download"]["sha256"] = mod.sha256_bytes(bundle)

        def fetch_json(url: str, source: dict[str, Any], max_bytes: int) -> dict[str, Any]:
            if url.endswith("catalogue.json"):
                return {"entries": [{"id": "pan_panos", "download_available": True}]}
            if url.endswith("manifest.json"):
                return {"downloads": []}
            if url.endswith("entries/pan_panos.json"):
                return detail
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as d:
            manager = mod.LibraryManager(
                root=Path(d) / "sc4s",
                manager_root=Path(d) / "manager",
                fetch_json=fetch_json,
                fetch_bytes=lambda url, source, max_bytes: bundle,
            )
            manager.sync_source("official")
            validated = manager.validate_import("official", "pan_panos")
            record_path = manager.imports_dir / validated["import_id"] / "record.json"
            record = json.loads(record_path.read_text())
            record["apply_allowed"] = False
            record["reference_only"] = True
            record["runtime_files"] = []
            record_path.write_text(json.dumps(record, indent=2) + "\n")
            applied = manager.apply_import(validated["import_id"], actor="tester", apply=True)
            self.assertTrue(applied["ok"])
            self.assertFalse(applied["apply_allowed"])
            self.assertTrue(applied["reference_only"])
            self.assertEqual(applied["changed_targets"], [])


if __name__ == "__main__":
    unittest.main()
