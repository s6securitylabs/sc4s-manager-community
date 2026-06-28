import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "api_acceptance_probe.py"


def load_probe():
    spec = importlib.util.spec_from_file_location("api_acceptance_probe_test", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class ApiAcceptanceProbeTests(unittest.TestCase):
    def test_manual_login_token_is_primary_token_source(self):
        probe = load_probe()
        with mock.patch.dict(os.environ, {"SC4S_MANAGER_MANUAL_LOGIN_TOKEN": "manual", "SC4S_MANAGER_API_TOKEN": "legacy"}, clear=True):
            token, source, scheme = probe.load_auth_token()
        self.assertEqual((token, source, scheme), ("manual", "SC4S_MANAGER_MANUAL_LOGIN_TOKEN", "bearer"))

    def test_api_token_is_legacy_fallback(self):
        probe = load_probe()
        with mock.patch.dict(os.environ, {"SC4S_MANAGER_API_TOKEN": "legacy"}, clear=True):
            token, source, scheme = probe.load_auth_token()
        self.assertEqual((token, source, scheme), ("legacy", "SC4S_MANAGER_API_TOKEN", "legacy-header"))

    def test_manual_token_uses_bearer_header(self):
        probe = load_probe()
        captured = {}

        class FakeResponse:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
            def read(self):
                return b"{}"

        def fake_urlopen(req, timeout):
            captured["authorization"] = req.get_header("Authorization")
            captured["legacy"] = req.get_header("X-sc4s-manager-token") or req.get_header("X-SC4S-Manager-Token")
            return FakeResponse()

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            status, body = probe.request("https://example.invalid", "GET", "/api/stats", "manual", "bearer")
        self.assertEqual(status, 200)
        self.assertEqual(captured["authorization"], "Bearer manual")
        self.assertIsNone(captured["legacy"])


if __name__ == "__main__":
    unittest.main()
