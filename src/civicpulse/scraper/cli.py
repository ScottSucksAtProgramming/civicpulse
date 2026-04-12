"""
CLI entry points for the CivicPulse scraper pipeline.

Commands:
    civicpulse-scrape   Run all scrapers and populate the vault
    civicpulse-query    Query the vault FTS index from the command line

Note: civicpulse-query will migrate to the backend package in Phase 2 once
the retrieval API is built.
"""
import click


@click.group()
def scrape() -> None:
    """Run CivicPulse scrapers to populate the knowledge vault."""
    pass


@click.command()
@click.argument("query")
@click.option("--top-n", default=10, help="Number of results to return.")
@click.option("--type", "doc_type", default=None, help="Filter by document_type.")
def query(query: str, top_n: int, doc_type: str | None) -> None:
    """Query the knowledge vault FTS index."""
    raise NotImplementedError
