"""Tests for the sample event classifier and parser/pack match preview.

Tests cover:
- Cisco ASA good path (high-confidence match)
- JSON classification
- Multiline boundary ambiguity
- Secret redaction
- No file writes (stored=False)
- Unknown/fallback path (no match, next actions present)
- RFC 5424 / RFC 3164 format detection
- Source-hint-based candidate matching
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sc4s_manager.sample_preview import (
    classify_sample,
    preview_sample,
    _redact_sample,
)

CISCO_ASA_SAMPLE = (
    "<134>1 2026-01-15T12:00:00Z firewall01 ASA - - "
    "%ASA-6-302013: Built outbound TCP connection 12345 for outside:203.0.113.10/443 "
    "(203.0.113.10/443) to inside:10.10.1.5/54321 (10.10.1.5/54321)"
)

CISCO_FTD_SAMPLE = (
    "<134>Mar  1 00:00:00 ngfw %FTD-6-110002: Failed to locate egress interface for "
    "protocol from src interface:src IP/port to dest IP/port"
)

JSON_SAMPLE = '{"timestamp": "2026-01-15T12:00:00Z", "level": "info", "msg": "login ok"}'

MULTILINE_SAMPLE = (
    "<134>Jan 15 12:00:00 host sshd[1234]: Accepted publickey\n"
    "  from 10.0.0.1 port 54321 ssh2"
)

SECRET_SAMPLE = (
    "<134>Jan 15 12:00:00 host app[99]: token=supersecretvalue123 user=admin "
    "password=hunter2 host=dbserver"
)

UNKNOWN_SAMPLE = "2026-01-15 12:00:00 INFO Application started successfully"

PALOALTO_SAMPLE = (
    "<14>Jan 15 12:00:00 pa-fw 1,2026/01/15 12:00:00,0123456789,TRAFFIC,"
    "end,2049,2026/01/15 12:00:00,10.0.0.1,8.8.8.8,0.0.0.0,0.0.0.0"
)

SOURCE_CATALOG = [
    {
        "vendor_product": "cisco_asa",
        "label": "Cisco ASA",
        "default_index": "netfw",
    },
    {
        "vendor_product": "cisco_ios",
        "label": "Cisco IOS",
        "default_index": "netops",
    },
    {
        "vendor_product": "paloalto_panos",
        "label": "Palo Alto PAN-OS",
        "default_index": "netfw",
    },
    {
        "vendor_product": "linux_messages_syslog",
        "label": "Linux syslog/messages",
        "default_index": "osnix",
    },
]


class TestClassifySample:
    def test_cisco_asa_sample_classifies_syslog_format(self):
        result = classify_sample(CISCO_ASA_SAMPLE)
        assert result["ok"] is True
        assert "rfc5424" in result["format_hints"]

    def test_cisco_asa_stored_is_always_false(self):
        result = classify_sample(CISCO_ASA_SAMPLE)
        assert result["stored"] is False

    def test_cisco_ftd_sample_classifies_rfc3164_format(self):
        result = classify_sample(CISCO_FTD_SAMPLE)
        assert result["ok"] is True
        assert "rfc3164" in result["format_hints"]
        assert result["stored"] is False

    def test_json_sample_classifies_as_json(self):
        result = classify_sample(JSON_SAMPLE)
        assert result["ok"] is True
        assert "json" in result["format_hints"]

    def test_multiline_sample_reports_boundary_ambiguity(self):
        result = classify_sample(MULTILINE_SAMPLE)
        assert result["ok"] is True
        assert "multiline" in result["format_hints"]
        assert "boundary_ambiguous" in result["format_hints"]

    def test_unknown_sample_classifies_as_raw_headerless(self):
        result = classify_sample(UNKNOWN_SAMPLE)
        assert result["ok"] is True
        assert "raw_headerless" in result["format_hints"]

    def test_empty_sample_returns_ok_false(self):
        result = classify_sample("")
        assert result["ok"] is False
        assert "empty sample provided" in result["limitations"]
        assert result["stored"] is False

    def test_whitespace_only_sample_returns_ok_false(self):
        result = classify_sample("   \n  ")
        assert result["ok"] is False
        assert result["stored"] is False

    def test_timestamp_hint_extracted_from_rfc5424(self):
        result = classify_sample(CISCO_ASA_SAMPLE)
        assert result["timestamp_hint"] is not None
        assert "2026-01-15" in result["timestamp_hint"]

    def test_host_hint_extracted_from_rfc5424(self):
        result = classify_sample(CISCO_ASA_SAMPLE)
        assert result["host_hint"] == "firewall01"

    def test_limitations_always_present(self):
        result = classify_sample(CISCO_ASA_SAMPLE)
        assert len(result["limitations"]) >= 1

    def test_classify_does_not_write_files(self, tmp_path):
        before = list(tmp_path.iterdir())
        classify_sample(CISCO_ASA_SAMPLE)
        after = list(tmp_path.iterdir())
        assert before == after


class TestRedactSample:
    def test_token_value_is_redacted(self):
        result = _redact_sample("token=supersecretvalue123 host=example")
        assert "supersecretvalue123" not in result
        assert "[REDACTED]" in result
        assert "host=example" in result

    def test_password_value_is_redacted(self):
        result = _redact_sample("password=hunter2 user=alice")
        assert "hunter2" not in result
        assert "user=alice" in result

    def test_bearer_token_is_redacted(self):
        result = _redact_sample("Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9")
        assert "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_non_secret_key_value_is_preserved(self):
        result = _redact_sample("host=myserver.example.com port=514")
        assert "host=myserver.example.com" in result
        assert "port=514" in result

    def test_redaction_does_not_corrupt_metadata(self):
        result = _redact_sample('vendor=cisco product=asa token=abc123')
        assert "vendor=cisco" in result
        assert "product=asa" in result

    def test_classify_sample_redacts_secrets_in_preview(self):
        result = classify_sample(SECRET_SAMPLE)
        assert "supersecretvalue123" not in result["redacted_sample_preview"]
        assert "hunter2" not in result["redacted_sample_preview"]
        assert "[REDACTED]" in result["redacted_sample_preview"]


class TestPreviewSample:
    def test_cisco_asa_sample_matches_cisco_asa_candidate(self):
        result = preview_sample(CISCO_ASA_SAMPLE, source_catalog=SOURCE_CATALOG)
        assert result["validated"] is False
        matches = result["candidate_matches"]
        assert len(matches) >= 1
        top = matches[0]
        assert top["vendor_product"] == "cisco_asa"
        assert top["confidence"] == "high"
        assert top["requires_operator_review"] is True

    def test_cisco_asa_expected_metadata_has_netfw_index(self):
        result = preview_sample(CISCO_ASA_SAMPLE, source_catalog=SOURCE_CATALOG)
        meta = result["expected_metadata"]
        assert meta["index"] == "netfw"
        assert meta["sourcetype"] == "cisco_asa"

    def test_validated_always_false(self):
        result = preview_sample(CISCO_ASA_SAMPLE, source_catalog=SOURCE_CATALOG)
        assert result["validated"] is False

    def test_unknown_sample_returns_no_matches_and_next_actions(self):
        result = preview_sample(UNKNOWN_SAMPLE, source_catalog=SOURCE_CATALOG)
        assert result["validated"] is False
        assert result["candidate_matches"] == []
        assert len(result["next_actions"]) >= 1

    def test_unknown_sample_expected_metadata_index_is_none(self):
        result = preview_sample(UNKNOWN_SAMPLE, source_catalog=SOURCE_CATALOG)
        assert result["expected_metadata"]["index"] is None
        assert result["expected_metadata"]["sourcetype"] is None

    def test_source_hint_produces_candidate_when_no_signature_match(self):
        result = preview_sample(
            UNKNOWN_SAMPLE,
            source_hint="linux_messages_syslog",
            source_catalog=SOURCE_CATALOG,
        )
        vps = [c["vendor_product"] for c in result["candidate_matches"]]
        assert "linux_messages_syslog" in vps

    def test_source_hint_candidate_confidence_is_low(self):
        result = preview_sample(
            UNKNOWN_SAMPLE,
            source_hint="linux_messages_syslog",
            source_catalog=SOURCE_CATALOG,
        )
        match = next(c for c in result["candidate_matches"] if c["vendor_product"] == "linux_messages_syslog")
        assert match["confidence"] == "low"

    def test_preview_does_not_write_files(self, tmp_path):
        before = list(tmp_path.iterdir())
        preview_sample(CISCO_ASA_SAMPLE, source_catalog=SOURCE_CATALOG)
        after = list(tmp_path.iterdir())
        assert before == after

    def test_classification_is_embedded_in_preview_result(self):
        result = preview_sample(CISCO_ASA_SAMPLE, source_catalog=SOURCE_CATALOG)
        assert "classification" in result
        assert result["classification"]["ok"] is True

    def test_next_actions_present_for_matched_sample(self):
        result = preview_sample(CISCO_ASA_SAMPLE, source_catalog=SOURCE_CATALOG)
        assert len(result["next_actions"]) >= 1

    def test_paloalto_sample_matches_paloalto_candidate(self):
        result = preview_sample(PALOALTO_SAMPLE, source_catalog=SOURCE_CATALOG)
        vps = [c["vendor_product"] for c in result["candidate_matches"]]
        assert "paloalto_panos" in vps

    def test_empty_sample_propagates_classification_failure(self):
        result = preview_sample("", source_catalog=SOURCE_CATALOG)
        assert result["classification"]["ok"] is False
        assert result["candidate_matches"] == []
        assert result["validated"] is False

    def test_preview_without_source_catalog_returns_no_catalog_matches(self):
        result = preview_sample(UNKNOWN_SAMPLE, source_catalog=[])
        assert result["candidate_matches"] == []

    def test_cisco_asa_candidate_does_not_appear_duplicated(self):
        result = preview_sample(
            CISCO_ASA_SAMPLE,
            source_hint="cisco_asa",
            source_catalog=SOURCE_CATALOG,
        )
        vps = [c["vendor_product"] for c in result["candidate_matches"]]
        assert vps.count("cisco_asa") == 1
