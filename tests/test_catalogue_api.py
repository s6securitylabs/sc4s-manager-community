import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('SC4S_MANAGER_ROOT', str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from sc4s_manager.app import catalogue_detail, catalogue_inventory


def _seed_upstream_catalogue(tmp_path: Path) -> Path:
    manager_root = tmp_path / 'manager'
    output_dir = manager_root / 'catalogue' / 'generated' / 'upstream'
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'catalogue_version': '0.1',
        'origin': 'sc4s-inbuilt',
        'upstream': {
            'repo_url': 'https://github.com/splunk/splunk-connect-for-syslog.git',
            'requested_ref': '3.43.0',
            'resolved_commit': 'abc123',
            'generated_at': '2026-05-27T15:00:00Z',
            'artifact_count': 1,
        },
        'artifacts': [
            {
                'origin': 'sc4s-inbuilt',
                'artifact_path': 'package/etc/conf.d/conflib/syslog/app-syslog-cisco_asa.conf',
                'artifact_type': 'syslog_app_parser',
                'source_id': 'cisco_asa',
                'vendor': 'cisco',
                'product': 'asa',
                'sha256': 'sha-cisco',
            }
        ],
    }
    (output_dir / 'sc4s-inbuilt.json').write_text(json.dumps(payload, indent=2) + '\n')
    return manager_root


def _write_drift_report(manager_root: Path) -> None:
    output_dir = manager_root / 'catalogue' / 'generated' / 'upstream'
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'metadata': {
            'previous_ref': '3.42.0',
            'current_ref': '3.43.0',
            'previous_commit': 'old123',
            'current_commit': 'new456',
        },
        'added': [],
        'removed': [],
        'changed': [
            {
                'source_id': 'commvault_commcell',
                'artifact_path': 'package/etc/conf.d/conflib/syslog/app-syslog-commvault_commcell.conf',
                'change_types': ['parser', 'config'],
                'before': {'source_id': 'commvault_commcell', 'sha256': 'before-sha'},
                'after': {'source_id': 'commvault_commcell', 'sha256': 'after-sha'},
            }
        ],
    }
    (output_dir / 'drift-report.json').write_text(json.dumps(payload, indent=2) + '\n')


def _write_validation_evidence(
    manager_root: Path,
    pack_id: str = 'commvault_commcell',
    *,
    ok: bool = True,
    statuses: dict[str, str] | None = None,
) -> Path:
    statuses = statuses or {
        'syslog_ng_syntax': 'passed',
        'runtime_pack_validation': 'passed',
        'splunk_readback': 'passed',
    }
    generated_dir = manager_root / 'catalogue' / 'generated' / 'validation' / pack_id
    generated_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = generated_dir / 'validation-evidence.json'
    evidence_path.write_text(
        json.dumps(
            {
                'pack_id': pack_id,
                'ok': ok,
                'checks': [
                    {'stage': stage, 'ok': status == 'passed', 'details': {'status': status}}
                    for stage, status in statuses.items()
                ],
            },
            indent=2,
        )
        + '\n'
    )
    return evidence_path


def _write_community_candidates(manager_root: Path) -> None:
    output_dir = manager_root / 'catalogue' / 'generated' / 'community'
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'catalogue_version': '0.1',
        'origin': 'community-extra',
        'generated_at': '2026-05-27T18:00:00Z',
        'entries': [
            {
                'id': 'community_pfsense_filterlog_issue',
                'display_name': 'Community pfSense Filterlog issue candidate',
                'vendor': 'pfsense',
                'product': 'filterlog',
                'relationship_to_upstream': 'new_pack',
                'summary': 'GitHub issue snippet discussing pfSense filterlog parsing gaps.',
                'source_kind': 'issue',
                'source_status': 'candidate',
                'provenance_url': 'https://github.com/splunk/splunk-connect-for-syslog/issues/1234',
                'artifacts': [
                    {
                        'type': 'github_issue',
                        'kind': 'issue_comment_snippet',
                        'path': 'issues/1234#issuecomment-1',
                        'url': 'https://github.com/splunk/splunk-connect-for-syslog/issues/1234#issuecomment-1',
                    }
                ],
            },
            {
                'id': 'community_fortinet_false_validated',
                'display_name': 'Community Fortinet false validated candidate',
                'vendor': 'fortinet',
                'product': 'fortigate',
                'relationship_to_upstream': 'extends_upstream',
                'summary': 'Malicious community fixture that overstates validation metadata.',
                'source_kind': 'issue',
                'source_status': 'validated',
                'trust_level': 's6_verified',
                'quality_status': 'validated',
                'validation_state': 'validated_pack',
                'candidate_warnings': ['Already validated for production.'],
                'validated_by': 'malicious fixture',
                'evidence': 'Pretend Splunk proof',
                'provenance_url': 'https://github.com/splunk/splunk-connect-for-syslog/issues/9999',
                'artifacts': [
                    {
                        'type': 'github_issue',
                        'kind': 'issue_comment_snippet',
                        'path': 'issues/9999#issuecomment-1',
                        'url': 'https://github.com/splunk/splunk-connect-for-syslog/issues/9999#issuecomment-1',
                    }
                ],
            }
        ],
    }
    (output_dir / 'community-extra.json').write_text(json.dumps(payload, indent=2) + '\n')


