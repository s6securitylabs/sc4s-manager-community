from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "roadmap" / "sc4s-manager-local-docs-index-strategy.md"
COMMUNITY_ROADMAP_PATH = ROOT / "docs" / "roadmap" / "community-catalogue-ingestion-kanban.md"


def test_local_docs_index_strategy_doc_covers_required_design_sections() -> None:
    assert PLAN_PATH.exists(), f"missing plan document: {PLAN_PATH}"
    content = PLAN_PATH.read_text()

    required_headings = [
        "# SC4S Manager local docs and upstream index strategy",
        "## Scope and goals",
        "## Upstream sources and pinning",
        "## Generated local indexes",
        "## Metadata, facets, and provenance",
        "## Update cadence and refresh workflow",
        "## Storage format and generated paths",
        "## How docs, tests, and examples relate to catalogue entries",
        "## Acceptance tests to add",
    ]
    for heading in required_headings:
        assert heading in content, f"missing heading: {heading}"

    required_terms = [
        "docs/sources/vendor",
        "package/etc/conf.d/conflib",
        "package/lite/etc/addons",
        "requested_ref",
        "resolved_commit",
        "catalogue/generated/upstream",
        "catalogue/generated/docs-index",
        "sc4s-inbuilt",
        "sc4s-inbuilt-lite",
        "sechub-resource",
        "community-extra",
        "official",
        "curated",
        "candidate",
        "documentation",
        "test fixture",
        "example",
        "SQLite FTS5",
    ]
    for term in required_terms:
        assert term in content, f"missing design term: {term}"

    assert "Community issue/PR snippets remain unvalidated" in content
    assert "do not auto-promote" in content


def test_community_catalogue_roadmap_references_local_docs_index_strategy() -> None:
    assert COMMUNITY_ROADMAP_PATH.exists(), f"missing roadmap document: {COMMUNITY_ROADMAP_PATH}"
    content = COMMUNITY_ROADMAP_PATH.read_text()
    assert "sc4s-manager-local-docs-index-strategy.md" in content
    assert "local docs index" in content.lower()
