import os
import re
from pathlib import Path
from typing import Protocol

from slugify import slugify

from civicpulse.scraper.indexer import FTSIndexer
from civicpulse.scraper.models import VaultChunk
from civicpulse.scraper.writer import VaultWriter

ECODE_CUSTOMER = os.getenv("CIVICPULSE_ECODE_CUSTOMER", "BA0924")
ECODE_BASE_URL = f"https://ecode360.com/{ECODE_CUSTOMER}"


class MarkdownConverter(Protocol):
    def convert(self, pdf_path: Path) -> str: ...


class MarkItDownConverter:
    def __init__(self) -> None:
        try:
            from markitdown import MarkItDown
        except ImportError as exc:
            raise RuntimeError(
                "markitdown is required for eCode360 PDF import. "
                "Install project dependencies first."
            ) from exc

        self._converter = MarkItDown()

    def convert(self, pdf_path: Path) -> str:
        result = self._converter.convert(str(pdf_path))
        for attr in ("text_content", "markdown", "text_content_markdown", "text"):
            value = getattr(result, attr, None)
            if isinstance(value, str) and value.strip():
                return value
        if isinstance(result, str) and result.strip():
            return result
        raise RuntimeError(f"markitdown returned no markdown for {pdf_path}")


class SectionChunker:
    def __init__(self, min_words: int = 80) -> None:
        self._min_words = min_words

    def chunk(self, *, markdown: str, title: str, source_url: str) -> list[VaultChunk]:
        cleaned = self._strip_noise(markdown)
        sections = self._split_sections(cleaned)
        merged = self._merge_short_sections(sections)

        base_slug = slugify(title)[:60] or "ordinance"
        chunks: list[VaultChunk] = []
        for index, section in enumerate(merged):
            section_number = self._extract_section_number(section)
            chunk_title = section.splitlines()[0].strip() if section.strip() else title
            chunks.append(
                VaultChunk(
                    content=section.strip(),
                    source_url=self._section_url(section_number),
                    document_type="ordinance",
                    date=None,
                    meeting_id=None,
                    title=chunk_title,
                    chunk_index=index,
                    slug=f"{base_slug}-{section_number or index}",
                    extra_metadata={"section_number": section_number},
                )
            )
        return chunks

    def _strip_noise(self, markdown: str) -> str:
        lines = []
        for line in markdown.splitlines():
            stripped = line.strip()
            if not stripped:
                lines.append("")
                continue
            if re.fullmatch(r"Page \d+ of \d+", stripped):
                continue
            if stripped.lower() == "town of babylon":
                continue
            if stripped.lower().startswith("part ") and "legislation" in stripped.lower():
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def _split_sections(self, markdown: str) -> list[str]:
        matches = list(re.finditer(r"(?m)^§\s*[A-Z0-9-]+", markdown))
        if not matches:
            return [markdown.strip()] if markdown.strip() else []

        sections: list[str] = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
            section = markdown[match.start():end].strip()
            if section:
                sections.append(section)
        return sections

    def _merge_short_sections(self, sections: list[str]) -> list[str]:
        merged: list[str] = []
        index = 0
        while index < len(sections):
            current = sections[index].strip()
            if len(current.split()) < self._min_words and index + 1 < len(sections):
                current = f"{current}\n\n{sections[index + 1].strip()}"
                index += 1
            merged.append(current)
            index += 1
        return merged

    @staticmethod
    def _extract_section_number(section: str) -> str | None:
        match = re.search(r"§\s*([A-Z0-9-]+)", section)
        return match.group(1) if match else None

    @staticmethod
    def _section_url(section_number: str | None) -> str:
        if not section_number:
            return ECODE_BASE_URL
        return f"{ECODE_BASE_URL}#{section_number}"


class ECodeImporter:
    def __init__(
        self,
        vault_path: Path,
        converter: MarkdownConverter | None = None,
        chunker: SectionChunker | None = None,
    ) -> None:
        self._vault_path = vault_path
        self._converter = converter or MarkItDownConverter()
        self._chunker = chunker or SectionChunker()
        self._writer = VaultWriter(vault_path)
        self._indexer = FTSIndexer(vault_path)

    def import_path(self, source_dir: Path) -> int:
        total_chunks = 0
        for pdf_path in sorted(source_dir.glob("*.pdf")):
            markdown = self._converter.convert(pdf_path)
            for chunk in self._chunker.chunk(
                markdown=markdown,
                title=self._title_from_path(pdf_path),
                source_url=pdf_path.as_posix(),
            ):
                self._writer.write(chunk)
                total_chunks += 1
        self._indexer.index()
        return total_chunks

    @staticmethod
    def _title_from_path(pdf_path: Path) -> str:
        return pdf_path.stem.replace("-", " ").strip()
