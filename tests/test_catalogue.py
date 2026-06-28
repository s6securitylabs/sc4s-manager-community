import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from sc4s_manager.catalogue import build_catalogue_entries, catalogue_detail, catalogue_inventory

BUNDLED_PACK = ROOT / 'packs' / 'commvault_commcell'


def _write_upstream(manager_root: Path) -> None:
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
            'artifact_count': 3,
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
            },
            {
                'origin': 'sc4s-inbuilt',
                'artifact_path': 'docs/sources/vendor/Cisco/asa/index.md',
                'artifact_type': 'source_documentation',
                'source_id': 'cisco_asa',
                'vendor': 'cisco',
                'product': 'asa',
                'sha256': 'sha-docs',
            },
            {
                'origin': 'sc4s-inbuilt',
                'artifact_path': 'package/etc/conf.d/conflib/syslog/app-syslog-commvault_commcell.conf',
                'artifact_type': 'syslog_app_parser',
                'source_id': 'commvault_commcell',
                'vendor': 'commvault',
                'product': 'commcell',
                'sha256': 'sha-commvault',
            },
        ],
    }
    (output_dir / 'sc4s-inbuilt.json').write_text(json.dumps(payload, indent=2) + '\n')


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
                'id': 'community_sonicwall_pr_candidate',
                'display_name': 'Community SonicWall PR candidate',
                'vendor': 'sonicwall',
                'product': 'firewall',
                'relationship_to_upstream': 'extends_upstream',
                'summary': 'Merged PR snippet showing parser adjustments for SonicWall events.',
                'source_kind': 'pull_request',
                'source_status': 'candidate',
                'provenance_url': 'https://github.com/splunk/splunk-connect-for-syslog/pull/5678',
                'artifacts': [
                    {
                        'type': 'github_pull_request',
                        'kind': 'pull_request_file',
                        'path': 'pulls/5678/files/app-sonicwall_firewall.conf',
                        'url': 'https://github.com/splunk/splunk-connect-for-syslog/pull/5678/files',
                    }
                ],
            },
            {
                'id': 'community_qnap_parser_snippet',
                'display_name': 'Community QNAP parser snippet',
                'vendor': 'qnap',
                'product': 'nas',
                'relationship_to_upstream': 'new_pack',
                'summary': 'Parser snippet candidate extracted from a GitHub discussion thread.',
                'source_kind': 'parser_snippet',
                'source_status': 'candidate',
                'provenance_url': 'https://github.com/splunk/splunk-connect-for-syslog/discussions/9012',
                'artifacts': [
                    {
                        'type': 'parser_snippet',
                        'kind': 'syslog_ng_parser_snippet',
                        'path': 'discussions/9012#snippet-qnap',
                        'url': 'https://github.com/splunk/splunk-connect-for-syslog/discussions/9012',
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
                'known_limitations': ['Actually unreviewed community data.'],
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
            },
        ],
    }
    (output_dir / 'community-extra.json').write_text(json.dumps(payload, indent=2) + '\n')


