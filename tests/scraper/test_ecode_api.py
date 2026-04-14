from civicpulse.scraper.sources.ecode_api import DEFAULT_CUSTOMER, ECodeScraper


class StubECodeClient:
    def get_structure(self, guid: str):
        if guid == "ROOT":
            return {
                "children": [
                    {
                        "guid": "chapter-213",
                        "title": "Chapter 213 Zoning",
                        "node_type": "chapter",
                    }
                ]
            }
        if guid == "chapter-213":
            return {
                "children": [
                    {
                        "guid": "section-213-166",
                        "title": "Fences",
                        "node_type": "section",
                        "section_number": "213-166",
                    }
                ]
            }
        raise AssertionError(f"unexpected guid {guid}")

    def get_content(self, guid: str):
        assert guid == "section-213-166"
        return "Fences in residential districts shall not exceed six feet."


def test_ecode_scraper_returns_ordinance_raw_documents():
    scraper = ECodeScraper(api_client=StubECodeClient(), api_key="key", api_secret="secret")

    docs = scraper.scrape_all()

    assert len(docs) == 1
    assert docs[0].document_type == "ordinance"
    assert docs[0].extra_metadata["section_number"] == "213-166"
    assert docs[0].content.startswith("§ 213-166.")


def test_ecode_scraper_respects_customer_override():
    scraper = ECodeScraper(
        api_client=StubECodeClient(),
        api_key="key",
        api_secret="secret",
        customer="TEST123",
    )

    docs = scraper.scrape_all()

    assert docs[0].url == "https://ecode360.com/TEST123#213-166"


def test_ecode_scraper_uses_default_customer():
    scraper = ECodeScraper(api_client=StubECodeClient(), api_key="key", api_secret="secret")

    docs = scraper.scrape_all()

    assert docs[0].url == f"https://ecode360.com/{DEFAULT_CUSTOMER}#213-166"
