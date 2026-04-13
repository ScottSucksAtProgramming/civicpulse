import frontmatter

from civicpulse.scraper.models import VaultChunk
from civicpulse.scraper.writer import VaultWriter


def make_chunk(**kwargs) -> VaultChunk:
    defaults = dict(
        content="Body text here.",
        source_url="https://example.gov/page",
        document_type="service-page",
        date="2026-03-15",
        meeting_id=None,
        title="Test Chunk",
        chunk_index=0,
        slug="test-chunk-0",
    )
    return VaultChunk(**{**defaults, **kwargs})


def test_writes_file_at_correct_path(tmp_path):
    chunk = make_chunk(document_type="meeting-minutes", date="2026-03-15", chunk_index=0)
    path = VaultWriter(tmp_path).write(chunk)
    assert path.parts[-3] == "meeting-minutes"
    assert path.parts[-2] == "2026"
    assert path.exists()


def test_undated_chunk_goes_to_undated_dir(tmp_path):
    chunk = make_chunk(date=None)
    path = VaultWriter(tmp_path).write(chunk)
    assert "undated" in str(path)


def test_frontmatter_roundtrip(tmp_path):
    chunk = make_chunk()
    path = VaultWriter(tmp_path).write(chunk)
    post = frontmatter.load(path)
    assert post["source_url"] == chunk.source_url
    assert post["document_type"] == chunk.document_type
    assert post["chunk_index"] == chunk.chunk_index
    assert post.content == chunk.content


def test_overwrite_does_not_duplicate(tmp_path):
    chunk = make_chunk()
    VaultWriter(tmp_path).write(chunk)
    VaultWriter(tmp_path).write(chunk)
    assert len(list(tmp_path.rglob("*.md"))) == 1
