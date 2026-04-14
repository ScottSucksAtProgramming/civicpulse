from pathlib import Path

import frontmatter

from civicpulse.scraper.models import VaultChunk


class VaultWriter:
    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path

    def write(self, chunk: VaultChunk) -> Path:
        year = chunk.date[:4] if chunk.date else "undated"
        dir_path = self.vault_path / chunk.document_type / year
        dir_path.mkdir(parents=True, exist_ok=True)
        filename = f"{chunk.slug}-chunk-{chunk.chunk_index}.md"
        file_path = dir_path / filename

        metadata = {
            "source_url": chunk.source_url,
            "document_type": chunk.document_type,
            "date": chunk.date,
            "meeting_id": chunk.meeting_id,
            "title": chunk.title,
            "chunk_index": chunk.chunk_index,
        }
        metadata.update(
            {
                key: value
                for key, value in chunk.extra_metadata.items()
                if value is not None
            }
        )
        post = frontmatter.Post(chunk.content, **metadata)
        tmp = file_path.with_suffix(".tmp")
        tmp.write_text(frontmatter.dumps(post), encoding="utf-8")
        tmp.rename(file_path)
        return file_path
