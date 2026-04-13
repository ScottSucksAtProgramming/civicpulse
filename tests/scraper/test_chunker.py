from civicpulse.scraper.chunker import Chunker
from civicpulse.scraper.models import RawDocument


def make_doc(content: str, doc_type: str = "service-page") -> RawDocument:
    return RawDocument(
        url="https://example.gov/page",
        content=content,
        title="Test Page",
        document_type=doc_type,
        date=None,
        meeting_id=None,
    )


LONG = " ".join(["word"] * 120)


def test_two_sections_produce_two_chunks():
    content = f"## Section One\n\n{LONG}\n\n## Section Two\n\n{LONG}"
    chunks = Chunker().chunk(make_doc(content))
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_short_section_merged_with_previous():
    content = f"## Long Section\n\n{LONG}\n\n## Tiny\n\nfew words"
    chunks = Chunker().chunk(make_doc(content))
    assert len(chunks) == 1


def test_all_required_fields_present():
    content = f"## Only Section\n\n{LONG}"
    chunk = Chunker().chunk(make_doc(content))[0]
    assert chunk.source_url
    assert chunk.document_type
    assert chunk.title
    assert chunk.slug
    assert chunk.chunk_index == 0


def test_slug_is_deterministic():
    doc = make_doc(f"## Section\n\n{LONG}")
    assert Chunker().chunk(doc)[0].slug == Chunker().chunk(doc)[0].slug
