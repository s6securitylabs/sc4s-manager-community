import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.ci_functional import validate_ci_evidence


LIVE_CI = os.environ.get("SC4S_MANAGER_LIVE_CI") == "1"
BROWSER_CI = os.environ.get("SC4S_MANAGER_BROWSER_CI") == "1"


@pytest.mark.skipif(not LIVE_CI, reason="set SC4S_MANAGER_LIVE_CI=1 to run disposable Splunk live CI tests")
def test_live_disposable_splunk_hec_indexes_marker():
    splunk_url = os.environ["SC4S_MANAGER_TEST_SPLUNK_URL"].rstrip("/")
    hec_url = os.environ["SC4S_MANAGER_TEST_HEC_URL"].rstrip("/")
    hec_token = os.environ["SC4S_MANAGER_TEST_HEC_TOKEN"]
    index = os.environ.get("SC4S_MANAGER_TEST_INDEX", "sc4s_ci")
    marker = "sc4s-ci-live-hec-test"

    send = subprocess.run(
        [
            "curl",
            "-skS",
            "-H",
            f"Authorization: Splunk {hec_token}",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps({"index": index, "event": f"SC4S_MANAGER_LIVE_HEC {marker}"}),
            f"{hec_url}/services/collector/event",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert send.returncode == 0, send.stderr
    assert "Success" in send.stdout or "success" in send.stdout.lower()

    search = f'search index={index} "{marker}" | stats count as count'
    result = subprocess.run(
        [
            "curl",
            "-skS",
            "-u",
            os.environ["SC4S_MANAGER_TEST_SPLUNK_AUTH"],
            "--data-urlencode",
            f"search={search}",
            "--data",
            "output_mode=json",
            f"{splunk_url}/services/search/jobs/export",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert marker in result.stdout or '"count":"1"' in result.stdout or '"count":1' in result.stdout


@pytest.mark.skipif(not LIVE_CI, reason="set SC4S_MANAGER_LIVE_CI=1 to run live SC4S pack pipeline tests")
def test_live_sc4s_pack_pipeline_evidence_file_is_valid():
    evidence_path = Path(os.environ["SC4S_MANAGER_LIVE_PIPELINE_EVIDENCE"])
    evidence = json.loads(evidence_path.read_text())

    findings = validate_ci_evidence(evidence, release_mode=True)

    assert findings == [{"ok": True, "detail": "CI functional evidence is valid"}]


@pytest.mark.skipif(not BROWSER_CI, reason="set SC4S_MANAGER_BROWSER_CI=1 to run live browser screenshot evidence tests")
def test_live_browser_crawl_evidence_file_is_valid():
    evidence_path = Path(os.environ["SC4S_MANAGER_BROWSER_EVIDENCE"])
    evidence = json.loads(evidence_path.read_text())

    findings = validate_ci_evidence(evidence, release_mode=True)

    assert findings == [{"ok": True, "detail": "CI functional evidence is valid"}]
