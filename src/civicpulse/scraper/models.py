"""
Shared data models for the CivicPulse scraper pipeline.

Pipeline flow: RawDocument → VaultChunk → (written to disk) → Result (from FTS query)
"""
from dataclasses import dataclass, field


@dataclass
class RawDocument:
    """A scraped page before cleaning or chunking."""
    url: str               # canonical URL of the scraped page
    content: str           # cleaned text content (plain text with Markdown headings)
    title: str             # page/document title (extracted from <title> or <h1>)
    document_type: str     # e.g. "meeting-minutes", "agenda", "service-page"
    date: str | None       # ISO 8601 date if parseable, else None
    meeting_id: str | None # meeting identifier for agenda/minutes docs, else None
    extra_metadata: dict[str, str | int | None] = field(default_factory=dict)


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
    extra_metadata: dict[str, str | int | None] = field(default_factory=dict)

    @property
    def section_number(self) -> str | None:
        value = self.extra_metadata.get("section_number")
        return value if isinstance(value, str) else None

    @property
    def video_id(self) -> str | None:
        value = self.extra_metadata.get("video_id")
        return value if isinstance(value, str) else None

    @property
    def video_title(self) -> str | None:
        value = self.extra_metadata.get("video_title")
        return value if isinstance(value, str) else None

    @property
    def published_at(self) -> str | None:
        value = self.extra_metadata.get("published_at")
        return value if isinstance(value, str) else None

    @property
    def timestamp_start(self) -> int | None:
        value = self.extra_metadata.get("timestamp_start")
        return value if isinstance(value, int) else None


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
