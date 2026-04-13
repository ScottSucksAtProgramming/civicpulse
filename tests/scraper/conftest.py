from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def department_html() -> str:
    return (FIXTURES_DIR / "department_page.html").read_text()


@pytest.fixture
def minutes_html() -> str:
    return (FIXTURES_DIR / "meeting_minutes.html").read_text()


@pytest.fixture
def agenda_listing_html() -> str:
    return (FIXTURES_DIR / "agenda_listing.html").read_text()


@pytest.fixture
def pdf_with_body_date() -> bytes:
    return (FIXTURES_DIR / "body_date.pdf").read_bytes()


@pytest.fixture
def pdf_without_date() -> bytes:
    return (FIXTURES_DIR / "body_no_date.pdf").read_bytes()


@pytest.fixture
def pdf_with_conflicting_date() -> bytes:
    return (FIXTURES_DIR / "body_conflicting_date.pdf").read_bytes()
