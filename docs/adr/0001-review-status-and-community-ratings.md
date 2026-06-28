# ADR 0001: Treat Library review status as advisory and community rating as feedback

Date: 2026-06-13

## Status

Accepted

## Context

SC4S Manager consumes packs and catalogue entries from SecHub/SecHub Resources, but Manager is the local/private control plane. Public catalogue wording is moving away from trust/quality labels toward simpler Review status and Community rating language.

Manager must keep that distinction clear: public review status and community ratings help operators choose what to inspect, but they do not prove that a pack is safe to apply in a local environment.

## Decision

Manager-facing language will treat upstream public fields as advisory catalogue metadata:

- **Review status**: Unreviewed, Reviewed, or Deprecated.
- **Community rating**: 1–5 star user feedback when available.

Manager must not treat either field as local deployment approval.

Manager still owns local gates:

1. checksum and manifest verification;
2. schema/fixture validation;
3. preview of generated local configuration;
4. operator approval;
5. apply/reload/restart through the narrow control path;
6. post-check and rollback-ready evidence;
7. Splunk/readback proof when configured and required.

## Consequences

- UI/API copy should avoid implying that a Reviewed pack is live-safe or production-ready.
- Community rating is never a validation signal.
- Any local `verified`, `validated`, or `applied` wording must refer to Manager-generated local evidence, not public catalogue review status.
- Contract docs should describe public Review status separately from local validation state.

## Non-goals

- This ADR does not change runtime-control safety gates.
- This ADR does not create community review submission/moderation in Manager.
- This ADR does not promote any imported pack.