def _pack_tree(tmp_path: Path, relationship: str) -> Path:
    packs_root = tmp_path / 'packs'
    target = packs_root / 'commvault_commcell'
    shutil.copytree(BUNDLED_PACK, target)
    manifest = json.loads((target / 'pack.json').read_text())
    manifest['relationship_to_upstream'] = relationship
    (target / 'pack.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return packs_root


def test_catalogue_entries_merge_upstream_only_next_only_and_extended_entries(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'extends_upstream')
    _write_upstream(manager_root)

    entries = build_catalogue_entries(packs_root, manager_root)
    ids = {entry['id']: entry for entry in entries}

    assert {'cisco_asa', 'commvault_commcell'} <= set(ids)

    upstream_only = ids['cisco_asa']
    assert upstream_only['origins'] == ['sc4s-inbuilt']
    assert upstream_only['relationship_to_upstream'] == 'upstream_only'
    assert upstream_only['quality_status'] == 'catalogued'
    assert upstream_only['capabilities']['parser'] is True
    assert upstream_only['capabilities']['splunk_props_transforms'] is False

    extended = ids['commvault_commcell']
    assert extended['effective_origin'] == 'sechub-resource'
    assert extended['relationship_to_upstream'] == 'extends_upstream'
    assert set(extended['origins']) == {'sc4s-inbuilt', 'sechub-resource'}
    assert extended['capabilities']['parser'] is True
    assert extended['capabilities']['splunk_props_transforms'] is True
    assert extended['capabilities']['fixtures'] is True
    assert extended['upstream']['commit'] == 'abc123'
    assert extended['sc4s_manager']['pack_version'] == '0.1.0'


def test_catalogue_inventory_filters_and_paginates(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'new_pack')
    _write_upstream(manager_root)

    filtered = catalogue_inventory(
        packs_root,
        manager_root,
        {
            'origin': 'sechub-resource',
            'has_splunk_knowledge': 'true',
            'limit': '1',
            'offset': '0',
        },
    )
    assert filtered['count'] == 1
    assert filtered['entries'][0]['id'] == 'commvault_commcell'

    upstream = catalogue_inventory(packs_root, manager_root, {'q': 'cisco asa'})
    assert upstream['count'] == 1
    assert upstream['entries'][0]['id'] == 'cisco_asa'


def test_catalogue_detail_returns_full_entry_and_raises_for_missing(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'new_pack')
    _write_upstream(manager_root)

    detail = catalogue_detail('commvault_commcell', packs_root, manager_root)
    assert detail['feedback'] == {'likes': 0, 'rating_average': None, 'comments_url': None}
    assert detail['presets']
    assert detail['artifacts']
    assert detail['validation']['trust_level'] == 's6_verified'

    try:
        catalogue_detail('missing', packs_root, manager_root)
    except KeyError as exc:
        assert 'missing' in str(exc)
    else:
        raise AssertionError('expected KeyError for missing catalogue entry')


def test_catalogue_detail_includes_drift_field_contract_preset_previews_and_evidence_bundle(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'new_pack')
    _write_upstream(manager_root)
    _write_drift_report(manager_root)

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

    detail = catalogue_detail('commvault_commcell', packs_root, manager_root)

    assert detail['upstream_drift'] == {
        'summary': {'added': 0, 'removed': 0, 'changed': 1},
        'previous_ref': '3.42.0',
        'current_ref': '3.43.0',
        'previous_commit': 'old123',
        'current_commit': 'new456',
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
    assert detail['field_contract_summary']['common']['status'] == 'complete'
    assert detail['field_contract_summary']['cim']['declared_status'] == 'partial'
    assert detail['preset_previews'][0]['id'] == 'basic'
    assert detail['preset_previews'][-1]['id'] == 'enhanced'
    assert detail['preset_previews'][-1]['apply_safety'] == 'preview_required'
    assert detail['preset_previews'][-1]['fixture_impact'] == {'dropped_events': 1, 'retained_events': 2}
    assert detail['validation']['evidence_bundle'] == {
        'pack_id': 'commvault_commcell',
        'paths': [str(generated_json), str(generated_md), str(doc_path)],
        'generated': [str(generated_json), str(generated_md)],
        'docs': [str(doc_path)],
    }
    assert detail['validation']['evidence_paths'] == [str(generated_json), str(generated_md), str(doc_path)]


def test_catalogue_inventory_exposes_facets_for_modern_filter_ui(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'new_pack')
    _write_upstream(manager_root)

    inventory = catalogue_inventory(packs_root, manager_root)

    facets = inventory['facets']
    assert facets['origins'] == [
        {'value': 'sc4s-inbuilt', 'label': 'SC4S built-in', 'count': 2},
        {'value': 'sechub-resource', 'label': 'SecHub Resources SC4S pack', 'count': 1},
    ]
    assert {'value': 'cisco', 'label': 'Cisco', 'count': 1} in facets['vendors']
    assert {'value': 'commvault', 'label': 'Commvault', 'count': 1} in facets['vendors']
    assert {'value': 'syslog_app_parser', 'label': 'syslog app parser', 'count': 2} in facets['artifact_types']
    assert {'value': 'parser', 'label': 'Parser', 'count': 2} in facets['capabilities']
    assert {'value': 'splunk_props_transforms', 'label': 'Splunk knowledge', 'count': 1} in facets['capabilities']
    assert {'value': '3.43.0', 'label': '3.43.0', 'count': 2} in facets['sc4s_versions']


def test_community_pack_keeps_community_origin_and_facets(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = tmp_path / 'packs'
    packs_root.mkdir(parents=True)
    _write_community_candidates(manager_root)

    inventory = catalogue_inventory(packs_root, manager_root, {'source_status': 'candidate'})
    entries = {entry['id']: entry for entry in inventory['entries']}
    entry = entries['community_qnap_parser_snippet']

    assert entry['origins'] == ['community-extra']
    assert entry['effective_origin'] == 'community-extra'
    assert entry['trust_level'] == 'community_submitted'
    assert entry['quality_status'] == 'catalogued'
    assert inventory['facets']['origins'] == [
        {'value': 'community-extra', 'label': 'Community extra', 'count': 4},
    ]


def test_catalogue_requires_product_for_upstream_vendor_only_sources(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = tmp_path / 'packs'
    packs_root.mkdir()
    output_dir = manager_root / 'catalogue' / 'generated' / 'upstream'
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'catalogue_version': '0.1',
        'origin': 'sc4s-inbuilt',
        'upstream': {'requested_ref': '3.43.0'},
        'artifacts': [
            {
                'origin': 'sc4s-inbuilt',
                'artifact_path': 'package/etc/conf.d/conflib/syslog/app-syslog-checkpoint.conf',
                'artifact_type': 'syslog_app_parser',
                'source_id': 'checkpoint',
                'vendor': 'checkpoint',
                'product': None,
                'sha256': 'sha-checkpoint',
            }
        ],
    }
    (output_dir / 'sc4s-inbuilt.json').write_text(json.dumps(payload, indent=2) + '\n')

    inventory = catalogue_inventory(packs_root, manager_root)

    assert inventory['entries'][0]['vendor'] == 'checkpoint'
    assert inventory['entries'][0]['product'] == 'checkpoint'
    assert {'value': 'checkpoint', 'label': 'Checkpoint', 'count': 1} in inventory['facets']['products']


def test_catalogue_quality_score_and_verified_filters(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'new_pack')
    _write_upstream(manager_root)
    _write_validation_evidence(manager_root)

    min_quality = catalogue_inventory(packs_root, manager_root, {'min_quality_score': '4'})
    assert min_quality['count'] == 1
    assert min_quality['entries'][0]['id'] == 'commvault_commcell'
    assert min_quality['entries'][0]['quality_score'] >= 4
    assert min_quality['entries'][0]['is_verified'] is True

    verified = catalogue_inventory(packs_root, manager_root, {'is_verified': 'true'})
    assert verified['count'] == 1
    assert verified['entries'][0]['id'] == 'commvault_commcell'

    unverified = catalogue_inventory(packs_root, manager_root, {'is_verified': 'false'})
    assert unverified['count'] == 1
    assert unverified['entries'][0]['id'] == 'cisco_asa'
    assert unverified['entries'][0]['quality_score'] < 4


def test_catalogue_pack_harness_passed_alone_does_not_promote_validation(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'new_pack')
    _write_upstream(manager_root)
    manifest_path = packs_root / 'commvault_commcell' / 'pack.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['validation_harness'] = {
        'status': 'passed',
        'evidence': ['untrusted pack.json must not self-promote validation'],
    }
    manifest['capabilities'] = {'syntax_validated': True, 'splunk_ingestion_validated': True}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')

    detail = catalogue_detail('commvault_commcell', packs_root, manager_root)

    assert detail['quality_score'] <= 3
    assert detail['is_verified'] is False
    assert detail['capabilities']['syntax_validated'] is False
    assert detail['capabilities']['splunk_ingestion_validated'] is False
    assert detail['validation']['state'] != 'validated_pack'


def test_catalogue_generated_evidence_requires_ok_and_required_passed_stages(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'new_pack')
    _write_upstream(manager_root)

    _write_validation_evidence(manager_root, ok=False)
    failed_detail = catalogue_detail('commvault_commcell', packs_root, manager_root)
    assert failed_detail['quality_score'] <= 3
    assert failed_detail['is_verified'] is False
    assert failed_detail['capabilities']['syntax_validated'] is False
    assert failed_detail['capabilities']['splunk_ingestion_validated'] is False
    assert failed_detail['validation']['state'] != 'validated_pack'

    _write_validation_evidence(
        manager_root,
        statuses={
            'syslog_ng_syntax': 'passed',
            'runtime_pack_validation': 'skipped',
            'splunk_readback': 'skipped',
        },
    )
    skipped_detail = catalogue_detail('commvault_commcell', packs_root, manager_root)
    assert skipped_detail['quality_score'] <= 3
    assert skipped_detail['is_verified'] is False
    assert skipped_detail['capabilities']['syntax_validated'] is True
    assert skipped_detail['capabilities']['splunk_ingestion_validated'] is False
    assert skipped_detail['validation']['state'] != 'validated_pack'


def test_catalogue_docs_validation_evidence_md_alone_does_not_promote_splunk_validation(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'new_pack')
    _write_upstream(manager_root)
    docs_dir = packs_root / 'commvault_commcell' / 'docs'
    docs_dir.mkdir(exist_ok=True)
    (docs_dir / 'validation-evidence.md').write_text('# Local validation evidence\n')

    detail = catalogue_detail('commvault_commcell', packs_root, manager_root)

    assert detail['quality_score'] <= 3
    assert detail['is_verified'] is False
    assert detail['capabilities']['syntax_validated'] is False
    assert detail['capabilities']['splunk_ingestion_validated'] is False
    assert detail['validation']['state'] != 'validated_pack'


def test_catalogue_merges_seeded_community_candidates_without_validated_claims(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'new_pack')
    _write_upstream(manager_root)
    _write_community_candidates(manager_root)

    entries = build_catalogue_entries(packs_root, manager_root)
    ids = {entry['id']: entry for entry in entries}

    issue_candidate = ids['community_pfsense_filterlog_issue']
    assert issue_candidate['origins'] == ['community-extra']
    assert issue_candidate['effective_origin'] == 'community-extra'
    assert issue_candidate['trust_level'] == 'community_submitted'
    assert issue_candidate['quality_status'] == 'catalogued'
    assert issue_candidate['quality_score'] == 2
    assert issue_candidate['is_verified'] is False
    assert issue_candidate['source_status'] == 'candidate'
    assert issue_candidate['provenance']['url'] == 'https://github.com/splunk/splunk-connect-for-syslog/issues/1234'
    assert issue_candidate['provenance']['source_kind'] == 'issue'
    assert issue_candidate['validation']['state'] == 'unvalidated_source_corpus'
    assert issue_candidate['validation']['last_verified_at'] is None
    assert issue_candidate['validation']['summary'] is None
    assert issue_candidate['candidate_warnings']
    assert any('not curated or validated' in warning.lower() for warning in issue_candidate['candidate_warnings'])

    pr_candidate = ids['community_sonicwall_pr_candidate']
    assert pr_candidate['artifacts'][0]['type'] == 'github_pull_request'
    assert pr_candidate['provenance']['source_kind'] == 'pull_request'

    snippet_candidate = ids['community_qnap_parser_snippet']
    assert snippet_candidate['artifacts'][0]['type'] == 'parser_snippet'
    assert snippet_candidate['provenance']['source_kind'] == 'parser_snippet'

    malicious_candidate = ids['community_fortinet_false_validated']
    assert malicious_candidate['trust_level'] == 'community_submitted'
    assert malicious_candidate['quality_status'] == 'catalogued'
    assert malicious_candidate['quality_score'] == 2
    assert malicious_candidate['source_status'] == 'candidate'
    assert malicious_candidate['validation'] == {
        'last_verified_at': None,
        'trust_level': 'community_submitted',
        'evidence_paths': [],
        'validated_by': None,
        'summary': None,
        'state': 'unvalidated_source_corpus',
        'evidence_bundle': None,
    }
    assert 'Already validated for production.' in malicious_candidate['candidate_warnings']
    assert any('not curated or validated' in warning.lower() for warning in malicious_candidate['candidate_warnings'])

    official_entry = ids['commvault_commcell']
    assert official_entry['effective_origin'] == 'sechub-resource'
    assert official_entry['source_status'] is None
    assert official_entry['validation'].get('state') != 'unvalidated_source_corpus'


def test_catalogue_inventory_facets_and_filters_include_community_candidate_status(tmp_path: Path) -> None:
    manager_root = tmp_path / 'manager'
    packs_root = _pack_tree(manager_root, 'new_pack')
    _write_upstream(manager_root)
    _write_community_candidates(manager_root)

    inventory = catalogue_inventory(packs_root, manager_root)
    assert {'value': 'candidate', 'label': 'Candidate', 'count': 4} in inventory['facets']['source_statuses']

    candidate_only = catalogue_inventory(packs_root, manager_root, {'source_status': 'candidate'})
    assert candidate_only['count'] == 4
    assert {entry['id'] for entry in candidate_only['entries']} == {
        'community_pfsense_filterlog_issue',
        'community_sonicwall_pr_candidate',
        'community_qnap_parser_snippet',
        'community_fortinet_false_validated',
    }
