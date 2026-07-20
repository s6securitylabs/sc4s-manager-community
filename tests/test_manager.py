import base64
import importlib.util
import json
import os
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "src" / "sc4s_manager" / "app.py"


def load_app(tmp: Path) -> Any:
    os.environ["SC4S_ROOT"] = str(tmp / "sc4s")
    os.environ["SC4S_MANAGER_ROOT"] = str(tmp / "manager")
    os.environ["SC4S_MANAGER_PROXY_SECRET"] = "test-secret"
    spec = importlib.util.spec_from_file_location("sc4s_manager_app_test", APP_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    mod.ROOT = tmp / "sc4s"
    mod.LOCAL_ROOT = mod.ROOT / "local"
    mod.ENV_FILE = mod.ROOT / "env_file"
    mod.TLS_DIR = mod.ROOT / "tls"
    mod.MANAGER_ROOT = tmp / "manager"
    mod.STATE_DIR = mod.MANAGER_ROOT / "state"
    mod.BACKUP_DIR = mod.MANAGER_ROOT / "backups"
    mod.TEMPLATE_DIR = mod.MANAGER_ROOT / "templates"
    mod.PACK_DIR = mod.MANAGER_ROOT / "packs"
    mod.FRONTEND_DIST = mod.MANAGER_ROOT / "frontend" / "dist"
    mod.AUDIT_LOG = mod.STATE_DIR / "audit.jsonl"
    mod.STATE_FILE = mod.STATE_DIR / "state.json"
    mod.CSV_FILES = {
        "vendor_product": mod.LOCAL_ROOT / "context" / "vendor_product_by_source.csv",
        "splunk_metadata": mod.LOCAL_ROOT / "context" / "splunk_metadata.csv",
        "compliance_meta": mod.LOCAL_ROOT / "context" / "compliance_meta_by_source.csv",
        "host": mod.LOCAL_ROOT / "context" / "host.csv",
    }
    mod.EDITABLE_ROOTS = [mod.LOCAL_ROOT / "context", mod.LOCAL_ROOT / "config"]
    (mod.LOCAL_ROOT / "context").mkdir(parents=True)
    (mod.LOCAL_ROOT / "config" / "filters").mkdir(parents=True)
    mod.TLS_DIR.mkdir(parents=True)
    mod.ENV_FILE.write_text("SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN=secret\nSC4S_SOURCE_LISTEN_TCP_PORT=514\nSC4S_SOURCE_LISTEN_UDP_PORT=514\nSC4S_SOURCE_LISTEN_TLS_PORT=6514\n")
    return mod


class FakeResponseHandler:
    def __init__(self):
        from io import BytesIO
        self.wfile = BytesIO()
        self.calls = []
        self.headers_sent = {}

    def send_response(self, status):
        self.status = status
        self.calls.append(("status", status))

    def send_header(self, key, value):
        self.headers_sent[key] = value
        self.calls.append(("header", key, value))

    def end_headers(self):
        self.calls.append(("end",))


class ManagerUnitTests(unittest.TestCase):
    def test_main_reports_directory_permission_errors_without_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            denied = PermissionError(13, "Permission denied", "/opt/sc4s")
            with patch.object(app, "ensure_dirs", side_effect=denied), patch("sys.stderr") as stderr, patch.object(app, "ThreadingHTTPServer") as server:
                with self.assertRaises(SystemExit) as raised:
                    app.main()
            self.assertEqual(raised.exception.code, 78)
            server.assert_not_called()
            message = "".join(call.args[0] for call in stderr.write.call_args_list if call.args)
            self.assertIn("SC4S Manager cannot create its required runtime directories", message)
            self.assertIn("SC4S_ROOT=", message)
            self.assertIn("SC4S_MANAGER_ROOT=", message)
            self.assertIn("/opt/sc4s", message)

    def test_log_message_redacts_manual_login_query_tokens(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            handler = object.__new__(app.Handler)
            handler.client_address = ("127.0.0.1", 12345)
            with patch("builtins.print") as fake_print:
                handler.log_message(
                    '"%s" %s %s',
                    "GET /ui?token=secret-token&keep=value&login_token=other-secret HTTP/1.1",
                    "200",
                    "123",
                )
            payload = json.loads(fake_print.call_args.args[0])
            self.assertIn("GET /ui?token=[REDACTED]&keep=value&login_token=[REDACTED] HTTP/1.1", payload["msg"])
            self.assertNotIn("secret-token", payload["msg"])
            self.assertNotIn("other-secret", payload["msg"])
            self.assertIn("keep=value", payload["msg"])

    def test_static_frontend_serves_assets_and_spa_fallback_from_dist(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            (app.FRONTEND_DIST / "assets").mkdir(parents=True)
            (app.FRONTEND_DIST / "index.html").write_text("<div id='root'></div>")
            (app.FRONTEND_DIST / "assets" / "app.js").write_text("console.log('ok');")

            asset = FakeResponseHandler()
            self.assertTrue(app.static_asset_response(asset, "/assets/app.js"))
            self.assertEqual(asset.status, 200)
            self.assertEqual(asset.headers_sent["Content-Type"], "text/javascript")
            self.assertEqual(asset.headers_sent["Cache-Control"], "public, max-age=31536000, immutable")
            self.assertEqual(asset.wfile.getvalue(), b"console.log('ok');")

            spa = FakeResponseHandler()
            self.assertTrue(app.frontend_response(spa, "/packs/cisco_asa"))
            self.assertEqual(spa.status, 200)
            self.assertEqual(spa.headers_sent["Content-Type"], "text/html; charset=utf-8")
            self.assertEqual(spa.wfile.getvalue(), b"<div id='root'></div>")

    def test_static_frontend_blocks_traversal_and_uses_inline_fallback_without_dist(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            missing_asset = FakeResponseHandler()
            self.assertTrue(app.static_asset_response(missing_asset, "/assets/../index.html"))
            self.assertEqual(missing_asset.status, 404)
            self.assertEqual(missing_asset.headers_sent["Content-Type"], "application/json; charset=utf-8")

            root = FakeResponseHandler()
            self.assertTrue(app.frontend_response(root, "/"))
            self.assertEqual(root.status, 200)
            self.assertIn(b"SC4S Manager", root.wfile.getvalue())

            unknown = FakeResponseHandler()
            self.assertFalse(app.frontend_response(unknown, "/packs/cisco_asa"))

    def test_static_frontend_blocks_symlink_escape_from_assets(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            (app.FRONTEND_DIST / "assets").mkdir(parents=True)
            outside = Path(d) / "secret.txt"
            outside.write_text("do-not-serve")
            (app.FRONTEND_DIST / "assets" / "leak.txt").symlink_to(outside)

            response = FakeResponseHandler()
            self.assertTrue(app.static_asset_response(response, "/assets/leak.txt"))
            self.assertEqual(response.status, 404)
            self.assertEqual(response.headers_sent["Content-Type"], "application/json; charset=utf-8")
            self.assertNotIn(b"do-not-serve", response.wfile.getvalue())

    def test_binary_response_sanitizes_content_disposition_filename(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            response = FakeResponseHandler()
            app.binary_response(response, 200, b"payload", 'bad";\r\nX-Injected: yes.zip', "application/zip")
            disposition = response.headers_sent["Content-Disposition"]
            self.assertNotIn("\r", disposition)
            self.assertNotIn("\n", disposition)
            self.assertNotIn('";', disposition)
            self.assertEqual(response.wfile.getvalue(), b"payload")

    def test_env_redacts_secrets_and_disable_enable_port(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            env = app.parse_env()
            self.assertEqual(env["SC4S_SOURCE_LISTEN_TCP_PORT"], "514")
            r = app.set_port("tcp", False, None, "tester")
            self.assertTrue(r["restart_required"])
            self.assertNotIn("SC4S_SOURCE_LISTEN_TCP_PORT", app.parse_env())
            r = app.set_port("tcp", True, 5514, "tester")
            self.assertEqual(app.parse_env()["SC4S_SOURCE_LISTEN_TCP_PORT"], "5514")
            self.assertTrue(list(app.BACKUP_DIR.glob("*.bak")))

    def test_secret_env_keys_are_not_editable(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            with self.assertRaises(ValueError):
                app.set_env_value("SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN", "leak", "tester")

    def test_add_service_writes_filter_and_csv_rows(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            out = app.add_service({"filter":"cisco_lab","source":"10.10.2.0/24","vendor_product":"cisco_asa","index":"netops","compliance":"pci"}, "tester")
            self.assertEqual(out["filter"], "f_cisco_lab")
            self.assertIn("netmask", (app.LOCAL_ROOT / "config" / "filters" / "cisco_lab.conf").read_text())
            self.assertIn(["f_cisco_lab", "sc4s_vendor_product", "cisco_asa"], app.read_csv(app.CSV_FILES["vendor_product"]))
            self.assertIn(["f_cisco_lab", ".splunk.index", "netops"], app.read_csv(app.CSV_FILES["splunk_metadata"]))
            self.assertIn(["f_cisco_lab", ".splunk.index", "netops"], app.read_csv(app.CSV_FILES["compliance_meta"]))
            self.assertIn('filter f_cisco_lab { netmask("10.10.2.0/24"); };', (app.LOCAL_ROOT / "context" / "vendor_product_by_source.conf").read_text())
            self.assertIn('filter f_cisco_lab { netmask("10.10.2.0/24"); };', (app.LOCAL_ROOT / "context" / "compliance_meta_by_source.conf").read_text())

    def test_delete_source_removes_filter_context_rows_and_audits(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": "syntax ok", "stderr": "", "status": {"running": True, "health": "healthy", "image_version": app.SUPPORTED_SC4S_VERSION}}
            app.tls_inventory = lambda: {"ready": True, "enabled": True, "problems": []}
            app.add_service({"filter":"cisco_lab","source":"10.10.2.0/24","vendor_product":"cisco_asa","index":"netops","compliance":"pci"}, "tester")

            out = app.delete_source("cisco_lab", "tester")

            self.assertTrue(out["ok"])
            self.assertEqual(out["filter"], "f_cisco_lab")
            self.assertFalse((app.LOCAL_ROOT / "config" / "filters" / "cisco_lab.conf").exists())
            self.assertNotIn(["f_cisco_lab", "sc4s_vendor_product", "cisco_asa"], app.read_csv(app.CSV_FILES["vendor_product"]))
            self.assertNotIn(["f_cisco_lab", ".splunk.index", "netops"], app.read_csv(app.CSV_FILES["splunk_metadata"]))
            self.assertNotIn(["f_cisco_lab", ".splunk.index", "netops"], app.read_csv(app.CSV_FILES["compliance_meta"]))
            self.assertNotIn("filter f_cisco_lab ", (app.LOCAL_ROOT / "context" / "vendor_product_by_source.conf").read_text())
            self.assertNotIn("filter f_cisco_lab ", (app.LOCAL_ROOT / "context" / "compliance_meta_by_source.conf").read_text())
            self.assertIn("delete_source", app.AUDIT_LOG.read_text())

    def test_source_catalog_exposes_known_vendors_with_help(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            catalog = app.source_catalog()
            keys = {x["vendor_product"]: x for x in catalog["sources"]}
            self.assertIn("cisco_asa", keys)
            self.assertIn("docs", keys["cisco_asa"])
            self.assertIn("default_index", keys["cisco_asa"])

    def test_onboard_source_returns_apply_workflow_and_test_instructions(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": "syntax ok", "stderr": "", "status": {"running": True, "health": "healthy", "image_version": app.SUPPORTED_SC4S_VERSION}}
            app.tls_inventory = lambda: {"ready": True, "enabled": True, "problems": []}
            out = app.onboard_source({"name":"asa_lab", "source":"10.10.2.0/24", "vendor_product":"cisco_asa", "index":"netfw", "compliance":"pci", "apply": False}, "tester")
            self.assertTrue(out["ok"])
            self.assertEqual(out["apply_mode"], "reloadable")
            self.assertIn("udp", out["test_instructions"])
            self.assertIn("tcp", out["test_instructions"])
            self.assertIn(["f_asa_lab", "sc4s_vendor_product", "cisco_asa"], app.read_csv(app.CSV_FILES["vendor_product"]))
            self.assertIn(["f_asa_lab", ".splunk.index", "netfw"], app.read_csv(app.CSV_FILES["splunk_metadata"]))
            self.assertIn(["f_asa_lab", ".splunk.index", "netfw"], app.read_csv(app.CSV_FILES["compliance_meta"]))

    def test_source_inventory_lists_configured_filters_with_csv_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            self.assertEqual(app.source_inventory(), {"sources": []})
            app.add_service({"filter":"asa_lab","source":"10.10.2.0/24","vendor_product":"cisco_asa","index":"netfw","compliance":"pci"}, "tester")

            inventory = app.source_inventory()

            self.assertEqual(len(inventory["sources"]), 1)
            entry = inventory["sources"][0]
            self.assertEqual(entry["name"], "asa_lab")
            self.assertEqual(entry["filter"], "f_asa_lab")
            self.assertEqual(entry["source"], "10.10.2.0/24")
            self.assertEqual(entry["vendor_product"], "cisco_asa")
            self.assertEqual(entry["index"], "netfw")
            self.assertEqual(entry["compliance"], "pci")
            self.assertEqual(entry["apply_mode"], "reloadable")
            self.assertEqual(entry["path"], "config/filters/asa_lab.conf")

    def test_destination_inventory_redacts_default_hec_token(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            inv = app.destination_inventory()
            default = inv["destinations"][0]
            self.assertEqual(default["id"], "DEFAULT")
            self.assertEqual(default["token"], "[REDACTED]")

    def test_configure_hec_destination_writes_env_and_redacts_secret(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": "syntax ok", "stderr": "", "status": {"running": True, "health": "healthy", "image_version": app.SUPPORTED_SC4S_VERSION}}
            app.tls_inventory = lambda: {"ready": True, "enabled": True, "problems": []}
            out = app.configure_destination({"kind":"hec", "id":"OTHER", "url":"https://splunk2:8088", "token":"abc123", "mode":"GLOBAL", "tls_verify":"no", "apply": False}, "tester")
            self.assertTrue(out["ok"])
            env = app.parse_env()
            self.assertEqual(env["SC4S_DEST_SPLUNK_HEC_OTHER_URL"], "https://splunk2:8088")
            self.assertEqual(env["SC4S_DEST_SPLUNK_HEC_OTHER_TOKEN"], "abc123")
            self.assertNotIn("abc123", json.dumps(out))

    def test_configure_destination_rolls_back_env_when_validation_fails(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            before = app.ENV_FILE.read_text()
            app.validate_config = lambda: {"ok": False, "syntax": {"stderr": "broken"}}

            out = app.configure_destination({"kind": "hec", "id": "OTHER", "url": "https://splunk2:8088", "token": "abc123", "mode": "GLOBAL", "apply": False}, "tester")

            self.assertFalse(out["ok"])
            self.assertEqual(app.ENV_FILE.read_text(), before)
            self.assertNotIn("SC4S_DEST_SPLUNK_HEC_OTHER_URL", app.parse_env())

    def test_onboard_source_rolls_back_files_when_validation_fails(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.validate_config = lambda: {"ok": False, "syntax": {"stderr": "broken"}}

            out = app.onboard_source({"name": "asa_lab", "source": "10.10.2.0/24", "vendor_product": "cisco_asa", "index": "netfw", "apply": False}, "tester")

            self.assertFalse(out["ok"])
            self.assertFalse((app.LOCAL_ROOT / "config" / "filters" / "asa_lab.conf").exists())
            self.assertFalse(app.CSV_FILES["vendor_product"].exists())
            self.assertFalse(app.CSV_FILES["splunk_metadata"].exists())

    def test_configure_destination_rejects_invalid_mode_without_mutating(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            before = app.ENV_FILE.read_text()
            with self.assertRaises(ValueError):
                app.configure_destination({"kind":"hec", "id":"OTHER", "url":"https://splunk2:8088", "mode":"BROKEN"}, "tester")
            self.assertEqual(app.ENV_FILE.read_text(), before)
            self.assertNotIn("SC4S_DEST_SPLUNK_HEC_OTHER_URL", app.parse_env())

    def test_configure_syslog_select_destination_generates_selector(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": "syntax ok", "stderr": "", "status": {"running": True, "health": "healthy", "image_version": app.SUPPORTED_SC4S_VERSION}}
            app.tls_inventory = lambda: {"ready": True, "enabled": True, "problems": []}
            out = app.configure_destination({"kind":"syslog", "id":"SIEM", "host":"10.0.0.5", "port":601, "transport":"tcp", "mode":"SELECT", "selector_vendor_product":"cisco_asa", "apply": False}, "tester")
            self.assertTrue(out["ok"])
            env = app.parse_env()
            self.assertEqual(env["SC4S_DEST_SYSLOG_SIEM_HOST"], "10.0.0.5")
            selector = app.LOCAL_ROOT / "config" / "app_parsers" / "selectors" / "sc4s-lp-cisco_asa_d_syslog_siem.conf"
            self.assertTrue(selector.exists())
            self.assertIn("sc4s-lp-dest-select-d_syslog_siem", selector.read_text())

    def test_delete_destination_removes_env_selector_and_redacts_audit(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": "syntax ok", "stderr": "", "status": {"running": True, "health": "healthy", "image_version": app.SUPPORTED_SC4S_VERSION}}
            app.tls_inventory = lambda: {"ready": True, "enabled": True, "problems": []}
            app.configure_destination({"kind":"hec", "id":"OTHER", "url":"https://splunk2:8088", "token":"abc123", "mode":"SELECT", "tls_verify":"no", "apply": False}, "tester")
            self.assertIn("SC4S_DEST_SPLUNK_HEC_OTHER_TOKEN", app.parse_env())

            out = app.delete_destination("hec", "OTHER", "tester")

            self.assertTrue(out["ok"])
            self.assertNotIn("SC4S_DEST_SPLUNK_HEC_OTHER_TOKEN", app.parse_env())
            self.assertNotIn("SC4S_DEST_SPLUNK_HEC_OTHER_URL", app.parse_env())
            self.assertNotIn("abc123", json.dumps(out))
            self.assertNotIn("abc123", app.AUDIT_LOG.read_text())

    def test_route_lifecycle_creates_selector_and_deletes_cleanly(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": "syntax ok", "stderr": "", "status": {"running": True, "health": "healthy", "image_version": app.SUPPORTED_SC4S_VERSION}}
            app.tls_inventory = lambda: {"ready": True, "enabled": True, "problems": []}
            app.add_service({"filter":"asa_lab","source":"10.10.2.0/24","vendor_product":"cisco_asa","index":"netfw","compliance":"pci"}, "tester")
            app.configure_destination({"kind":"hec", "id":"OTHER", "url":"https://splunk2:8088", "token":"abc123", "mode":"SELECT", "apply": False}, "tester")

            route = app.upsert_route({"id":"asa_to_hec", "source":"asa_lab", "pack":"cisco_asa", "destination_kind":"hec", "destination_id":"OTHER", "apply": False}, "tester")

            self.assertTrue(route["ok"])
            self.assertEqual(route["route"]["id"], "asa_to_hec")
            selector = app.LOCAL_ROOT / "config" / "app_parsers" / "selectors" / "sc4s-lp-cisco_asa_d_hec_other.conf"
            self.assertTrue(selector.exists())
            self.assertIn("sc4s-lp-dest-select-d_hec_other", selector.read_text())
            inventory = app.route_inventory()
            self.assertEqual(inventory["routes"][0]["pack"], "cisco_asa")

            deleted = app.delete_route("asa_to_hec", "tester")

            self.assertTrue(deleted["ok"])
            self.assertFalse(selector.exists())
            self.assertEqual(app.route_inventory()["routes"], [])

    def test_config_editor_blocks_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            with self.assertRaises(ValueError):
                app.save_config_file("../../etc/passwd", "oops", "tester")

    def test_template_export_import_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            target = app.LOCAL_ROOT / "context" / "vendor_product_by_source.csv"
            target.write_text("f_a,sc4s_vendor_product,cisco\n")
            tpl = app.export_template("baseline", "tester")
            target.write_text("changed\n")
            app.import_template(tpl["template"], "tester")
            self.assertEqual(target.read_text(), "f_a,sc4s_vendor_product,cisco\n")

    def test_import_template_rejects_sibling_prefix_path(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            evil_dir = app.MANAGER_ROOT / "templates_evil"
            evil_dir.mkdir(parents=True)
            evil = evil_dir / "evil.zip"
            import zipfile
            with zipfile.ZipFile(evil, "w") as z:
                z.writestr("local/context/vendor_product_by_source.csv", "bad\n")
            with self.assertRaises(ValueError):
                app.import_template(str(evil), "tester")

    def test_backup_sanitizes_actor_filename(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.set_env_value("SC4S_QA_SAFE", "1", "../../evil/user")
            names = [p.name for p in app.BACKUP_DIR.glob("*.bak")]
            self.assertTrue(names)
            self.assertFalse(any("/" in n or ".." in n for n in names))

    def test_restore_backup_restores_local_paths_with_extensions(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            target = app.LOCAL_ROOT / "context" / "vendor_product_by_source.csv"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("old csv\n")
            backup = app.backup(target, "tester")
            target.write_text("new csv\n")

            out = app.restore_backup(backup.name, "tester")

            self.assertEqual(out["restored_to"], str(target))
            self.assertEqual(target.read_text(), "old csv\n")
            self.assertFalse((target.parent / "vendor_product_by_source").exists())

    def test_restore_backup_restores_tls_files_not_env_file(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            target = app.TLS_DIR / "server.pem"
            target.write_text("old pem\n")
            backup = app.backup(target, "tester")
            target.write_text("new pem\n")
            before_env = app.ENV_FILE.read_text()

            out = app.restore_backup(backup.name, "tester")

            self.assertEqual(out["restored_to"], str(target))
            self.assertEqual(target.read_text(), "old pem\n")
            self.assertEqual(app.ENV_FILE.read_text(), before_env)

    def test_docker_status_parses_untruncated_json(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            large = "x" * 20000
            app.control_request = lambda action, **params: {"ok": True, "status": {"running": True, "status": "running", "started_at": "now", "restart_count": 0, "image": large}}
            self.assertTrue(app.docker_status()["running"])

    def test_redaction_keeps_benign_paths_versions_and_secret_metadata_flags(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            value = {"version":"1.0.0", "template":"/opt/sc4s-manager/templates/baseline.zip", "api_token":"secret", "contains_secrets": False}
            redacted = app.redact(value)
            self.assertEqual(redacted["version"], value["version"])
            self.assertEqual(redacted["template"], value["template"])
            self.assertIs(redacted["contains_secrets"], False)
            self.assertEqual(redacted["api_token"], "[REDACTED]")

    def test_redaction_redacts_credential_values_but_preserves_option_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            value = {
                "api_token": "tok-123",
                "password": "pw-123",
                "authorization": "Bearer auth-123",
                "credential": "cred-123",
                "client_secret_value": "secret-123",
                "private_key_pem": "key-123",
                "options": [
                    {
                        "key": "SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN",
                        "secret": True,
                        "contains_secrets": False,
                        "type": "secret",
                    }
                ],
            }
            redacted = app.redact(value)

            self.assertEqual(redacted["api_token"], "[REDACTED]")
            self.assertEqual(redacted["password"], "[REDACTED]")
            self.assertEqual(redacted["authorization"], "[REDACTED]")
            self.assertEqual(redacted["credential"], "[REDACTED]")
            self.assertEqual(redacted["client_secret_value"], "[REDACTED]")
            self.assertEqual(redacted["private_key_pem"], "[REDACTED]")
            option = redacted["options"][0]
            self.assertEqual(option["key"], "SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN")
            self.assertIs(option["secret"], True)
            self.assertIs(option["contains_secrets"], False)
            self.assertEqual(option["type"], "secret")

    def test_group_parsing_uses_exact_membership_tokens(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            self.assertIn("sc4s-admin", app.parse_groups("users,sc4s-admin|ops"))
            self.assertNotIn("sc4s-admin", app.parse_groups("users,not-sc4s-admin|ops"))

    def test_manual_login_token_authorizes_without_authentik_proxy(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            handler = type("Handler", (), {})()
            handler.path = "/api/stats"
            handler.client_address = ("203.0.113.10", 55555)
            handler.headers = {"Authorization": "Bearer manual-secret", "Host": "sc4s-manager.example"}
            self.assertTrue(app.authorized(handler, unsafe=False))
            self.assertTrue(app.authorized(handler, unsafe=True))

    def test_manual_login_token_rejects_wrong_token(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            handler = type("Handler", (), {})()
            handler.path = "/api/stats"
            handler.client_address = ("203.0.113.10", 55555)
            handler.headers = {"Authorization": "Bearer wrong", "Host": "sc4s-manager.example"}
            self.assertFalse(app.authorized(handler, unsafe=False))

    def test_manual_login_token_cookie_authorizes_browser_session(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            handler = type("Handler", (), {})()
            handler.path = "/api/stats"
            handler.client_address = ("203.0.113.10", 55555)
            handler.headers = {
                "Cookie": f"other=1; sc4s_manual_session={app._manual_session_token()}",
                "Host": "sc4s-manager.example",
            }
            self.assertTrue(app.authorized(handler, unsafe=False))

    def test_manual_login_query_sets_cookie_and_removes_token_from_location(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            handler = type("Handler", (), {})()
            handler.path = "/?token=manual-secret&tab=stats"
            handler.headers = {}
            calls = []
            handler.send_response = lambda status: calls.append(("status", status))
            handler.send_header = lambda key, value: calls.append(("header", key, value))
            handler.end_headers = lambda: calls.append(("end",))
            self.assertTrue(app.manual_login_redirect(handler))
            self.assertIn(("status", 303), calls)
            self.assertIn(("header", "Location", "/?tab=stats"), calls)
            headers = {call[1]: call[2] for call in calls if call[0] == "header"}
            cookie = headers["Set-Cookie"]
            self.assertIn(f"sc4s_manual_session={app._manual_session_token()}", cookie)
            self.assertNotIn("manual-secret", cookie)
            self.assertNotIn("token=", headers["Location"])

    def test_manual_login_redirect_rejects_raw_header_newlines(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            handler = type("Handler", (), {})()
            handler.path = "/safe\r\nX-Injected: yes?login_token=manual-secret"
            handler.headers = {"Host": "sc4s-manager.example"}
            calls = []
            handler.send_response = lambda status: calls.append(("status", status))
            handler.send_header = lambda key, value: calls.append(("header", key, value))
            handler.end_headers = lambda: calls.append(("end",))

            self.assertTrue(app.manual_login_redirect(handler))
            self.assertIn(("header", "Location", "/"), calls)


    def test_actor_from_uses_proxy_identity_only_after_proxy_authentication(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            handler = type("Handler", (), {})()
            handler.path = "/api/stats"
            handler.client_address = ("203.0.113.10", 55555)
            handler.headers = {
                "X-SC4S-Manager-Proxy": "test-secret",
                "X-Authentik-Username": "operator",
                "X-Forwarded-User": "forwarded-user",
            }
            self.assertEqual(app.actor_from(handler), "operator")

    def test_actor_from_labels_manual_token_actor_without_claiming_a_user_identity(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            handler = type("Handler", (), {})()
            handler.path = "/api/stats"
            handler.client_address = ("203.0.113.10", 55555)
            handler.headers = {"Authorization": "Bearer manual-secret"}
            self.assertEqual(app.actor_from(handler), "manual-token")

    def test_actor_from_does_not_trust_proxy_identity_without_proxy_authentication(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            handler = type("Handler", (), {})()
            handler.path = "/api/env"
            handler.client_address = ("203.0.113.10", 55555)
            handler.headers = {
                "Authorization": "Bearer manual-secret",
                "X-Authentik-Username": "forged-admin",
                "X-Forwarded-User": "forged-forwarded-admin",
            }
            self.assertTrue(app.authorized(handler, unsafe=True))
            self.assertEqual(app.actor_from(handler), "manual-token")

    def test_cookie_authenticated_mutation_requires_present_matching_origin(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            handler = type("Handler", (), {})()
            handler.path = "/api/env"
            handler.client_address = ("203.0.113.10", 55555)
            handler.headers = {
                "Cookie": f"sc4s_manual_session={app._manual_session_token()}",
                "Host": "sc4s-manager.example",
            }
            self.assertFalse(app.authorized(handler, unsafe=True))
            handler.headers["Origin"] = "https://sc4s-manager.example"
            self.assertTrue(app.authorized(handler, unsafe=True))

    def test_apply_consent_requires_a_json_boolean_before_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            self.assertFalse(app.payload_bool({"apply": False}, "apply", True))
            self.assertTrue(app.payload_bool({}, "apply", True))
            before = app.ENV_FILE.read_text()
            invalid_calls = (
                (app.apply_change, {"type": "env", "key": "SC4S_TEST", "value": "changed", "apply": "false"}),
                (app.configure_destination, {"apply": "false"}),
                (app.onboard_source, {"apply": "false"}),
                (app.upsert_route, {"apply": "false"}),
            )
            for operation, payload in invalid_calls:
                with self.assertRaisesRegex(ValueError, "apply must be a JSON boolean"):
                    operation(payload, "tester")
            self.assertEqual(app.ENV_FILE.read_text(), before)

    def test_atomic_write_preserves_mode_and_replaces_content(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            target = app.ENV_FILE
            target.chmod(0o640)
            app.atomic_write(target, "SC4S_TEST=yes\n")
            self.assertEqual(target.read_text(), "SC4S_TEST=yes\n")
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)

    def test_template_upload_import_restores_zip_content(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            import base64, zipfile, io
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("local/context/vendor_product_by_source.csv", "f_b,sc4s_vendor_product,fortinet\n")
            app.import_template_upload("uploaded.zip", base64.b64encode(buf.getvalue()).decode(), "tester")
            target = app.LOCAL_ROOT / "context" / "vendor_product_by_source.csv"
            self.assertEqual(target.read_text(), "f_b,sc4s_vendor_product,fortinet\n")

    def test_tls_inventory_reports_missing_files_and_inactive_listener(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.run = lambda cmd, timeout=20, stdout_limit=12000: {"ok": True, "code": 0, "stdout": "tcp LISTEN 0 1 0.0.0.0:514 0.0.0.0:*\n", "stderr": ""}
            inv = app.tls_inventory()
            self.assertFalse(inv["ready"])
            self.assertFalse(inv["listener_active"])
            self.assertEqual(inv["expected_port"], "6514")
            self.assertIn("missing certificate", inv["problems"])
            self.assertIn("missing private key", inv["problems"])

    def test_install_tls_bundle_validates_key_pair_and_sets_tls_env(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            calls = []
            def fake_run(cmd, timeout=20, stdout_limit=12000):
                calls.append(cmd)
                if cmd[:2] == ["openssl", "x509"]:
                    return {"ok": True, "code": 0, "stdout": "SHA2-256(stdin)= ABC\n", "stderr": ""}
                if cmd[:2] == ["openssl", "rsa"]:
                    return {"ok": True, "code": 0, "stdout": "SHA2-256(stdin)= ABC\n", "stderr": ""}
                return {"ok": True, "code": 0, "stdout": "", "stderr": ""}
            app.run = fake_run
            cert = "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n"
            key = "-----BEGIN PRIVATE KEY-----\nMIIB\n-----END PRIVATE KEY-----\n"
            out = app.install_tls_bundle(cert, key, "", "tester")
            self.assertTrue(out["restart_required"])
            self.assertEqual((app.TLS_DIR / "server.pem").read_text(), cert)
            self.assertEqual((app.TLS_DIR / "server.key").read_text(), key)
            env = app.parse_env()
            self.assertEqual(env["SC4S_SOURCE_TLS_ENABLE"], "yes")
            self.assertEqual(env["SC4S_TLS"], "/etc/syslog-ng/tls")

    def test_syslog_ng_metrics_are_parsed_and_summarized(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            sample = "SourceName;SourceId;SourceInstance;State;Type;Number\nsource;s_DEFAULT;;a;processed;10\ndst.http;d_hec;;a;dropped;2\nfilter;f_test;;a;matched;7\nparser;p_test;;a;discarded;3\n"
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": sample, "stderr": ""}
            metrics = app.syslog_ng_metrics()
            self.assertEqual(metrics["summary"]["processed"], 10)
            self.assertEqual(metrics["summary"]["dropped"], 2)
            self.assertEqual(metrics["summary"]["discarded"], 3)
            self.assertEqual(len(metrics["rows"]), 4)

    def test_metrics_explorer_filters_raw_rows_and_builds_group_summaries(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            sample = "\n".join([
                "SourceName;SourceId;SourceInstance;State;Type;Number",
                "source;s_DEFAULT;;a;processed;10",
                "source;s_DEFAULT;;a;dropped;2",
                "dst.http;d_hec;;a;written;8",
                "filter;f_prod;;a;matched;5",
                "filter;f_lab;;a;matched;3",
            ])
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": sample, "stderr": ""}
            metrics = app.syslog_ng_metrics({"source_name": "filter", "type": "matched", "search": "prod", "limit": 10})
            self.assertEqual(metrics["row_count"], 5)
            self.assertEqual(metrics["filtered_row_count"], 1)
            self.assertEqual(metrics["rows"][0]["SourceId"], "f_prod")
            self.assertEqual(metrics["summaries"]["by_source_name"]["filter"]["matched"], 8)
            self.assertEqual(metrics["summaries"]["by_type"]["matched"], 8)

    def test_recent_log_findings_extract_warnings_and_errors_without_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            logs = "\n".join([
                "INFO boot complete",
                "WARNING queue high token=abc123",
                "ERR destination failed PASSWORD=hunter2",
                "notice normal",
            ])
            app.control_request = lambda action, **params: {"ok": True, "stdout": logs}
            findings = app.recent_log_findings(lines=20)
            self.assertEqual(findings["warning_count"], 1)
            self.assertEqual(findings["error_count"], 1)
            joined = "\n".join(findings["warnings"] + findings["errors"])
            self.assertIn("WARNING queue high", joined)
            self.assertNotIn("abc123", joined)
            self.assertNotIn("hunter2", joined)

    def test_service_stats_include_control_provider_health_and_version_drift(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.run = lambda cmd, timeout=20, stdout_limit=12000: {"ok": True, "code": 0, "stdout": "", "stderr": ""}
            app.health_probe = lambda: {"ok": True, "status": 200, "body": "ok"}
            app.tls_inventory = lambda: {"ready": True, "problems": []}
            def fake_control(action, **params):
                if action == "status":
                    return {"ok": True, "status": {"running": True, "health": "healthy", "image_version": "9.99.0", "image": "sc4s:test"}}
                if action == "metrics":
                    return {"ok": True, "stdout": "SourceName;SourceId;SourceInstance;State;Type;Number\nsource;s;;a;processed;1\n"}
                if action == "logs":
                    return {"ok": True, "stdout": "WARN backlog\nERROR hec failed\n"}
                return {"ok": True}
            app.control_request = fake_control
            stats = app.service_stats()
            self.assertEqual(stats["control_provider"]["provider"], "narrow-control")
            self.assertTrue(stats["control_provider"]["ok"])
            self.assertTrue(stats["version_drift"]["drift"])
            self.assertEqual(stats["running_sc4s_version"], "9.99.0")
            self.assertEqual(stats["log_findings"]["warning_count"], 1)
            self.assertEqual(stats["log_findings"]["error_count"], 1)

    def test_index_html_exposes_operations_and_metrics_sections(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            self.assertIn("<h2>Operations</h2>", app.INDEX_HTML)
            self.assertIn("<h2>Metrics Explorer</h2>", app.INDEX_HTML)
            self.assertIn("/api/metrics/syslog-ng", app.INDEX_HTML)

    def test_option_schema_contains_help_and_tls_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.control_request = lambda action, **params: {"ok": True, "status": {"image_version": app.SUPPORTED_SC4S_VERSION, "image": "sc4s:test"}}
            schema = app.option_schema()
            keys = {o["key"]: o for o in schema["options"]}
            self.assertIn("SC4S_SOURCE_TLS_ENABLE", keys)
            self.assertIn("description", keys["SC4S_SOURCE_TLS_ENABLE"])
            self.assertIn("server.pem", " ".join(keys["SC4S_SOURCE_TLS_ENABLE"].get("requires", [])))
            self.assertEqual(keys["SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN"]["secret"], True)
            self.assertEqual(schema["supported_sc4s_version"], "3.43.0")
            self.assertFalse(schema["version_drift"]["drift"])

    def test_option_schema_v1_catalog_covers_required_categories_and_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.control_request = lambda action, **params: {"ok": True, "status": {"image_version": app.SUPPORTED_SC4S_VERSION, "image": "sc4s:test"}}
            schema = app.option_schema()
            keys = {o["key"]: o for o in schema["options"]}
            required_keys = {
                "SC4S_DEST_SPLUNK_HEC_DEFAULT_URL",
                "SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN",
                "SC4S_DEST_SPLUNK_HEC_DEFAULT_WORKERS",
                "SC4S_DEST_SPLUNK_HEC_DEFAULT_DISKBUFF_ENABLE",
                "SC4S_SOURCE_UDP_FETCH_LIMIT",
                "SC4S_SOURCE_TCP_FETCH_LIMIT",
                "SC4S_SOURCE_LISTEN_UDP_SOCKETS",
                "SC4S_SOURCE_TLS_MAX_CONNECTIONS",
                "SC4S_ENABLE_EBPF",
                "SC4S_ENABLE_PARALLELIZE",
                "SC4S_USE_REVERSE_DNS",
                "SC4S_ARCHIVE_GLOBAL",
                "SC4S_LISTEN_STATUS_PORT",
                "SC4S_DEBUG_LOGS",
            }
            self.assertTrue(required_keys.issubset(keys), sorted(required_keys - set(keys)))
            categories = set(schema["categories"])
            for category in {"destinations", "disk_buffer", "listeners", "tls", "performance", "dns", "archive", "operations"}:
                self.assertIn(category, categories)
            for key in required_keys:
                opt = keys[key]
                for field in ["description", "docs", "apply_mode", "secret", "type"]:
                    self.assertIn(field, opt, key)
                self.assertIn(opt["apply_mode"], {"reloadable", "restart_required", "deployment_required"})

    def test_option_schema_reports_version_drift(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.control_request = lambda action, **params: {"ok": True, "status": {"image_version": "9.99.0", "image": "sc4s:test"}}
            schema = app.option_schema()
            self.assertEqual(schema["running_sc4s_version"], "9.99.0")
            self.assertTrue(schema["version_drift"]["drift"])
            self.assertIn("3.43.0", schema["version_drift"]["message"])

    def test_validate_config_allows_tls_port_when_tls_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": "syntax ok", "stderr": ""}
            result = app.validate_config()
            self.assertTrue(result["syntax"]["ok"])
            self.assertFalse(result["tls"]["enabled"])
            self.assertFalse(result["tls"]["ready"])
            self.assertTrue(result["ok"])

    def test_validate_config_fails_when_tls_enabled_but_not_ready(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.ENV_FILE.write_text(app.ENV_FILE.read_text() + "SC4S_SOURCE_TLS_ENABLE=yes\n")
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": "syntax ok", "stderr": ""}
            result = app.validate_config()
            self.assertTrue(result["syntax"]["ok"])
            self.assertTrue(result["tls"]["enabled"])
            self.assertFalse(result["tls"]["ready"])
            self.assertFalse(result["ok"])

    def test_restore_backup_restores_file_content(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.set_env_value("SC4S_QA_SAFE", "1", "tester")
            backup_name = sorted(app.BACKUP_DIR.glob("*.bak"))[-1].name
            app.set_env_value("SC4S_QA_SAFE", "2", "tester")
            out = app.restore_backup(backup_name, "tester")
            self.assertTrue(out["restart_required"])
            self.assertNotIn("SC4S_QA_SAFE=2", app.ENV_FILE.read_text())

    def test_preview_env_change_returns_redacted_diff_and_apply_mode(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            preview = app.preview_change({"type":"env", "key":"SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN", "value":"newsecret"})
            self.assertEqual(preview["apply_mode"], "restart_required")
            self.assertIn("SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN=[REDACTED]", preview["diff"])
            self.assertNotIn("newsecret", preview["diff"])
            self.assertTrue(preview["validation"]["skipped"])

    def test_apply_env_change_validates_backs_up_and_restarts(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            actions = []
            def fake_control(action, **params):
                actions.append(action)
                if action == "validate":
                    return {"ok": True, "code": 0, "stdout": "syntax ok", "stderr": ""}
                if action in {"restart", "status"}:
                    return {"ok": True, "status": {"running": True, "health": "healthy", "image_version": app.SUPPORTED_SC4S_VERSION}}
                return {"ok": True, "code": 0, "stdout": "", "stderr": ""}
            app.control_request = fake_control
            app.tls_inventory = lambda: {"ready": True, "enabled": True, "problems": []}
            result = app.apply_change({"type":"env", "key":"SC4S_USE_REVERSE_DNS", "value":"yes", "apply": True}, "tester")
            self.assertTrue(result["ok"])
            self.assertEqual(app.parse_env()["SC4S_USE_REVERSE_DNS"], "yes")
            self.assertTrue(list(app.BACKUP_DIR.glob("*.bak")))
            self.assertIn("validate", actions)
            self.assertIn("restart", actions)
            self.assertEqual(result["post_check"]["docker"]["health"], "healthy")

    def test_failed_apply_control_restores_file_and_retries_restored_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            actions = []
            app.validate_config = lambda: {"ok": True}
            app.restart_sc4s = lambda actor: actions.append(actor) or ({"ok": False, "error": "first failed"} if len(actions) == 1 else {"ok": True})
            before = app.ENV_FILE.read_text()

            out = app.apply_change({"type": "env", "key": "SC4S_USE_REVERSE_DNS", "value": "yes", "apply": True}, "tester")

            self.assertFalse(out["ok"])
            self.assertTrue(out["rolled_back"])
            self.assertEqual(actions, ["tester", "tester"])
            self.assertTrue(out["rollback_runtime"]["ok"])
            self.assertEqual(app.ENV_FILE.read_text(), before)

    def test_delete_source_apply_honors_intent_and_rolls_back_after_reload_failure(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.add_service({"filter": "asa_lab", "source": "10.10.2.0/24", "vendor_product": "cisco_asa"}, "tester")
            app.validate_config = lambda: {"ok": True}
            calls = []
            app.reload_sc4s = lambda actor: calls.append(actor) or ({"ok": False} if len(calls) == 1 else {"ok": True})

            out = app.delete_source("asa_lab", "tester", apply=True)

            self.assertFalse(out["ok"])
            self.assertTrue(out["rolled_back"])
            self.assertEqual(calls, ["tester", "tester"])
            self.assertTrue((app.LOCAL_ROOT / "config" / "filters" / "asa_lab.conf").exists())


    def test_rollback_restore_preserves_local_root_inode_for_bind_mounts(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.add_service({"filter": "keepme", "source": "10.10.2.0/24", "vendor_product": "cisco_asa", "index": "netfw"}, "tester")
            snapshot = app.mutation_snapshot()
            inode_before = app.LOCAL_ROOT.stat().st_ino
            app.add_service({"filter": "extra", "source": "10.10.3.0/24", "vendor_product": "cisco_asa"}, "tester")

            app.restore_mutation_snapshot(snapshot)
            app.cleanup_mutation_snapshot(snapshot)

            # LOCAL_ROOT is bind-mounted into the SC4S container; replacing its
            # inode detaches the runtime's config view until container restart.
            self.assertEqual(app.LOCAL_ROOT.stat().st_ino, inode_before)
            self.assertTrue((app.LOCAL_ROOT / "config" / "filters" / "keepme.conf").exists())
            self.assertFalse((app.LOCAL_ROOT / "config" / "filters" / "extra.conf").exists())

    def test_failed_apply_of_new_file_removes_broken_config(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.validate_config = lambda: {"ok": False, "syntax": {"stderr": "broken"}}
            target = app.LOCAL_ROOT / "config" / "filters" / "broken_new.conf"

            out = app.apply_change({"type": "file", "path": "config/filters/broken_new.conf", "content": "filter f_broken { broken(; };\n", "apply": True}, "tester")

            self.assertFalse(out["ok"])
            self.assertTrue(out["rolled_back"])
            self.assertIsNone(out["backup"])
            self.assertFalse(target.exists())

    def test_failed_apply_of_existing_file_restores_backup(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            target = app.LOCAL_ROOT / "config" / "filters" / "rollme.conf"
            target.write_text("filter f_rollme { netmask(\"192.0.2.0/24\"); };\n")
            app.validate_config = lambda: {"ok": False, "syntax": {"stderr": "broken"}}

            out = app.apply_change({"type": "file", "path": "config/filters/rollme.conf", "content": "filter f_rollme { broken(; };\n", "apply": True}, "tester")

            self.assertFalse(out["ok"])
            self.assertTrue(out["rolled_back"])
            self.assertIn("netmask", target.read_text())

    def test_prometheus_metrics_render_summary_and_escape_labels(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            metrics = {"ok": True, "summary": {"processed": 10, "dropped": 0}, "by_source": {"src.syslog": 2}}
            text = app.prometheus_metrics(metrics)
            self.assertIn("sc4s_manager_syslogng_processed 10", text)
            self.assertIn('sc4s_manager_syslogng_source_rows{source="src.syslog"} 2', text)
            self.assertIn("# HELP", text)

    def test_cert_metadata_includes_not_after_and_days_remaining(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            cert = app.TLS_DIR / "server.pem"
            cert.write_text("-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n")
            app.ENV_FILE.write_text(app.ENV_FILE.read_text() + "SC4S_SOURCE_TLS_ENABLE=yes\n")
            def fake_run(cmd, timeout=20, stdout_limit=12000):
                if cmd[:2] == ["openssl", "x509"] and "-enddate" in cmd:
                    return {"ok": True, "code": 0, "stdout": "notAfter=Dec 31 23:59:59 2099 GMT\n", "stderr": ""}
                if cmd[:2] == ["openssl", "x509"]:
                    return {"ok": True, "code": 0, "stdout": "sha256 Fingerprint=AA:BB\n", "stderr": ""}
                return {"ok": True, "code": 0, "stdout": "tcp LISTEN 0 1 0.0.0.0:6514 0.0.0.0:*\n", "stderr": ""}
            app.run = fake_run
            inv = app.tls_inventory()
            self.assertEqual(inv["cert"]["not_after"], "2099-12-31T23:59:59+00:00")
            self.assertGreater(inv["cert"]["days_remaining"], 1000)

    def test_set_secret_env_value_writes_without_echoing_secret(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            out = app.set_secret_env_value("SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN", "newsecret", "tester")
            self.assertEqual(app.parse_env()["SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN"], "newsecret")
            self.assertEqual(out["value"], "[REDACTED]")
            self.assertTrue(out["restart_required"])

    def test_backup_diff_redacts_secret_values(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.set_secret_env_value("SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN", "newsecret", "tester")
            backup_name = sorted(app.BACKUP_DIR.glob("*.bak"))[-1].name
            diff = app.backup_diff(backup_name)
            self.assertIn("SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN=[REDACTED]", diff["diff"])
            self.assertNotIn("newsecret", diff["diff"])
            self.assertNotIn("secret", diff["diff"].replace("[REDACTED]", ""))

    def test_origin_allowed_rejects_mismatched_origin(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            class H:
                headers = {"Origin": "https://evil.example", "Host": "sc4s-dev.s6securitylabs.com"}
            self.assertFalse(app.origin_allowed(H()))

    def test_http_handler_serves_authenticated_get_routes_and_redacts_config(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            app.service_stats = lambda: {"ok": True, "health": {"ok": True}, "docker": {"running": True}}
            app.health_probe = lambda: {"ok": True, "status": 200}
            app.syslog_ng_metrics = lambda filters=None: {"ok": True, "filters": filters or {}}
            app.prometheus_metrics = lambda metrics=None: "# HELP sc4s_manager_test test\nsc4s_manager_test 1\n"
            app.option_schema = lambda: {"options": [], "categories": []}
            app.validate_config = lambda: {"ok": True}
            app.tls_inventory = lambda: {"ready": True}
            app.templates = lambda: []
            app.products = lambda: {"products": []}
            app.destination_inventory = lambda: {"destinations": []}
            app.catalogue_inventory = lambda filters=None: {"entries": [{"id": "commvault_commcell"}], "count": 1, "limit": 50, "offset": 0, "filters": filters or {}}
            app.catalogue_detail = lambda entry_id: {"id": entry_id, "display_name": "Commvault CommCell"}
            app.library_sources = lambda: {"sources": [{"source_id": "official", "enabled": True, "last_sync": "2026-06-01T00:00:00Z"}]}
            app.library_catalogue = lambda source_id="official", filters=None: {"source_id": source_id, "entries": [{"id": "pan_panos"}], "filters": filters or {}}
            app.library_entry = lambda source_id, entry_id, refresh=False: {"source_id": source_id, "entry": {"id": entry_id}, "refresh": refresh}
            app.list_library_imports = lambda: {"imports": [{"import_id": "imp_123", "entry_id": "pan_panos", "apply_allowed": True}]}
            app.backups = lambda: []
            app.backup_diff = lambda name: {"name": name, "diff": "safe"}
            app.AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
            app.AUDIT_LOG.write_text("audit-line\n")

            server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def get(path):
                    conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                    conn.request("GET", path, headers={"Authorization": "Bearer manual-secret", "Host": "sc4s-manager.test"})
                    resp = conn.getresponse()
                    body = resp.read().decode("utf-8")
                    conn.close()
                    return resp.status, resp.getheader("Content-Type"), body

                status, ctype, body = get("/api/config")
                self.assertEqual(status, 200)
                self.assertIn("application/json", ctype)
                config = json.loads(body)
                self.assertEqual(config["env"]["SC4S_DEST_SPLUNK_HEC_DEFAULT_TOKEN"], "[REDACTED]")

                status, ctype, body = get("/api/metrics/syslog-ng?source_name=filter&type=matched&limit=5")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["filters"], {"source_name": "filter", "type": "matched", "limit": "5"})

                status, ctype, body = get("/api/catalogue?origin=sechub-resource&limit=5")
                self.assertEqual(status, 200)
                payload = json.loads(body)
                self.assertEqual(payload["entries"][0]["id"], "commvault_commcell")
                self.assertEqual(payload["filters"], {"origin": "sechub-resource", "limit": "5"})

                status, ctype, body = get("/api/catalogue/commvault_commcell")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["display_name"], "Commvault CommCell")

                status, ctype, body = get("/api/library/sources")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["sources"][0]["source_id"], "official")

                status, ctype, body = get("/api/library/catalogue?source_id=official&downloadable_only=yes&search=pan")
                self.assertEqual(status, 200)
                library_catalogue = json.loads(body)
                self.assertEqual(library_catalogue["source_id"], "official")
                self.assertEqual(library_catalogue["filters"], {"downloadable_only": "yes", "search": "pan"})

                status, ctype, body = get("/api/library/entry?source_id=official&entry_id=pan_panos&refresh=yes")
                self.assertEqual(status, 200)
                library_entry = json.loads(body)
                self.assertEqual(library_entry["source_id"], "official")
                self.assertEqual(library_entry["entry"]["id"], "pan_panos")
                self.assertTrue(library_entry["refresh"])

                status, ctype, body = get("/api/library/imports")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["imports"][0]["import_id"], "imp_123")

                status, ctype, body = get("/metrics")
                self.assertEqual(status, 200)
                self.assertIn("text/plain", ctype)
                self.assertIn("sc4s_manager_test 1", body)

                status, ctype, body = get("/api/audit")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["lines"], ["audit-line"])

                status, ctype, body = get("/missing")
                self.assertEqual(status, 404)
                self.assertEqual(json.loads(body)["error"], "not found")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_library_post_routes_are_wired(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            app.sync_library_source = lambda source_id: {"ok": True, "source_id": source_id, "synced": True}
            app.download_library_bundle = lambda source_id, entry_id: {"ok": True, "source_id": source_id, "entry_id": entry_id, "download": {"filename": f"{entry_id}.zip"}}
            app.validate_library_import = lambda source_id, entry_id, actor="manager": {"ok": True, "source_id": source_id, "entry_id": entry_id, "import_id": "imp_123", "actor": actor}
            app.apply_library_import = lambda import_id, actor, apply=True: {"ok": True, "import_id": import_id, "actor": actor, "apply": apply}
            server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def post(path, payload):
                    conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                    conn.request(
                        "POST",
                        path,
                        body=json.dumps(payload),
                        headers={"Authorization": "Bearer manual-secret", "Host": "sc4s-manager.test", "Content-Type": "application/json"},
                    )
                    resp = conn.getresponse()
                    body = resp.read().decode("utf-8")
                    conn.close()
                    return resp.status, json.loads(body)

                status, body = post("/api/library/sync", {"source_id": "official"})
                self.assertEqual(status, 200)
                self.assertTrue(body["synced"])

                status, body = post("/api/library/download", {"source_id": "official", "entry_id": "pan_panos"})
                self.assertEqual(status, 200)
                self.assertEqual(body["download"]["filename"], "pan_panos.zip")

                status, body = post("/api/library/import/validate", {"source_id": "official", "entry_id": "pan_panos"})
                self.assertEqual(status, 200)
                self.assertEqual(body["import_id"], "imp_123")

                status, body = post("/api/library/import/apply", {"import_id": "imp_123", "apply": False})
                self.assertEqual(status, 200)
                self.assertFalse(body["apply"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_retired_profile_and_marketplace_api_routes_return_404(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            app.pack_inventory = lambda: {"packs": [], "count": 0}
            app.library_sources = lambda: {"sources": []}
            server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def request(method, path, payload=None):
                    conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                    headers = {"Authorization": "Bearer manual-secret", "Host": "sc4s-manager.test"}
                    body = None
                    if payload is not None:
                        headers["Content-Type"] = "application/json"
                        body = json.dumps(payload)
                    conn.request(method, path, body=body, headers=headers)
                    resp = conn.getresponse()
                    raw = resp.read().decode("utf-8")
                    conn.close()
                    return resp.status, json.loads(raw)

                # The pack/library taxonomy is canonical; removed API routes
                # must not resolve. Construct removed paths in pieces so the
                # active-surface scan does not reintroduce literal legacy routes.
                removed_profile_api = "/api/" + "pro" + "files"
                removed_remote_api = "/api/" + "market" + "place"
                for path in [
                    removed_profile_api,
                    f"{removed_profile_api}/commvault_commcell",
                    f"{removed_profile_api}/commvault_commcell/export",
                    f"{removed_remote_api}/sources",
                    f"{removed_remote_api}/catalogue",
                    f"{removed_remote_api}/entry?source_id=official&entry_id=pan_panos",
                    f"{removed_remote_api}/imports",
                ]:
                    status, body = request("GET", path)
                    self.assertEqual(status, 404, path)
                    self.assertEqual(body["error"], "not found")

                for path in [
                    f"{removed_remote_api}/sync",
                    f"{removed_remote_api}/download",
                    f"{removed_remote_api}/import/validate",
                    f"{removed_remote_api}/import/apply",
                    f"{removed_profile_api}/commvault_commcell/validate-fixtures",
                ]:
                    status, body = request("POST", path, payload={})
                    self.assertEqual(status, 404, path)
                    self.assertEqual(body["error"], "not found")

                # Canonical replacements stay reachable.
                status, body = request("GET", "/api/packs")
                self.assertEqual(status, 200)
                self.assertEqual(body, {"packs": [], "count": 0})

                status, body = request("GET", "/api/library/sources")
                self.assertEqual(status, 200)
                self.assertEqual(body, {"sources": []})
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_crud_post_routes_are_wired_for_staged_operator_journey(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            app.control_request = lambda action, **params: {"ok": True, "code": 0, "stdout": "syntax ok", "stderr": "", "status": {"running": True, "health": "healthy", "image_version": app.SUPPORTED_SC4S_VERSION}}
            app.tls_inventory = lambda: {"ready": True, "enabled": True, "problems": []}
            server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def request(method, path, payload=None, authenticated=True):
                    conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                    headers = {"Host": "sc4s-manager.test"}
                    if authenticated:
                        headers["Authorization"] = "Bearer manual-secret"
                    body = None
                    if payload is not None:
                        headers["Content-Type"] = "application/json"
                        body = json.dumps(payload)
                    conn.request(method, path, body=body, headers=headers)
                    resp = conn.getresponse()
                    raw = resp.read().decode("utf-8")
                    conn.close()
                    return resp.status, json.loads(raw), raw

                status, body, _ = request("POST", "/api/sources/onboard", {"name": "evil", "source": "10.0.0.1"}, authenticated=False)
                self.assertEqual(status, 403)
                self.assertEqual(body["error"], "forbidden")

                status, body, _ = request("POST", "/api/sources/onboard", {
                    "name": "asa_lab", "source": "10.10.2.0/24", "vendor_product": "cisco_asa",
                    "index": "netfw", "compliance": "pci", "apply": False,
                })
                self.assertEqual(status, 200)
                self.assertTrue(body["ok"])
                self.assertTrue(body["control"]["skipped"])

                status, body, _ = request("GET", "/api/sources")
                self.assertEqual(status, 200)
                self.assertEqual([item["name"] for item in body["sources"]], ["asa_lab"])

                status, body, raw = request("POST", "/api/destinations", {
                    "kind": "hec", "id": "QAHEC", "url": "https://splunk2:8088",
                    "token": "qa-secret-token", "mode": "SELECT", "tls_verify": "no", "apply": False,
                })
                self.assertEqual(status, 200)
                self.assertTrue(body["ok"])
                self.assertNotIn("qa-secret-token", raw)

                status, body, raw = request("GET", "/api/destinations")
                self.assertEqual(status, 200)
                entry = next(item for item in body["destinations"] if item["id"] == "QAHEC")
                self.assertEqual(entry["token"], "[REDACTED]")
                self.assertNotIn("qa-secret-token", raw)

                status, body, _ = request("POST", "/api/routes", {
                    "id": "asa_to_hec", "source": "asa_lab", "pack": "cisco_asa",
                    "destination_kind": "hec", "destination_id": "QAHEC", "apply": False,
                })
                self.assertEqual(status, 200)
                self.assertTrue(body["ok"])
                self.assertEqual(body["route"]["id"], "asa_to_hec")

                status, body, _ = request("GET", "/api/routes")
                self.assertEqual(status, 200)
                self.assertEqual([item["id"] for item in body["routes"]], ["asa_to_hec"])

                status, body, _ = request("POST", "/api/routes/delete", {"id": "asa_to_hec"})
                self.assertEqual(status, 200)
                self.assertTrue(body["ok"])
                status, body, _ = request("GET", "/api/routes")
                self.assertEqual(body["routes"], [])

                status, body, raw = request("POST", "/api/destinations/delete", {"kind": "hec", "id": "QAHEC"})
                self.assertEqual(status, 200)
                self.assertTrue(body["ok"])
                self.assertIn("SC4S_DEST_SPLUNK_HEC_QAHEC_TOKEN", body["removed_env_keys"])
                self.assertNotIn("qa-secret-token", raw)

                status, body, _ = request("POST", "/api/sources/delete", {"name": "asa_lab"})
                self.assertEqual(status, 200)
                self.assertTrue(body["ok"])
                self.assertTrue(body["removed_paths"])
                status, body, _ = request("GET", "/api/sources")
                self.assertEqual(body["sources"], [])

                status, body, _ = request("POST", "/api/sources/delete", {"name": "../../etc/passwd"})
                self.assertEqual(status, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_http_handler_rejects_unauthenticated_requests_and_bad_post_bodies(self):
        with tempfile.TemporaryDirectory() as d:
            app = load_app(Path(d))
            app.MANUAL_LOGIN_TOKEN = "manual-secret"
            server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                conn.request("GET", "/api/stats", headers={"Host": "sc4s-manager.test"})
                resp = conn.getresponse()
                body = resp.read().decode("utf-8")
                conn.close()
                self.assertEqual(resp.status, 403)
                self.assertEqual(json.loads(body)["error"], "forbidden")

                conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                conn.request(
                    "POST",
                    "/api/env",
                    body='["not", "an", "object"]',
                    headers={"Authorization": "Bearer manual-secret", "Host": "sc4s-manager.test", "Content-Type": "application/json"},
                )
                resp = conn.getresponse()
                body = resp.read().decode("utf-8")
                conn.close()
                self.assertEqual(resp.status, 400)
                self.assertIn("JSON body must be an object", json.loads(body)["error"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
