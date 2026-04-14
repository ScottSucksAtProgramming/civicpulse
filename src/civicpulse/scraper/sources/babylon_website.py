from civicpulse.scraper.base import BaseScraper

SEED_URLS = [
    "https://www.townofbabylonny.gov/459/Upcoming-Public-Meetings",
    "https://www.townofbabylonny.gov/123/Planning-Board",
    "https://www.townofbabylonny.gov/115/Town-Council",
    "https://www.townofbabylonny.gov/8/Departments",
    "https://www.townofbabylonny.gov/147/Planning-Development",
    "https://www.townofbabylonny.gov/152/Town-Clerks-Office",
    "https://www.townofbabylonny.gov/243/Forms-Documents",
    "https://www.townofbabylonny.gov/392/Freedom-of-Information-Law",
]


class BabylonWebsiteScraper(BaseScraper):
    def __init__(self, seed_urls: list[str] | None = None, **kwargs):
        super().__init__(seed_urls=seed_urls if seed_urls is not None else SEED_URLS, **kwargs)

    def scrape_all(self) -> list:
        docs = []
        for url in self.seed_urls:
            child_scraper = self.__class__(
                seed_urls=[url],
                max_depth=self._max_depth_for_url(url),
                delay=self.delay,
                user_agent=self.user_agent,
            )
            child_scraper._visited = self._visited
            child_scraper._robots = self._robots
            child_scraper._client = self._client
            docs.extend(child_scraper.scrape(url))
        return docs

    @staticmethod
    def _max_depth_for_url(url: str) -> int:
        if "/243/" in url:
            return 2
        return 1

    def _infer_document_type(self, url: str) -> str:
        u = url.lower()
        if "upcoming-public-meetings" in u or "/459/" in u:
            return "public-meeting"
        if "planning-board" in u or "/123/" in u:
            return "planning"
        if "town-council" in u or "/115/" in u:
            return "council"
        if "departments" in u or "/8/" in u:
            return "department-page"
        if "planning-development" in u or "/147/" in u:
            return "planning"
        if "town-clerk" in u or "/152/" in u:
            return "clerk"
        if "documentcenter/view" in u:
            return "clerk-form"
        if "forms-documents" in u or "forms-publications" in u or "/243/" in u:
            return "clerk-form"
        if "freedom-of-information" in u or "/392/" in u:
            return "foil"
        return "service-page"
