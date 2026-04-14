import os
from pathlib import Path

import click
from dotenv import load_dotenv

from civicpulse.scraper.chunker import Chunker
from civicpulse.scraper.importers.ecode360 import ECodeImporter, SectionChunker
from civicpulse.scraper.indexer import FTSIndexer
from civicpulse.scraper.sources.agenda_center import AgendaCenterScraper
from civicpulse.scraper.sources.babylon_website import BabylonWebsiteScraper
from civicpulse.scraper.sources.ecode_api import ECodeScraper
from civicpulse.scraper.sources.youtube import YouTubeScraper
from civicpulse.scraper.writer import VaultWriter

load_dotenv()

IMPORT_SOURCES = ("ecode360", "ecode360-api")


@click.command()
@click.option("--vault", default=os.getenv("VAULT_PATH", "./vault"), show_default=True)
def scrape(vault: str) -> None:
    """Scrape all Town of Babylon sources and populate the knowledge vault."""
    vault_path = Path(vault)
    chunker = Chunker()
    writer = VaultWriter(vault_path)
    total_pages, total_chunks = 0, 0

    try:
        youtube_scraper = YouTubeScraper(vault_path=vault_path)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    for ScraperClass in (BabylonWebsiteScraper, AgendaCenterScraper):
        docs = ScraperClass().scrape_all()
        total_pages += len(docs)
        for doc in docs:
            for chunk in chunker.chunk(doc):
                writer.write(chunk)
                total_chunks += 1

    total_chunks += youtube_scraper.scrape_all()

    click.echo(f"Done. {total_pages} pages scraped → {total_chunks} chunks indexed.")


@click.command()
@click.argument("query_string")
@click.option("--top-n", default=10, show_default=True)
@click.option("--type", "doc_type", default=None, help="Filter by document_type.")
@click.option("--vault", default=os.getenv("VAULT_PATH", "./vault"), show_default=True)
def query(query_string: str, top_n: int, doc_type: str | None, vault: str) -> None:
    """Query the knowledge vault FTS index."""
    load_dotenv()
    filters = {"document_type": doc_type} if doc_type else None
    results = FTSIndexer(Path(vault)).query(query_string, filters=filters, top_n=top_n)
    if not results:
        click.echo("No results found.")
        return
    for i, r in enumerate(results, 1):
        click.echo(f"\n[{i}] {r.title}  (score: {r.score:.4f})")
        click.echo(f"    Type: {r.document_type}  |  Date: {r.date or 'n/a'}")
        click.echo(f"    URL:  {r.source_url}")
        click.echo(f"    {r.content_preview}…")


@click.command(name="import")
@click.option(
    "--source",
    "source_name",
    type=click.Choice(IMPORT_SOURCES, case_sensitive=False),
    required=True,
    help="Import source to run.",
)
@click.option("--path", "source_path", type=click.Path(path_type=Path), required=True)
def import_documents(source_name: str, source_path: Path) -> None:
    """Import local document sources into the knowledge vault."""
    vault_path = Path(os.getenv("VAULT_PATH", "./vault"))

    if source_name == "ecode360":
        imported = ECodeImporter(vault_path=vault_path).import_path(source_path)
        click.echo(f"Imported {imported} ordinance chunks from {source_path}.")
        return

    if source_name == "ecode360-api":
        try:
            docs = ECodeScraper().scrape_all()
        except RuntimeError as exc:
            raise click.ClickException(str(exc)) from exc

        writer = VaultWriter(vault_path)
        chunker = SectionChunker()
        imported = 0
        for doc in docs:
            for chunk in chunker.chunk(markdown=doc.content, title=doc.title, source_url=doc.url):
                writer.write(chunk)
                imported += 1
        FTSIndexer(vault_path).index()
        click.echo(f"Imported {imported} ordinance chunks from eCode360 API.")
        return

    click.echo(f"Import source '{source_name}' at {source_path} not yet implemented.")