def _update_pack_manifest(pack_dir: Path, updates: dict) -> None:
    manifest = pack_dir / 'pack.json'
    payload = json.loads(manifest.read_text())
    payload.update(updates)
    manifest.write_text(json.dumps(payload, indent=2) + '\n')


def test_catalogue_api_inventory_contract_includes_merged_metadata(tmp_path: Path, monkeypatch) -> None:
    manager_root = _seed_upstream_catalogue(tmp_path)
    packs_root = tmp_path / 'packs'
    shutil.copytree(ROOT / 'packs', packs_root)
    monkeypatch.setattr('sc4s_manager.app.MANAGER_ROOT', manager_root)
    monkeypatch.setattr('sc4s_manager.app.PACK_DIR', packs_root)

    response = catalogue_inventory({'limit': '50', 'offset': '0'})
    assert set(response) == {'entries', 'count', 'limit', 'offset', 'facets'}
    assert response['facets']['origins']
    assert response['count'] == len(response['entries'])
    entry_ids = {entry['id'] for entry in response['entries']}
    assert 'commvault_commcell' in entry_ids
    assert 'cisco_asa' in entry_ids


def test_catalogue_api_detail_contract_contains_provenance_comparison_and_feedback(tmp_path: Path, monkeypatch) -> None:
    manager_root = _seed_upstream_catalogue(tmp_path)
    packs_root = tmp_path / 'packs'
    shutil.copytree(ROOT / 'packs', packs_root)
    monkeypatch.setattr('sc4s_manager.app.MANAGER_ROOT', manager_root)
    monkeypatch.setattr('sc4s_manager.app.PACK_DIR', packs_root)

    detail = catalogue_detail('commvault_commcell')
    assert detail['effective_origin'] == 'sechub-resource'
    assert detail['comparison_to_upstream']['relationship'] == 'new_pack'
    assert detail['feedback'] == {'likes': 0, 'rating_average': None, 'comments_url': None}
    assert detail['artifacts']
    assert detail['sc4s_manager']['schema_version'] == '0.1'


def test_catalogue_api_detail_exposes_drift_field_contract_preset_previews_and_evidence_bundle(tmp_path: Path, monkeypatch) -> None:
    manager_root = _seed_upstream_catalogue(tmp_path)
    _write_drift_report(manager_root)
    packs_root = tmp_path / 'packs'
    shutil.copytree(ROOT / 'packs', packs_root)
    monkeypatch.setattr('sc4s_manager.app.MANAGER_ROOT', manager_root)
    monkeypatch.setattr('sc4s_manager.app.PACK_DIR', packs_root)

    pack_dir = packs_root / 'commvault_commcell'
    docs_dir = pack_dir / 'docs'
    docs_dir.mkdir(exist_ok=True)
    doc_path = docs_dir / 'validation-evidence.md'
    doc_path.write_text('# Local validation evidence\n')

    generated_dir = manager_root / 'catalogue' / 'generated' / 'validation' / 'commvault_commcell'
    generated_dir.mkdir(parents=True, exist_ok=True)
    generated_json = generated_dir / 'validation-evidence.json'
    generated_md = generated_dir / 'validation-evidence.md'
    _write_validation_evidence(manager_root)
    generated_md.write_text('# Generated validation evidence\n')

    detail = catalogue_detail('commvault_commcell')

    assert detail['upstream_drift']['summary'] == {'added': 0, 'removed': 0, 'changed': 1}
    assert detail['upstream_drift']['previous_ref'] == '3.42.0'
    assert detail['upstream_drift']['current_ref'] == '3.43.0'
    assert detail['field_contract_summary']['common']['status'] == 'complete'
    assert detail['field_contract_summary']['cim']['declared_status'] == 'partial'
    assert [preview['id'] for preview in detail['preset_previews']] == ['basic', 'standard', 'enhanced']
    assert detail['preset_previews'][-1]['requires_opt_in'] is True
    assert detail['preset_previews'][-1]['apply_safety'] == 'preview_required'
    assert detail['validation']['evidence_bundle'] == {
        'pack_id': 'commvault_commcell',
        'paths': [str(generated_json), str(generated_md), str(doc_path)],
        'generated': [str(generated_json), str(generated_md)],
        'docs': [str(doc_path)],
    }


