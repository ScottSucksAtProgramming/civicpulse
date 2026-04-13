import re
from dataclasses import replace
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from civicpulse.scraper.base import BaseScraper
from civicpulse.scraper.models import RawDocument

SEED_URLS = [
    "https://www.townofbabylonny.gov/AgendaCenter",
    "https://www.townofbabylonny.gov/AgendaCenter/Town-Board-4",
]


class AgendaCenterScraper(BaseScraper):
    def __init__(self, seed_urls: list[str] | None = None, **kwargs):
        super().__init__(seed_urls=seed_urls if seed_urls is not None else SEED_URLS, **kwargs)

    def _infer_document_type(self, url: str) -> str:
        u = url.lower()
        if "minutes" in u:
            return "meeting-minutes"
        return "agenda"

    def _extract_html(self, html: str, url: str) -> RawDocument:
        doc = super()._extract_html(html, url)
        path_parts = [p for p in urlparse(url).path.split("/") if p]
        meeting_id = None
        for part in reversed(path_parts):
            if re.search(r"\d", part):
                meeting_id = part.lstrip("_")
                break
        date = self._parse_date(doc.title)
        if not date:
            soup = BeautifulSoup(html, "lxml")
            for tag in soup.find_all(["h1", "h2", "h3"]):
                date = self._parse_date(tag.get_text())
                if date:
                    break
        return RawDocument(
            url=doc.url,
            content=doc.content,
            title=doc.title,
            document_type=doc.document_type,
            date=date,
            meeting_id=meeting_id,
        )

    def _extract_pdf(self, body_bytes: bytes, url: str) -> RawDocument | None:
        doc = super()._extract_pdf(body_bytes, url)
        if doc is None:
            return None
        date = self._date_from_url(url)
        if date:
            return replace(doc, date=date)
        date = self._parse_date(doc.content)
        if date:
            return replace(doc, date=date)
        self._logger.warning("No date found for PDF: %s", url)
        return doc

    @staticmethod
    def _date_from_url(url: str) -> str | None:
        match = re.search(r"(?:^|/)(\d{8})(?:$|/)", urlparse(url).path)
        if not match:
            return None
        try:
            return datetime.strptime(match.group(1), "%m%d%Y").strftime("%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _parse_date(text: str) -> str | None:
        patterns = [
            ("%B %d, %Y", r"\b\w+ \d{1,2}, \d{4}\b"),
            ("%m/%d/%Y", r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
        ]
        for fmt, pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return datetime.strptime(match.group(), fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return None
