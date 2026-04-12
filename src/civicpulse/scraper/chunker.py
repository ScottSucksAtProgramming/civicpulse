"""
Chunker — splits a RawDocument into VaultChunks on section boundaries.

Splits on <h2>, <h3>, and double-newline paragraph boundaries.
Minimum chunk size: ~100 words. Orphaned short chunks are merged with
the preceding chunk. Assembles YAML frontmatter fields from RawDocument metadata.

Interface:
    chunker = Chunker()
    chunks: list[VaultChunk] = chunker.chunk(doc)
"""
from civicpulse.scraper.models import RawDocument, VaultChunk


class Chunker:
    """Segments a RawDocument into section-aligned VaultChunks."""

    def chunk(self, doc: RawDocument) -> list[VaultChunk]:
        """Split doc into section-aligned VaultChunks with populated frontmatter."""
        raise NotImplementedError
