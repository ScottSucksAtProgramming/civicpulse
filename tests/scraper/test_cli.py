import sqlite3

from click.testing import CliRunner

from civicpulse.backend.api.loggers import ScraperLogger
from civicpulse.scraper.cli import import_documents, scrape


def test_import_help_lists_available_sources():
    result = CliRunner().invoke(import_documents, ["--help"])

    assert result.exit_code == 0
    assert "--source" in result.output
    assert "ecode360" in result.output
    assert "ecode360-api" in result.output


def test_import_runs_for_ecode360_source(tmp_path, monkeypatch):
    class StubImporter:
        def __init__(self, vault_path):
            self.vault_path = vault_path

        def import_path(self, source_path):
            assert source_path == tmp_path
            return 3

    monkeypatch.setattr("civicpulse.scraper.cli.ECodeImporter", StubImporter)

    result = CliRunner().invoke(
        import_documents,
        ["--source", "ecode360", "--path", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Imported 3 ordinance chunks" in result.output


def test_import_requires_credentials_for_ecode360_api_source(tmp_path):
    result = CliRunner().invoke(
        import_documents,
        ["--source", "ecode360-api", "--path", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert "API key not configured" in result.output


def test_scrape_requires_youtube_api_key_at_startup(monkeypatch, tmp_path):
    monkeypatch.delenv("CIVICPULSE_YOUTUBE_API_KEY", raising=False)

    result = CliRunner().invoke(scrape, ["--vault", str(tmp_path / "vault")])

    assert result.exit_code != 0
    assert "CIVICPULSE_YOUTUBE_API_KEY is not configured" in result.output


def read_scraper_log_rows(vault_path):
    con = sqlite3.connect(vault_path / ".index.db")
    con.row_factory = sqlite3.Row
    try:
        return list(
            con.execute(
                """
                SELECT source_name, url, error_type, timestamp
                FROM scraper_log
                ORDER BY id
                """
            )
        )
    finally:
        con.close()


def test_scraper_logger_records_success_with_null_error_type(tmp_path):
    logger = ScraperLogger(tmp_path / ".index.db")
    logger.ensure_table()

    logger.log_run(
        source_name="BabylonWebsiteScraper",
        url="https://www.townofbabylonny.gov/",
        error_type=None,
    )

    rows = read_scraper_log_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["source_name"] == "BabylonWebsiteScraper"
    assert rows[0]["url"] == "https://www.townofbabylonny.gov/"
    assert rows[0]["error_type"] is None
    assert rows[0]["timestamp"]


def test_scraper_logger_records_failure_exception_class_name(tmp_path):
    logger = ScraperLogger(tmp_path / ".index.db")
    logger.ensure_table()

    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        logger.log_run(
            source_name="AgendaCenterScraper",
            url=None,
            error_type=type(exc).__name__,
        )

    rows = read_scraper_log_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["source_name"] == "AgendaCenterScraper"
    assert rows[0]["url"] is None
    assert rows[0]["error_type"] == "RuntimeError"


def test_scrape_logs_success_for_each_cli_scraper_run(monkeypatch, tmp_path):
    class StubPageScraper:
        seed_urls = ["https://example.gov/pages"]

        def scrape_all(self):
            return []

    class StubAgendaScraper:
        seed_urls = ["https://example.gov/agendas"]

        def scrape_all(self):
            return []

    class StubYouTubeScraper:
        seed_urls = ["https://example.gov/videos"]

        def __init__(self, vault_path):
            self.vault_path = vault_path

        def scrape_all(self):
            return 0

    monkeypatch.setattr("civicpulse.scraper.cli.BabylonWebsiteScraper", StubPageScraper)
    monkeypatch.setattr("civicpulse.scraper.cli.AgendaCenterScraper", StubAgendaScraper)
    monkeypatch.setattr("civicpulse.scraper.cli.YouTubeScraper", StubYouTubeScraper)

    vault_path = tmp_path / "vault"
    result = CliRunner().invoke(scrape, ["--vault", str(vault_path)])

    assert result.exit_code == 0
    rows = read_scraper_log_rows(vault_path)
    assert [(row["source_name"], row["error_type"]) for row in rows] == [
        ("StubPageScraper", None),
        ("StubAgendaScraper", None),
        ("StubYouTubeScraper", None),
    ]


def test_scrape_logs_failure_continues_other_sources_and_reraises(monkeypatch, tmp_path):
    class FailingScraper:
        seed_urls = ["https://example.gov/failing"]

        def scrape_all(self):
            raise ValueError("bad scrape")

    class SuccessfulScraper:
        seed_urls = ["https://example.gov/ok"]

        def scrape_all(self):
            return []

    class StubYouTubeScraper:
        def __init__(self, vault_path):
            self.vault_path = vault_path

        def scrape_all(self):
            return 0

    monkeypatch.setattr("civicpulse.scraper.cli.BabylonWebsiteScraper", FailingScraper)
    monkeypatch.setattr("civicpulse.scraper.cli.AgendaCenterScraper", SuccessfulScraper)
    monkeypatch.setattr("civicpulse.scraper.cli.YouTubeScraper", StubYouTubeScraper)

    vault_path = tmp_path / "vault"
    result = CliRunner().invoke(scrape, ["--vault", str(vault_path)])

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    rows = read_scraper_log_rows(vault_path)
    assert [(row["source_name"], row["error_type"]) for row in rows] == [
        ("FailingScraper", "ValueError"),
        ("SuccessfulScraper", None),
        ("StubYouTubeScraper", None),
    ]
