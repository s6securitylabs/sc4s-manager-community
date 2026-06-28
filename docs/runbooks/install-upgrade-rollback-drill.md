# SC4S Manager Install/Upgrade/Rollback Drill

This runbook describes a reproducible human drill of install, upgrade, and rollback
on a disposable VM or LXC container. It must be run on a throwaway host; never on
production. Evidence must be written to `docs/acceptance/package-install-<timestamp>.json`
with secrets redacted before it counts toward the release gate.

## Prerequisites

- Disposable VM or LXC container (Ubuntu 22.04 LTS or later recommended).
- Snapshot taken **before** any step that mutates system state.
- `sc4s-manager-<version>.tar.gz` and `manifest.json` already built and transferred.
- No docker socket access beyond what the control daemon requires.
- Evidence output path: `docs/acceptance/package-install-<timestamp>.json`.

## Snapshot boundary

Take a snapshot at the state labelled **CLEAN-BASELINE** so rollback to
pre-install state is available if the drill needs to start over.

## Step 0: Confirm artifact integrity

```bash
sha256sum sc4s-manager-<version>.tar.gz
python3 -c "import json; m=json.load(open('manifest.json')); print(m['version'], m['git_commit'])"
```

Record the SHA-256 in the evidence JSON `artifact_sha256` field.

## Step 1: Run the package install validator in dry-run mode

This step validates artifact structure and script syntax without changing system state:

```bash
python3 scripts/validate_package_install.py \
  --dry-run \
  --artifact sc4s-manager-<version>.tar.gz \
  --workdir /tmp/sc4s-manager-package-drill \
  --evidence-out /tmp/sc4s-package-dry-run.json
```

Expected: exit code 0. Review `/tmp/sc4s-package-dry-run.json`.

## Step 2: Clean install

```bash
tar -xzf sc4s-manager-<version>.tar.gz
cd sc4s-manager
sudo bash deploy/install/install.sh --execute
```

Confirm service state:

```bash
systemctl status sc4s-manager.service
systemctl status sc4s-manager-control.service
```

## Step 3: Upgrade from current pilot layout

```bash
sudo bash deploy/upgrade/upgrade.sh --artifact ../sc4s-manager-<new-version>.tar.gz --execute
```

Confirm services restarted and state directories were preserved:

```bash
systemctl status sc4s-manager.service sc4s-manager-control.service
ls /opt/sc4s-manager/state/
ls /opt/sc4s-manager/backups/
```

## Step 4: Rollback

```bash
sudo bash deploy/install/install.sh --rollback
```

or restore from the CLEAN-BASELINE snapshot.

Confirm services are back in the pre-upgrade state:

```bash
systemctl status sc4s-manager.service
```

## Step 5: Service readback commands

```bash
curl -s http://localhost:8080/api/stats | python3 -m json.tool
systemctl is-active sc4s-manager.service
systemctl is-active sc4s-manager-control.service
```

## Step 6: Capture live evidence

Run the validator in live mode to write timestamped evidence:

```bash
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
python3 scripts/validate_package_install.py \
  --artifact sc4s-manager-<version>.tar.gz \
  --workdir /tmp/sc4s-manager-package-drill \
  --evidence-out /tmp/sc4s-package-live-${TIMESTAMP}.json
```

Copy to the acceptance directory:

```bash
cp /tmp/sc4s-package-live-${TIMESTAMP}.json \
   docs/acceptance/package-install-${TIMESTAMP}.json
```

## Redaction checklist

Before committing the evidence file, verify:

- [ ] No HEC tokens, API tokens, or secrets appear unredacted.
- [ ] No internal IP addresses or hostnames beyond what is publicly known.
- [ ] `artifact_sha256` records the SHA-256 of the tarball, not a secret.
- [ ] `commands[].argv` entries are present and redacted where needed.
- [ ] `redaction.findings` lists any found and redacted items.

## Verification commands

```bash
python3 scripts/validate_package_install.py \
  --dry-run \
  --workdir /tmp/sc4s-manager-package-drill \
  --evidence-out /tmp/sc4s-package-dry-run.json

./scripts/test.sh tests/test_release_packaging.py tests/test_package_install_validator.py

python3 scripts/validate_acceptance_evidence.py --require-package-drill
```

The last command is expected to fail until real timestamped evidence exists under
`docs/acceptance/package-install-<timestamp>.json`. Do not mark this drill complete
without live evidence.

## Blockers for live run

A live full drill requires a disposable VM/LXC with systemd available. If running
in a CI-only environment without a VM/LXC, record this as a blocker in the evidence
JSON `install.notes` field and use `--dry-run` only. The dry-run result is **not**
sufficient to satisfy `--require-package-drill` in the release gate — only timestamped
live evidence with `install.ok=true`, `upgrade.ok=true`, and `rollback.ok=true` qualifies.
