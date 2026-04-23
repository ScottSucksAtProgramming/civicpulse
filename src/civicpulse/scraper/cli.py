import os
from pathlib import Path

import click
from dotenv import load_dotenv

from civicpulse.backend.api.loggers import ScraperLogger
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


def _scraper_url(scraper) -> str | None:
    seed_urls = getattr(scraper, "seed_urls", None)
    if seed_urls:
        return seed_urls[0]
    return None


def _run_logged_scraper(scraper, scraper_logger: ScraperLogger):
    source_name = scraper.__class__.__name__
    url = _scraper_url(scraper)
    try:
        result = scraper.scrape_all()
    except Exception as exc:
        scraper_logger.log_run(source_name=source_name, url=url, error_type=type(exc).__name__)
        raise
    scraper_logger.log_run(source_name=source_name, url=url, error_type=None)
    return result


@click.command()
@click.option("--vault", default=os.getenv("VAULT_PATH", "./vault"), show_default=True)
def scrape(vault: str) -> None:
    """Scrape all Town of Babylon sources and populate the knowledge vault."""
    vault_path = Path(vault)
    vault_path.mkdir(parents=True, exist_ok=True)
    scraper_logger = ScraperLogger(vault_path / ".index.db")
    scraper_logger.ensure_table()
    chunker = Chunker()
    writer = VaultWriter(vault_path)
    total_pages, total_chunks = 0, 0
    first_error: Exception | None = None

    try:
        youtube_scraper = YouTubeScraper(vault_path=vault_path)
    except RuntimeError as exc:
        scraper_logger.log_run(
            source_name="YouTubeScraper",
            url=None,
            error_type=type(exc).__name__,
        )
        raise click.ClickException(str(exc)) from exc

    for ScraperClass in (BabylonWebsiteScraper, AgendaCenterScraper):
        scraper = ScraperClass()
        try:
            docs = _run_logged_scraper(scraper, scraper_logger)
        except Exception as exc:
            if first_error is None:
                first_error = exc
            continue
        total_pages += len(docs)
        for doc in docs:
            for chunk in chunker.chunk(doc):
                writer.write(chunk)
                total_chunks += 1

    try:
        total_chunks += _run_logged_scraper(youtube_scraper, scraper_logger)
    except Exception as exc:
        if first_error is None:
            first_error = exc

    if first_error is not None:
        raise first_error

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
