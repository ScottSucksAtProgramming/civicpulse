"""
VaultWriter — writes VaultChunks to disk as Markdown files with YAML frontmatter.

Vault path convention: vault/{document_type}/{year}/{slug}-chunk-{index}.md
Year is derived from VaultChunk.date (defaults to "undated" if None).
Creates intermediate directories as needed.

Interface:
    writer = VaultWriter(vault_path=Path("./vault"))
    file_path: Path = writer.write(chunk)
"""
from pathlib import Path
from civicpulse.scraper.models import VaultChunk


class VaultWriter:
    """Writes VaultChunks as .md files with YAML frontmatter."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path

    def write(self, chunk: VaultChunk) -> Path:
        """Write chunk to vault and return the path of the written file."""
        raise NotImplementedError
