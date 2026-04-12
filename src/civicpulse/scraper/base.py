"""
BaseScraper — shared HTTP fetch, robots.txt enforcement, rate limiting, and retry logic.

All source-specific scrapers (e.g. BabylonWebsiteScraper, AgendaCenterScraper) inherit
from BaseScraper and implement scrape() by calling self._fetch() for each URL.

Interface:
    scraper = BaseScraper(config)
    documents: list[RawDocument] = scraper.scrape(url)
"""
from civicpulse.scraper.models import RawDocument


class BaseScraper:
    """Base class for all CivicPulse scrapers."""

    def scrape(self, url: str) -> list[RawDocument]:
        """Fetch a URL and return one or more RawDocuments.

        Handles robots.txt checking, rate limiting, and retries internally.
        Raises no exceptions on 404/timeout — logs and returns empty list instead.
        """
        raise NotImplementedError
