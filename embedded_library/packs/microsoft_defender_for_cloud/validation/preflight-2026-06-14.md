# Microsoft Defender for Cloud replay preflight — 2026-06-14

Status: blocked / not replay validated.

This pack was created from public Microsoft Defender for Cloud / Microsoft.Security resource naming and synthetic-equivalent JSON fixtures only. No live Defender for Cloud export, Event Hub, SC4S runtime, HEC delivery, or Splunk indexed read-back was available in this workspace.

Required promotion evidence:

- Confirm local collector emits exactly one JSON object per line or document the wrapper mapping.
- Replay `test-events/microsoft_defender_for_cloud_test_events.txt` through the dedicated tcp/20095 listener into a test Splunk index.
- Read back count=3, index=`epintel`, expected sourcetypes, source/host, timestamps, marker tokens, and normalized fields including subscription/resource/severity/status.
- Compare one real sanitized alert and one real sanitized recommendation or assessment against the required-field coverage before stating field validation.

This note is a blocker record only; it is not validation evidence.
