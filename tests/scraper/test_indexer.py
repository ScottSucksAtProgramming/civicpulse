from pathlib import Path

from civicpulse.scraper.indexer import FTSIndexer
from civicpulse.scraper.models import VaultChunk
from civicpulse.scraper.writer import VaultWriter


def write_chunk(vault: Path, **kwargs) -> Path:
    defaults = dict(
        content="Some civic content about zoning variances.",
        source_url="https://example.gov/p",
        document_type="planning",
        date="2026-01-01",
        meeting_id=None,
        title="Zoning Page",
        chunk_index=0,
        slug="zoning-page-0",
    )
    return VaultWriter(vault).write(VaultChunk(**{**defaults, **kwargs}))


def test_query_returns_matching_chunk(tmp_path):
    write_chunk(tmp_path, content="The zoning variance was approved by the board.")
    write_chunk(
        tmp_path,
        content="Budget appropriations for the fiscal year.",
        slug="budget-0",
        title="Budget",
    )
    FTSIndexer(tmp_path).index()
    results = FTSIndexer(tmp_path).query("zoning")
    assert len(results) >= 1
    assert "zoning" in results[0].content_preview.lower()


def test_empty_vault_returns_empty_list(tmp_path):
    assert FTSIndexer(tmp_path).query("anything") == []


def test_incremental_update_picks_up_new_file(tmp_path):
    write_chunk(tmp_path)
    FTSIndexer(tmp_path).index()
    write_chunk(
        tmp_path,
        content="New content about recycling programs.",
        slug="recycle-0",
        title="Recycling",
        chunk_index=1,
    )
    FTSIndexer(tmp_path).index()
    results = FTSIndexer(tmp_path).query("recycling")
    assert len(results) >= 1


def test_document_type_filter(tmp_path):
    write_chunk(
        tmp_path,
        document_type="planning",
        content="Planning board approved the subdivision.",
        slug="plan-0",
    )
    write_chunk(
        tmp_path,
        document_type="foil",
        content="FOIL request processing time planning.",
        slug="foil-0",
        chunk_index=1,
    )
    FTSIndexer(tmp_path).index()
    results = FTSIndexer(tmp_path).query("planning", filters={"document_type": "foil"})
    assert all(r.document_type == "foil" for r in results)


def test_deleted_file_removed_from_index(tmp_path):
    path = write_chunk(tmp_path, content="Temporary content about permits.")
    FTSIndexer(tmp_path).index()
    path.unlink()
    FTSIndexer(tmp_path).index()
    assert FTSIndexer(tmp_path).query("permits") == []
