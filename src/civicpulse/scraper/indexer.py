"""
FTSIndexer — builds and queries a SQLite FTS5 full-text search index over the vault.

Index schema: fts_index(title, content, source_url, document_type, date,
                        meeting_id, chunk_index, file_path)
Index location: vault/.index.db (gitignored)
Incremental updates: tracks file modification times; only re-indexes changed files.

Interface:
    indexer = FTSIndexer(vault_path=Path("./vault"))
    indexer.index()                                          # build/update index
    results: list[Result] = indexer.query("zoning variance", filters={"document_type": "ordinance"})
"""
from pathlib import Path
from civicpulse.scraper.models import Result


class FTSIndexer:
    """Builds and queries a SQLite FTS5 index over the knowledge vault."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path

    def index(self) -> None:
        """Build or incrementally update the FTS5 index from vault contents."""
        raise NotImplementedError

    def query(self, q: str, filters: dict | None = None, top_n: int = 10) -> list[Result]:
        """Return top_n BM25-ranked Results matching q, optionally filtered by metadata."""
        raise NotImplementedError
