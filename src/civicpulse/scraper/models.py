"""
Shared data models for the CivicPulse scraper pipeline.

Pipeline flow: RawDocument → VaultChunk → (written to disk) → Result (from FTS query)
"""
from dataclasses import dataclass


@dataclass
class RawDocument:
    """A scraped page before cleaning or chunking."""
    url: str               # canonical URL of the scraped page
    html: str              # raw HTML response body
    title: str             # page/document title (extracted from <title> or <h1>)
    document_type: str     # e.g. "meeting-minutes", "agenda", "service-page"
    date: str | None       # ISO 8601 date if parseable, else None
    meeting_id: str | None # meeting identifier for agenda/minutes docs, else None


@dataclass
class VaultChunk:
    """A single vault-ready content chunk ready to be written as a .md file."""
    content: str           # cleaned Markdown text of this chunk
    source_url: str        # canonical URL this chunk came from
    document_type: str     # mirrors RawDocument.document_type
    date: str | None       # ISO 8601 date, may be None
    meeting_id: str | None # meeting identifier, may be None
    title: str             # section heading or document title for this chunk
    chunk_index: int       # zero-based position within the source document
    slug: str              # generated filename slug (used in vault path)


@dataclass
class Result:
    """A single FTS search result returned by FTSIndexer.query()."""
    file_path: str         # absolute path to the vault .md file
    source_url: str        # original source URL
    document_type: str
    date: str | None
    meeting_id: str | None
    title: str
    chunk_index: int
    score: float           # BM25 relevance score (higher = more relevant)
    content_preview: str   # first ~200 characters of the chunk content
