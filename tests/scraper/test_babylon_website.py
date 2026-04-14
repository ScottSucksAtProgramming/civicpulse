import httpx
import respx

from civicpulse.scraper.sources.babylon_website import BabylonWebsiteScraper

ROBOTS_ALLOW = "User-agent: *\n"
FORMS_URL = "https://www.townofbabylonny.gov/243/Forms-Documents"
PLANNING_URL = "https://www.townofbabylonny.gov/147/Planning-Development"


def test_forms_seed_uses_depth_two_and_other_seeds_remain_at_default():
    scraper = BabylonWebsiteScraper(seed_urls=[FORMS_URL, PLANNING_URL])

    assert scraper._max_depth_for_url(FORMS_URL) == 2
    assert scraper._max_depth_for_url(PLANNING_URL) == 1


@respx.mock
def test_forms_seed_follows_pdf_links_from_child_pages(pdf_with_body_date):
    respx.get("https://www.townofbabylonny.gov/robots.txt").mock(
        return_value=httpx.Response(200, text=ROBOTS_ALLOW)
    )
    respx.get(FORMS_URL).mock(
        return_value=httpx.Response(
            200,
            html=(
                '<html><body><a href="/243/Dog-License">Dog License</a></body></html>'
            ),
            headers={"content-type": "text/html"},
        )
    )
    respx.get("https://www.townofbabylonny.gov/243/Dog-License").mock(
        return_value=httpx.Response(
            200,
            html=(
                '<html><body><a href="/DocumentCenter/View/999/dog-license.pdf">'
                "Download PDF</a></body></html>"
            ),
            headers={"content-type": "text/html"},
        )
    )
    respx.get("https://www.townofbabylonny.gov/DocumentCenter/View/999/dog-license.pdf").mock(
        return_value=httpx.Response(
            200,
            content=pdf_with_body_date,
            headers={"content-type": "application/pdf"},
        )
    )

    scraper = BabylonWebsiteScraper(seed_urls=[FORMS_URL])
    docs = scraper.scrape_all()

    assert any(doc.url.endswith("dog-license.pdf") for doc in docs)
    assert all(doc.document_type == "clerk-form" for doc in docs)
