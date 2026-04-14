from click.testing import CliRunner

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