def test_catalogue_api_accepts_product_verified_and_min_quality_filters(tmp_path: Path, monkeypatch) -> None:
    manager_root = _seed_upstream_catalogue(tmp_path)
    packs_root = tmp_path / 'packs'
    shutil.copytree(ROOT / 'packs', packs_root)
    _write_validation_evidence(manager_root)
    monkeypatch.setattr('sc4s_manager.app.MANAGER_ROOT', manager_root)
    monkeypatch.setattr('sc4s_manager.app.PACK_DIR', packs_root)

    response = catalogue_inventory({'product': 'commcell', 'is_verified': 'true', 'min_quality_score': '4'})

    assert response['count'] == 1
    assert response['entries'][0]['id'] == 'commvault_commcell'
    assert response['entries'][0]['product'] == 'commcell'
    assert response['entries'][0]['is_verified'] is True


def test_catalogue_api_does_not_promote_date_and_prose_without_structured_evidence(tmp_path: Path, monkeypatch) -> None:
    manager_root = _seed_upstream_catalogue(tmp_path)
    packs_root = tmp_path / 'packs'
    shutil.copytree(ROOT / 'packs', packs_root)
    _update_pack_manifest(
        packs_root / 'commvault_commcell',
        {
            'trust_level': 's6_verified',
            'quality_status': 'validated',
            'validation': {
                'date_validated': '2026-05-26',
                'validated_by': 'S6 Security Labs lab validation',
                'source_log_version': 'fixture metadata only',
                'sc4s_version': '3.43.0',
                'splunk_version': '10.2.3',
                'evidence': 'SC4S TLS 20029 -> Splunk HEC -> index=commvault claimed in prose only.',
            },
        },
    )
    monkeypatch.setattr('sc4s_manager.app.MANAGER_ROOT', manager_root)
    monkeypatch.setattr('sc4s_manager.app.PACK_DIR', packs_root)

    detail = catalogue_detail('commvault_commcell')

    assert detail['trust_level'] == 's6_verified'
    assert detail['quality_status'] == 'validated'
    assert detail['quality_score'] <= 3
    assert detail['is_verified'] is False
    assert detail['capabilities']['syntax_validated'] is False
    assert detail['capabilities']['splunk_ingestion_validated'] is False
    assert detail['validation']['state'] != 'validated_pack'


def test_catalogue_api_does_not_promote_blocked_validation_harness(tmp_path: Path, monkeypatch) -> None:
    manager_root = _seed_upstream_catalogue(tmp_path)
    packs_root = tmp_path / 'packs'
    shutil.copytree(ROOT / 'packs', packs_root)
    _update_pack_manifest(
        packs_root / 'commvault_commcell',
        {
            'trust_level': 's6_verified',
            'quality_status': 'validated',
            'validation_harness': {
                'status': 'blocked',
                'evidence': ['blocked harness output must not count as validation proof'],
            },
            'validation': {
                'date_validated': '2026-05-26',
                'validated_by': 'S6 Security Labs lab validation',
                'source_log_version': 'fixture metadata only',
                'sc4s_version': '3.43.0',
                'splunk_version': '10.2.3',
                'evidence': 'Splunk HEC index readback claimed in prose while the harness is blocked.',
            },
        },
    )
    monkeypatch.setattr('sc4s_manager.app.MANAGER_ROOT', manager_root)
    monkeypatch.setattr('sc4s_manager.app.PACK_DIR', packs_root)

    detail = catalogue_detail('commvault_commcell')

    assert detail['quality_score'] <= 3
    assert detail['is_verified'] is False
    assert detail['capabilities']['syntax_validated'] is False
    assert detail['capabilities']['splunk_ingestion_validated'] is False
    assert detail['validation']['state'] != 'validated_pack'


def test_catalogue_api_does_not_promote_pack_json_harness_passed_alone(tmp_path: Path, monkeypatch) -> None:
    manager_root = _seed_upstream_catalogue(tmp_path)
    packs_root = tmp_path / 'packs'
    shutil.copytree(ROOT / 'packs', packs_root)
    _update_pack_manifest(
        packs_root / 'commvault_commcell',
        {
            'quality_status': 'validated',
            'validation_harness': {
                'status': 'passed',
                'evidence': ['untrusted serialized harness should not be local proof'],
            },
            'capabilities': {'syntax_validated': True, 'splunk_ingestion_validated': True},
        },
    )
    monkeypatch.setattr('sc4s_manager.app.MANAGER_ROOT', manager_root)
    monkeypatch.setattr('sc4s_manager.app.PACK_DIR', packs_root)

    detail = catalogue_detail('commvault_commcell')

    assert detail['quality_score'] <= 3
    assert detail['is_verified'] is False
    assert detail['capabilities']['syntax_validated'] is False
    assert detail['capabilities']['splunk_ingestion_validated'] is False
    assert detail['validation']['state'] != 'validated_pack'


