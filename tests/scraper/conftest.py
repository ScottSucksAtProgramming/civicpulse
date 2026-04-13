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
