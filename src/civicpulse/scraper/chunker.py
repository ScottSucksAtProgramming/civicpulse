import re
from urllib.parse import urlparse

from slugify import slugify

from civicpulse.scraper.models import RawDocument, VaultChunk


class Chunker:
    def chunk(self, doc: RawDocument) -> list[VaultChunk]:
        sections = re.split(r"\n(?=#{1,3} )", doc.content.strip())
        if len(sections) <= 1:
            sections = [s for s in doc.content.split("\n\n") if s.strip()]

        raw_chunks: list[str] = []
        current = ""
        for section in sections:
            if len(current.split()) + len(section.split()) < 100 and current:
                current += "\n\n" + section
            elif len(current.split()) < 100 and not raw_chunks:
                current += "\n\n" + section
            else:
                if current:
                    raw_chunks.append(current)
                current = section
        if current:
            if raw_chunks and len(current.split()) < 100:
                raw_chunks[-1] += "\n\n" + current
            else:
                raw_chunks.append(current)

        path_slug = urlparse(doc.url).path.replace("/", "-").strip("-")
        title_slug = slugify(doc.title or "untitled")[:40]
        base_slug = slugify(f"{title_slug}-{path_slug}")[:60]

        chunks = []
        for i, text in enumerate(raw_chunks):
            first_line = text.lstrip("# ").split("\n")[0].strip()
            chunk_title = first_line if first_line else doc.title
            chunks.append(
                VaultChunk(
                    content=text,
                    source_url=doc.url,
                    document_type=doc.document_type,
                    date=doc.date,
                    meeting_id=doc.meeting_id,
                    title=chunk_title,
                    chunk_index=i,
                    slug=f"{base_slug}-{i}",
                    extra_metadata=dict(doc.extra_metadata),
                )
            )
        return chunks
