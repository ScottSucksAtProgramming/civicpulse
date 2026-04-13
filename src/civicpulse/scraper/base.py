import io
import logging
import os
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from civicpulse.scraper.cleaner import ContentCleaner
from civicpulse.scraper.models import RawDocument


class BaseScraper:
    def __init__(
        self,
        seed_urls: list[str],
        max_depth: int = 1,
        delay: float = float(os.getenv("SCRAPER_DELAY_SECONDS", "1.0")),
        user_agent: str = os.getenv("SCRAPER_USER_AGENT", "CivicPulse/0.1 (civic research)"),
    ) -> None:
        self.seed_urls = seed_urls
        self.max_depth = max_depth
        self.delay = delay
        self.user_agent = user_agent
        self._robots: dict[str, RobotFileParser] = {}
        self._visited: set[str] = set()
        self._cleaner = ContentCleaner()
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            follow_redirects=True,
            timeout=10.0,
        )
        self._logger = logging.getLogger(self.__class__.__name__)

    def scrape(self, url: str) -> list[RawDocument]:
        url = url.split("#")[0].rstrip("/")
        if url in self._visited:
            return []
        self._visited.add(url)
        if not self._is_allowed(url):
            self._logger.warning("Blocked by robots.txt: %s", url)
            return []
        result = self._fetch(url)
        if result is None:
            return []
        status, headers, body_bytes = result
        content_type = headers.get("content-type", "")
        if "application/pdf" in content_type or url.lower().endswith(".pdf"):
            doc = self._extract_pdf(body_bytes, url)
            return [doc] if doc else []
        html = body_bytes.decode("utf-8", errors="replace")
        doc = self._extract_html(html, url)
        docs = [doc]
        if self.max_depth > 0:
            links = self._extract_links(html, url)
            for link in links:
                child_scraper = self.__class__(
                    seed_urls=[link],
                    max_depth=self.max_depth - 1,
                    delay=self.delay,
                    user_agent=self.user_agent,
                )
                child_scraper._visited = self._visited
                child_scraper._robots = self._robots
                child_scraper._client = self._client
                time.sleep(self.delay)
                docs.extend(child_scraper.scrape(link))
        return docs

    def scrape_all(self) -> list[RawDocument]:
        docs = []
        for url in self.seed_urls:
            docs.extend(self.scrape(url))
        return docs

    def _fetch(self, url: str) -> tuple[int, dict, bytes] | None:
        attempts = 0
        backoff = [1, 2, 4]
        while attempts < 3:
            try:
                response = self._client.get(url)
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Server error: {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                if response.status_code >= 400:
                    self._logger.warning("HTTP %d: %s", response.status_code, url)
                    return None
                return (response.status_code, dict(response.headers), response.content)
            except (httpx.TimeoutException, httpx.HTTPStatusError):
                attempts += 1
                if attempts < 3:
                    time.sleep(backoff[attempts - 1])
        self._logger.warning("Failed after 3 attempts: %s", url)
        return None

    def _is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        if domain not in self._robots:
            parser = RobotFileParser()
            parser.set_url(f"{domain}/robots.txt")
            try:
                resp = self._client.get(f"{domain}/robots.txt", timeout=5.0)
                parser.parse(resp.text.splitlines())
            except Exception:
                parser.parse([])
            self._robots[domain] = parser
        return self._robots[domain].can_fetch(self.user_agent, url)

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        base_domain = urlparse(base_url).netloc
        links = []
        for tag in soup.find_all("a", href=True):
            href = urljoin(base_url, tag["href"])
            parsed = urlparse(href)
            if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
                clean = href.split("#")[0]
                if clean not in self._visited:
                    links.append(clean)
        return list(dict.fromkeys(links))

    def _extract_html(self, html: str, url: str) -> RawDocument:
        cleaned_text = self._cleaner.clean(html)
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        h1_tag = soup.find("h1")
        title = (
            title_tag.get_text(strip=True)
            if title_tag
            else h1_tag.get_text(strip=True)
            if h1_tag
            else urlparse(url).path.split("/")[-1] or url
        )
        return RawDocument(
            url=url,
            content=cleaned_text,
            title=title,
            document_type=self._infer_document_type(url),
            date=None,
            meeting_id=None,
        )

    def _extract_pdf(self, body_bytes: bytes, url: str) -> RawDocument | None:
        try:
            pages = []
            with pdfplumber.open(io.BytesIO(body_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
            if not pages:
                self._logger.warning("PDF has no extractable text: %s", url)
                return None
            content = "\n\n".join(pages)
            title = (
                urlparse(url).path.split("/")[-1].replace(".pdf", "").replace("-", " ").title()
            )
            return RawDocument(
                url=url,
                content=content,
                title=title,
                document_type=self._infer_document_type(url),
                date=None,
                meeting_id=None,
            )
        except Exception as e:
            self._logger.warning("PDF extraction failed for %s: %s", url, e)
            return None

    def _infer_document_type(self, url: str) -> str:
        return "service-page"
