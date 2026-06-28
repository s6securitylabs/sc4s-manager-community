"""Sample event classifier and parser/pack match preview.

Events are never stored or promoted by this module. All functions are
pure classifiers operating on the caller-supplied string. Redaction is
applied to secret-looking key=value patterns before returning previews.
"""
from __future__ import annotations

import json
import re
from typing import Any

_RFC5424_RE = re.compile(r"^<\d+>1 \S+ \S+ \S+ ")
_RFC3164_RE = re.compile(r"^<\d+>[A-Z][a-z]{2}\s+\d+ \d{2}:\d{2}:\d{2} ")
_CEF_RE = re.compile(r"^CEF:\d+\|", re.I)
_LEEF_RE = re.compile(r"^LEEF:[12]\.\d\|", re.I)
_JSON_RE = re.compile(r"^\s*\{")

_SECRET_KEY_RE = re.compile(r"(TOKEN|SECRET|PASSWORD|KEY|CREDENTIAL|AUTH)", re.I)

_CISCO_ASA_RE = re.compile(r"%(?:ASA|FTD)-\d+-\d+:", re.I)
_CISCO_IOS_RE = re.compile(r"%[A-Z][A-Z0-9_-]+-\d+-[A-Z0-9_]+:", re.I)
_PALOALTO_RE = re.compile(
    r"\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2},(?:\d+,)?(?:TRAFFIC|THREAT|CONFIG|SYSTEM|HIP-MATCH|URL|GLOBALPROTECT)",
    re.I,
)
_FORTINET_RE = re.compile(r"logid=\d|type=traffic\b|type=utm\b", re.I)

_TIMESTAMP_RFC5424_RE = re.compile(
    r"<\d+>1 (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)"
)
_TIMESTAMP_RFC3164_RE = re.compile(r"<\d+>([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})")
_HOST_RFC5424_RE = re.compile(r"<\d+>1 \S+ (\S+)")
_HOST_RFC3164_RE = re.compile(r"<\d+>[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2}\s+(\S+)")


def _redact_sample(sample: str) -> str:
    """Redact secret-looking key=value pairs; preserve structural characters."""
    truncated = sample[:4000]
    result = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*)=("[^"]{1,200}"|[^\s,;\'"\n]{1,200})',
        lambda m: m.group(1) + "=[REDACTED]" if _SECRET_KEY_RE.search(m.group(1)) else m.group(0),
        truncated,
    )
    result = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-+/=.]{8,}", r"\1[REDACTED]", result, flags=re.I)
    return result[:2000]


def _detect_formats(sample: str) -> list[str]:
    formats: list[str] = []
    if _RFC5424_RE.search(sample):
        formats.append("rfc5424")
    if _RFC3164_RE.search(sample):
        formats.append("rfc3164")
    if _CEF_RE.search(sample):
        formats.append("cef")
    if _LEEF_RE.search(sample):
        formats.append("leef")
    if _JSON_RE.match(sample):
        try:
            json.loads(sample)
            formats.append("json")
        except ValueError:
            pass
    stripped = sample.strip()
    if "\n" in stripped:
        formats.append("multiline")
        formats.append("boundary_ambiguous")
    if not formats:
        formats.append("raw_headerless")
    return formats


def _extract_timestamp_hint(sample: str) -> str | None:
    m = _TIMESTAMP_RFC5424_RE.search(sample)
    if m:
        return m.group(1)
    m = _TIMESTAMP_RFC3164_RE.search(sample)
    if m:
        return m.group(1)
    return None


def _extract_host_hint(sample: str) -> str | None:
    m = _HOST_RFC5424_RE.search(sample)
    if m and m.group(1) not in {"-", "nil", "NILVALUE"}:
        return m.group(1)
    m = _HOST_RFC3164_RE.search(sample)
    if m:
        return m.group(1)
    return None


def classify_sample(
    sample: str,
    source_hint: str = "",
    transport: str = "unknown",
) -> dict[str, Any]:
    """Classify a raw sample event without storing or promoting it."""
    if not sample or not sample.strip():
        return {
            "ok": False,
            "format_hints": [],
            "timestamp_hint": None,
            "host_hint": None,
            "redacted_sample_preview": "",
            "stored": False,
            "limitations": ["empty sample provided"],
        }
    return {
        "ok": True,
        "format_hints": _detect_formats(sample),
        "timestamp_hint": _extract_timestamp_hint(sample),
        "host_hint": _extract_host_hint(sample),
        "redacted_sample_preview": _redact_sample(sample),
        "stored": False,
        "limitations": [
            "Classification is heuristic only; no SC4S parser is run.",
            "Results are not stored or promoted.",
        ],
    }