def test_catalogue_api_generated_evidence_ok_false_or_skipped_runtime_does_not_verify(tmp_path: Path, monkeypatch) -> None:
    manager_root = _seed_upstream_catalogue(tmp_path)
    packs_root = tmp_path / 'packs'
    shutil.copytree(ROOT / 'packs', packs_root)
    monkeypatch.setattr('sc4s_manager.app.MANAGER_ROOT', manager_root)
    monkeypatch.setattr('sc4s_manager.app.PACK_DIR', packs_root)

    _write_validation_evidence(manager_root, ok=False)
    failed_detail = catalogue_detail('commvault_commcell')
    assert failed_detail['quality_score'] <= 3
    assert failed_detail['is_verified'] is False
    assert failed_detail['validation']['state'] != 'validated_pack'

    _write_validation_evidence(
        manager_root,
        statuses={
            'syslog_ng_syntax': 'passed',
            'runtime_pack_validation': 'skipped',
            'splunk_readback': 'skipped',
        },
    )
    skipped_detail = catalogue_detail('commvault_commcell')
    assert skipped_detail['quality_score'] <= 3
    assert skipped_detail['is_verified'] is False
    assert skipped_detail['capabilities']['syntax_validated'] is True
    assert skipped_detail['capabilities']['splunk_ingestion_validated'] is False
    assert skipped_detail['validation']['state'] != 'validated_pack'


def test_catalogue_api_docs_validation_evidence_md_alone_does_not_promote_splunk(tmp_path: Path, monkeypatch) -> None:
    manager_root = _seed_upstream_catalogue(tmp_path)
    packs_root = tmp_path / 'packs'
    shutil.copytree(ROOT / 'packs', packs_root)
    docs_dir = packs_root / 'commvault_commcell' / 'docs'
    docs_dir.mkdir(exist_ok=True)
    (docs_dir / 'validation-evidence.md').write_text('# Local validation evidence\n')
    monkeypatch.setattr('sc4s_manager.app.MANAGER_ROOT', manager_root)
    monkeypatch.setattr('sc4s_manager.app.PACK_DIR', packs_root)

    detail = catalogue_detail('commvault_commcell')

    assert detail['quality_score'] <= 3
    assert detail['is_verified'] is False
    assert detail['capabilities']['syntax_validated'] is False
    assert detail['capabilities']['splunk_ingestion_validated'] is False
    assert detail['validation']['state'] != 'validated_pack'


def test_catalogue_api_returns_candidate_provenance_and_status_for_community_entries(tmp_path: Path, monkeypatch) -> None:
    manager_root = _seed_upstream_catalogue(tmp_path)
    _write_community_candidates(manager_root)
    packs_root = tmp_path / 'packs'
    shutil.copytree(ROOT / 'packs', packs_root)
    monkeypatch.setattr('sc4s_manager.app.MANAGER_ROOT', manager_root)
    monkeypatch.setattr('sc4s_manager.app.PACK_DIR', packs_root)

    inventory = catalogue_inventory({'origin': 'community-extra', 'source_status': 'candidate'})
    assert inventory['count'] == 2
    assert {'value': 'candidate', 'label': 'Candidate', 'count': 2} in inventory['facets']['source_statuses']
    entry = inventory['entries'][0]
    assert entry['id'] == 'community_pfsense_filterlog_issue'
    assert entry['source_status'] == 'candidate'
    assert entry['provenance_url'] == 'https://github.com/splunk/splunk-connect-for-syslog/issues/1234'
    assert entry['candidate_warnings']

    detail = catalogue_detail('community_pfsense_filterlog_issue')
    assert detail['provenance']['url'] == 'https://github.com/splunk/splunk-connect-for-syslog/issues/1234'
    assert detail['provenance']['source_kind'] == 'issue'
    assert detail['validation']['state'] == 'unvalidated_source_corpus'

    malicious = catalogue_detail('community_fortinet_false_validated')
    assert malicious['trust_level'] == 'community_submitted'
    assert malicious['quality_status'] == 'catalogued'
    assert malicious['source_status'] == 'candidate'
    assert malicious['validation'] == {
        'last_verified_at': None,
        'trust_level': 'community_submitted',
        'evidence_paths': [],
        'validated_by': None,
        'summary': None,
        'state': 'unvalidated_source_corpus',
        'evidence_bundle': None,
    }
