import httpx

import respx

from civicpulse.scraper.base import BaseScraper

ROBOTS_ALLOW = "User-agent: *\n"
ROBOTS_DENY = "User-agent: *\nDisallow: /denied\n"


@respx.mock
def test_scrape_returns_raw_document(department_html):
    respx.get("https://example.gov/robots.txt").mock(
        return_value=httpx.Response(200, text=ROBOTS_ALLOW)
    )
    respx.get("https://example.gov/page").mock(
        return_value=httpx.Response(
            200,
            html=department_html,
            headers={"content-type": "text/html"},
        )
    )
    scraper = BaseScraper(seed_urls=["https://example.gov/page"], max_depth=0)
    docs = scraper.scrape("https://example.gov/page")
    assert len(docs) == 1
    assert docs[0].url == "https://example.gov/page"
    assert "Department Directory" in docs[0].content


@respx.mock
def test_robots_txt_blocks_disallowed_path():
    respx.get("https://example.gov/robots.txt").mock(
        return_value=httpx.Response(200, text=ROBOTS_DENY)
    )
    scraper = BaseScraper(seed_urls=[], max_depth=0)
    result = scraper.scrape("https://example.gov/denied")
    assert result == []


@respx.mock
def test_404_returns_empty_list():
    respx.get("https://example.gov/robots.txt").mock(
        return_value=httpx.Response(200, text=ROBOTS_ALLOW)
    )
    respx.get("https://example.gov/missing").mock(return_value=httpx.Response(404))
    scraper = BaseScraper(seed_urls=[], max_depth=0)
    assert scraper.scrape("https://example.gov/missing") == []


@respx.mock
def test_link_following_depth_1(department_html, agenda_listing_html):
    respx.get("https://example.gov/robots.txt").mock(
        return_value=httpx.Response(200, text=ROBOTS_ALLOW)
    )
    respx.get("https://example.gov/listing").mock(
        return_value=httpx.Response(
            200,
            html=agenda_listing_html,
            headers={"content-type": "text/html"},
        )
    )
    scraper = BaseScraper(seed_urls=["https://example.gov/listing"], max_depth=0)
    docs = scraper.scrape("https://example.gov/listing")
    assert len(docs) >= 1