def _match_candidates(
    sample: str,
    source_hint: str,
    classification: dict[str, Any],
    source_catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    if _CISCO_ASA_RE.search(sample):
        candidates.append({
            "pack_id": "cisco_asa",
            "vendor_product": "cisco_asa",
            "reason": (
                "Sample contains %ASA- or %FTD- marker tokens characteristic of "
                "Cisco ASA/FTD syslog messages."
            ),
            "confidence": "high",
            "requires_operator_review": True,
        })
    elif _CISCO_IOS_RE.search(sample):
        candidates.append({
            "pack_id": "cisco_ios",
            "vendor_product": "cisco_ios",
            "reason": (
                "Sample contains %FACILITY-SEVERITY-MNEMONIC: marker pattern "
                "characteristic of Cisco IOS syslog."
            ),
            "confidence": "medium",
            "requires_operator_review": True,
        })

    if _PALOALTO_RE.search(sample):
        candidates.append({
            "pack_id": "paloalto_panos",
            "vendor_product": "paloalto_panos",
            "reason": (
                "Sample contains CSV log structure with a traffic/threat/config type "
                "matching Palo Alto PAN-OS log format."
            ),
            "confidence": "medium",
            "requires_operator_review": True,
        })

    if _FORTINET_RE.search(sample):
        candidates.append({
            "pack_id": "fortinet_fortigate",
            "vendor_product": "fortinet_fortigate",
            "reason": (
                "Sample contains logid= or type=traffic/utm patterns matching "
                "Fortinet FortiGate syslog format."
            ),
            "confidence": "medium",
            "requires_operator_review": True,
        })

    if source_hint:
        hint_lower = source_hint.lower()
        for src in source_catalog:
            vp = src.get("vendor_product", "")
            if hint_lower in (vp.lower(), src.get("label", "").lower()):
                if not any(c["vendor_product"] == vp for c in candidates):
                    candidates.append({
                        "pack_id": vp,
                        "vendor_product": vp,
                        "reason": (
                            f"Operator-provided source hint '{source_hint}' matches "
                            f"known source '{src.get('label', vp)}'."
                        ),
                        "confidence": "low",
                        "requires_operator_review": True,
                    })

    return candidates


def _expected_metadata(
    candidates: list[dict[str, Any]],
    classification: dict[str, Any],
    source_catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    if not candidates:
        return {
            "index": None,
            "sourcetype": None,
            "source": None,
            "host": classification.get("host_hint"),
            "timestamp_policy": "unknown_requires_validation",
        }
    top = candidates[0]
    vp = top["vendor_product"]
    catalog_entry = next((s for s in source_catalog if s.get("vendor_product") == vp), None)
    return {
        "index": catalog_entry.get("default_index") if catalog_entry else None,
        "sourcetype": vp,
        "source": vp,
        "host": classification.get("host_hint"),
        "timestamp_policy": "unknown_requires_validation",
    }


def _next_actions(candidates: list[dict[str, Any]]) -> list[str]:
    if not candidates:
        return [
            "Identify the source vendor and product.",
            "Check the SC4S source catalogue for a matching parser or pack.",
            "Add a source mapping filter if the vendor_product is known but not auto-detected.",
        ]
    return [
        "Review matched pack/parser candidates — this is a preview, not a validated match.",
        "Configure a source mapping filter in SC4S Manager to route matching events.",
        "Validate routing by sending a test event and checking Splunk for the expected index and sourcetype.",
    ]


def preview_sample(
    sample: str,
    source_hint: str = "",
    transport: str = "unknown",
    source_catalog: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Preview likely parser/pack path without storing or validating the sample."""
    source_catalog = source_catalog or []
    classification = classify_sample(sample, source_hint, transport)
    candidates = _match_candidates(sample, source_hint, classification, source_catalog)
    return {
        "classification": classification,
        "candidate_matches": candidates,
        "expected_metadata": _expected_metadata(candidates, classification, source_catalog),
        "next_actions": _next_actions(candidates),
        "validated": False,
    }
