import io

import pdfplumber

from civicpulse.scraper.models import RawDocument, VaultChunk
from civicpulse.scraper.sources.agenda_center import AgendaCenterScraper
from civicpulse.scraper.writer import VaultWriter


def test_date_from_url_parses_mmddyyyy_segment():
    url = "https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Minutes/03152026"
    assert AgendaCenterScraper._date_from_url(url) == "2026-03-15"


def test_date_from_url_ignores_bare_meeting_id():
    url = "https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Agenda/1234"
    assert AgendaCenterScraper._date_from_url(url) is None


def test_date_from_url_rejects_invalid_digits():
    url = "https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Minutes/99999999"
    assert AgendaCenterScraper._date_from_url(url) is None


def test_date_from_url_returns_none_without_eight_digit_segment():
    url = "https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Minutes/March-15-2026"
    assert AgendaCenterScraper._date_from_url(url) is None


def test_extract_pdf_sets_date_from_url(monkeypatch):
    scraper = AgendaCenterScraper()
    source_doc = RawDocument(
        url="https://example.gov/minutes.pdf",
        content="Meeting minutes body",
        title="minutes",
        document_type="meeting-minutes",
        date=None,
        meeting_id=None,
    )

    def fake_super_extract_pdf(self, body_bytes, url):
        return source_doc

    monkeypatch.setattr(
        "civicpulse.scraper.base.BaseScraper._extract_pdf",
        fake_super_extract_pdf,
    )

    extracted = scraper._extract_pdf(
        b"%PDF-1.4",
        "https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Minutes/03152026",
    )

    assert extracted is not None
    assert extracted.date == "2026-03-15"
    assert extracted.content == source_doc.content
    assert extracted is not source_doc


def test_pdf_fixture_is_structurally_valid(pdf_with_body_date):
    with pdfplumber.open(io.BytesIO(pdf_with_body_date)) as pdf:
        assert [page.extract_text() for page in pdf.pages] == [
            "Town Board Meeting Minutes\nMeeting Date: March 15, 2026"
        ]


def test_extract_pdf_falls_back_to_body_text(pdf_with_body_date):
    scraper = AgendaCenterScraper()
    extracted = scraper._extract_pdf(
        pdf_with_body_date,
        "https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Minutes/body-date",
    )

    assert extracted is not None
    assert extracted.date == "2026-03-15"


def test_extract_pdf_prefers_url_date_over_body_text(pdf_with_conflicting_date):
    scraper = AgendaCenterScraper()
    extracted = scraper._extract_pdf(
        pdf_with_conflicting_date,
        "https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Minutes/03152026",
    )

    assert extracted is not None
    assert extracted.date == "2026-03-15"


def test_extract_pdf_logs_warning_when_no_date_found(pdf_without_date, caplog):
    scraper = AgendaCenterScraper()

    with caplog.at_level("WARNING", logger="AgendaCenterScraper"):
        extracted = scraper._extract_pdf(
            pdf_without_date,
            "https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Minutes/no-date",
        )

    assert extracted is not None
    assert extracted.date is None
    assert caplog.records
    assert caplog.records[0].name == "AgendaCenterScraper"
    assert "no date" in caplog.records[0].message.lower()


def test_writer_uses_year_directory_for_dated_minutes_chunk(tmp_path):
    path = VaultWriter(tmp_path).write(
        chunk=VaultChunk(
            content="Body text",
            source_url="https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Minutes/03152026",
            document_type="meeting-minutes",
            date="2026-03-15",
            meeting_id=None,
            title="Town Board Meeting Minutes",
            chunk_index=0,
            slug="town-board-meeting-minutes",
        )
    )

    assert path.parts[-3:] == ("meeting-minutes", "2026", "town-board-meeting-minutes-chunk-0.md")
