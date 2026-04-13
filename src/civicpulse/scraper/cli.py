import os
from pathlib import Path

import click
from dotenv import load_dotenv

from civicpulse.scraper.chunker import Chunker
from civicpulse.scraper.indexer import FTSIndexer
from civicpulse.scraper.sources.agenda_center import AgendaCenterScraper
from civicpulse.scraper.sources.babylon_website import BabylonWebsiteScraper
from civicpulse.scraper.writer import VaultWriter

load_dotenv()


@click.command()
@click.option("--vault", default=os.getenv("VAULT_PATH", "./vault"), show_default=True)
def scrape(vault: str) -> None:
    """Scrape all Town of Babylon sources and populate the knowledge vault."""
    vault_path = Path(vault)
    chunker = Chunker()
    writer = VaultWriter(vault_path)
    total_pages, total_chunks = 0, 0

    for ScraperClass in (BabylonWebsiteScraper, AgendaCenterScraper):
        docs = ScraperClass().scrape_all()
        total_pages += len(docs)
        for doc in docs:
            for chunk in chunker.chunk(doc):
                writer.write(chunk)
                total_chunks += 1

    FTSIndexer(vault_path).index()
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
