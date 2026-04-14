import shutil

import frontmatter

from civicpulse.scraper.importers.ecode360 import ECodeImporter, SectionChunker
from civicpulse.scraper.indexer import FTSIndexer

LONG_SECTION = " ".join(["fence"] * 130)


def test_section_chunker_splits_markdown_on_section_boundaries():
    markdown = (
        "# Chapter 120 Zoning\n\n"
        "Town of Babylon Code\n\n"
        "§ 120-1 Title.\n\n"
        f"{LONG_SECTION}\n\n"
        "§ 120-2 Purpose.\n\n"
        f"{LONG_SECTION}"
    )

    chunks = SectionChunker().chunk(
        markdown=markdown,
        title="Chapter 120 Zoning",
        source_url="https://ecode360.com/8789068#120-1",
    )

    assert len(chunks) == 2
    assert chunks[0].document_type == "ordinance"
    assert chunks[0].section_number == "120-1"
    assert chunks[1].section_number == "120-2"


def test_section_chunker_merges_short_sections_with_following_section():
    markdown = (
        "§ 120-10 Definitions.\n\n"
        "Short lead in.\n\n"
        "§ 120-11 Fence height.\n\n"
        f"{LONG_SECTION}"
    )

    chunks = SectionChunker(min_words=20).chunk(
        markdown=markdown,
        title="Chapter 120 Zoning",
        source_url="https://ecode360.com/8789068#120-10",
    )

    assert len(chunks) == 1
    assert chunks[0].section_number == "120-10"
    assert "§ 120-10" in chunks[0].content
    assert "§ 120-11" in chunks[0].content


def test_section_chunker_strips_preamble_and_headers():
    markdown = (
        "# Part II General Legislation\n\n"
        "Town of Babylon\n\n"
        "Page 1 of 300\n\n"
        "Part II General Legislation\n\n"
        "§ 120-167 Fences.\n\n"
        f"{LONG_SECTION}\n\n"
        "Page 2 of 300\n\n"
        "Part II General Legislation\n\n"
        "§ 120-168 Gates.\n\n"
        f"{LONG_SECTION}"
    )

    chunks = SectionChunker().chunk(
        markdown=markdown,
        title="Part II General Legislation",
        source_url="https://ecode360.com/8789068#120-167",
    )

    assert len(chunks) == 2
    assert "Page 1 of 300" not in chunks[0].content
    assert "Page 2 of 300" not in chunks[1].content
    assert "Town of Babylon" not in chunks[0].content


class StubConverter:
    def __init__(self, markdown_by_name: dict[str, str]) -> None:
        self.markdown_by_name = markdown_by_name

    def convert(self, pdf_path):
        return self.markdown_by_name[pdf_path.name]


def test_ecode_importer_writes_ordinance_chunks_with_section_metadata(tmp_path):
    source_dir = tmp_path / "data" / "ecode360"
    source_dir.mkdir(parents=True)
    fixture_pdf = "tests/scraper/fixtures/body_date.pdf"
    pdf_path = source_dir / "Part II General Legislation.pdf"
    shutil.copyfile(fixture_pdf, pdf_path)

    importer = ECodeImporter(
        vault_path=tmp_path / "vault",
        converter=StubConverter(
            {
                "Part II General Legislation.pdf": (
                    "§ 120-167 Fence height.\n\n"
                    f"{LONG_SECTION}\n\n"
                    "§ 120-168 Gates.\n\n"
                    f"{LONG_SECTION}"
                )
            }
        ),
    )

    imported = importer.import_path(source_dir)

    assert imported == 2
    chunk_files = sorted((tmp_path / "vault" / "ordinance").rglob("*.md"))
    assert len(chunk_files) == 2

    first_chunk = frontmatter.load(chunk_files[0])
    assert first_chunk["document_type"] == "ordinance"
    assert first_chunk["section_number"] == "120-167"
    assert first_chunk["source_url"].startswith("https://ecode360.com")

    FTSIndexer(tmp_path / "vault").index()
    results = FTSIndexer(tmp_path / "vault").query("fence")
    assert results
    assert results[0].document_type == "ordinance"
