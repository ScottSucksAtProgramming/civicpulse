# Plan: CivicPulse Phase 1 — Project Scaffold

## Context

CivicPulse is a civic engagement AI agent for Town of Babylon, NY. The project is documentation-complete but has zero code. This plan covers the first task: establishing a clean, reproducible Python project scaffold that all subsequent Phase 1 work (scraper, vault, FTS index) will build on.

**Working directory:** `/Users/scottkostolni/programming_projects/civicpulse/` — all paths below are relative to this root.

**Current state:**
- Python 3.13.9 and 3.14.4 available; `uv` 0.9.16 installed
- `.gitignore` already configured (handles `.venv/`, `vault/`, `*.db`, `.env`, `__pycache__`)
- No `pyproject.toml`, no source directories, no packages exist

---

## Directory Structure to Create

```
civicpulse/
  .python-version
  .env.example
  pyproject.toml

  src/
    civicpulse/
      __init__.py
      scraper/
        __init__.py
        models.py          ← RawDocument, VaultChunk, Result dataclasses
        base.py            ← BaseScraper stub
        cleaner.py         ← ContentCleaner stub
        chunker.py         ← Chunker stub
        writer.py          ← VaultWriter stub
        indexer.py         ← FTSIndexer stub
        cli.py             ← Click CLI entry points stub
        SCRAPING_NOTES.md  ← robots.txt findings (empty template)
      backend/
        __init__.py
        api/
          __init__.py
        retrieval/
          __init__.py

  tests/
    conftest.py            ← empty, enables pytest fixture discovery
    scraper/
      __init__.py
    backend/
      __init__.py

  vault/
    .gitkeep

  frontend/
    .gitkeep
```

---

## Files to Create

### `.python-version`
```
3.13.9
```

### `.env.example`
```
ANTHROPIC_API_KEY=your_key_here
SCRAPER_DELAY_SECONDS=1.0
SCRAPER_USER_AGENT=CivicPulse/0.1 (civic research)
VAULT_PATH=./vault
```

### `pyproject.toml`
Provide this file **verbatim**:

```toml
[project]
name = "civicpulse"
version = "0.1.0"
description = "Civic engagement AI agent for Town of Babylon, NY"
requires-python = ">=3.13"
dependencies = [
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "sqlite-utils>=3.37",
    "python-frontmatter>=1.1",
    "pyyaml>=6.0",
    "click>=8.1",
    "python-slugify>=8.0",
    "python-dotenv>=1.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "respx>=0.21",
    "ruff>=0.8",
    "mypy>=1.13",
    "types-pyyaml",
    "types-beautifulsoup4",
]

[project.scripts]
civicpulse-scrape = "civicpulse.scraper.cli:scrape"
civicpulse-query = "civicpulse.scraper.cli:query"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/civicpulse"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I"]
```

### `src/civicpulse/scraper/models.py`
Define all shared dataclasses. These are the data transfer objects that flow through the pipeline:

```python
"""
Shared data models for the CivicPulse scraper pipeline.

Pipeline flow: RawDocument → VaultChunk → (written to disk) → Result (from FTS query)
"""
from dataclasses import dataclass


@dataclass
class RawDocument:
    """A scraped page before cleaning or chunking."""
    url: str               # canonical URL of the scraped page
    html: str              # raw HTML response body
    title: str             # page/document title (extracted from <title> or <h1>)
    document_type: str     # e.g. "meeting-minutes", "agenda", "service-page"
    date: str | None       # ISO 8601 date if parseable, else None
    meeting_id: str | None # meeting identifier for agenda/minutes docs, else None


@dataclass
class VaultChunk:
    """A single vault-ready content chunk ready to be written as a .md file."""
    content: str           # cleaned Markdown text of this chunk
    source_url: str        # canonical URL this chunk came from
    document_type: str     # mirrors RawDocument.document_type
    date: str | None       # ISO 8601 date, may be None
    meeting_id: str | None # meeting identifier, may be None
    title: str             # section heading or document title for this chunk
    chunk_index: int       # zero-based position within the source document
    slug: str              # generated filename slug (used in vault path)


@dataclass
class Result:
    """A single FTS search result returned by FTSIndexer.query()."""
    file_path: str         # absolute path to the vault .md file
    source_url: str        # original source URL
    document_type: str
    date: str | None
    meeting_id: str | None
    title: str
    chunk_index: int
    score: float           # BM25 relevance score (higher = more relevant)
    content_preview: str   # first ~200 characters of the chunk content
```

### `src/civicpulse/scraper/base.py`
```python
"""
BaseScraper — shared HTTP fetch, robots.txt enforcement, rate limiting, and retry logic.

All source-specific scrapers (e.g. BabylonWebsiteScraper, AgendaCenterScraper) inherit
from BaseScraper and implement scrape() by calling self._fetch() for each URL.

Interface:
    scraper = BaseScraper(config)
    documents: list[RawDocument] = scraper.scrape(url)
"""
from civicpulse.scraper.models import RawDocument


class BaseScraper:
    """Base class for all CivicPulse scrapers."""

    def scrape(self, url: str) -> list[RawDocument]:
        """Fetch a URL and return one or more RawDocuments.

        Handles robots.txt checking, rate limiting, and retries internally.
        Raises no exceptions on 404/timeout — logs and returns empty list instead.
        """
        raise NotImplementedError
```

### `src/civicpulse/scraper/cleaner.py`
```python
"""
ContentCleaner — strips HTML boilerplate and extracts main content as plain text.

Removes <nav>, <header>, <footer>, <script>, <style> elements.
Extracts the main content area and converts to clean plain text.

Interface:
    cleaner = ContentCleaner()
    text: str = cleaner.clean(html)
"""


class ContentCleaner:
    """Strips navigation, headers, footers, and scripts from raw HTML."""

    def clean(self, html: str) -> str:
        """Return clean plain text extracted from the main content area of html."""
        raise NotImplementedError
```

### `src/civicpulse/scraper/chunker.py`
```python
"""
Chunker — splits a RawDocument into VaultChunks on section boundaries.

Splits on <h2>, <h3>, and double-newline paragraph boundaries.
Minimum chunk size: ~100 words. Orphaned short chunks are merged with
the preceding chunk. Assembles YAML frontmatter fields from RawDocument metadata.

Interface:
    chunker = Chunker()
    chunks: list[VaultChunk] = chunker.chunk(doc)
"""
from civicpulse.scraper.models import RawDocument, VaultChunk


class Chunker:
    """Segments a RawDocument into section-aligned VaultChunks."""

    def chunk(self, doc: RawDocument) -> list[VaultChunk]:
        """Split doc into section-aligned VaultChunks with populated frontmatter."""
        raise NotImplementedError
```

### `src/civicpulse/scraper/writer.py`
```python
"""
VaultWriter — writes VaultChunks to disk as Markdown files with YAML frontmatter.

Vault path convention: vault/{document_type}/{year}/{slug}-chunk-{index}.md
Year is derived from VaultChunk.date (defaults to "undated" if None).
Creates intermediate directories as needed.

Interface:
    writer = VaultWriter(vault_path=Path("./vault"))
    file_path: Path = writer.write(chunk)
"""
from pathlib import Path
from civicpulse.scraper.models import VaultChunk


class VaultWriter:
    """Writes VaultChunks as .md files with YAML frontmatter."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path

    def write(self, chunk: VaultChunk) -> Path:
        """Write chunk to vault and return the path of the written file."""
        raise NotImplementedError
```

### `src/civicpulse/scraper/indexer.py`
```python
"""
FTSIndexer — builds and queries a SQLite FTS5 full-text search index over the vault.

Index schema: fts_index(title, content, source_url, document_type, date,
                        meeting_id, chunk_index, file_path)
Index location: vault/.index.db (gitignored)
Incremental updates: tracks file modification times; only re-indexes changed files.

Interface:
    indexer = FTSIndexer(vault_path=Path("./vault"))
    indexer.index()                                          # build/update index
    results: list[Result] = indexer.query("zoning variance", filters={"document_type": "ordinance"})
"""
from pathlib import Path
from civicpulse.scraper.models import Result


class FTSIndexer:
    """Builds and queries a SQLite FTS5 index over the knowledge vault."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path

    def index(self) -> None:
        """Build or incrementally update the FTS5 index from vault contents."""
        raise NotImplementedError

    def query(self, q: str, filters: dict | None = None, top_n: int = 10) -> list[Result]:
        """Return top_n BM25-ranked Results matching q, optionally filtered by metadata."""
        raise NotImplementedError
```

### `src/civicpulse/scraper/cli.py`
```python
"""
CLI entry points for the CivicPulse scraper pipeline.

Commands:
    civicpulse-scrape   Run all scrapers and populate the vault
    civicpulse-query    Query the vault FTS index from the command line

Note: civicpulse-query will migrate to the backend package in Phase 2 once
the retrieval API is built.
"""
import click


@click.group()
def scrape() -> None:
    """Run CivicPulse scrapers to populate the knowledge vault."""
    pass


@click.command()
@click.argument("query")
@click.option("--top-n", default=10, help="Number of results to return.")
@click.option("--type", "doc_type", default=None, help="Filter by document_type.")
def query(query: str, top_n: int, doc_type: str | None) -> None:
    """Query the knowledge vault FTS index."""
    raise NotImplementedError
```

### `src/civicpulse/scraper/SCRAPING_NOTES.md`
```markdown
# Scraping Notes — townofbabylonny.gov

## robots.txt Review

- [ ] Review date: _TBD_
- [ ] robots.txt URL: https://www.townofbabylonny.gov/robots.txt
- [ ] Disallowed paths: _document findings here_
- [ ] Crawl-delay directive: _document if present_

## Rate Limiting Policy

- Default delay between requests: 1.0 second (configurable via SCRAPER_DELAY_SECONDS)
- User agent: CivicPulse/0.1 (civic research)

## Notes

_Add scraping observations, access issues, and URL structure notes here._
```

### `tests/conftest.py`
```python
# conftest.py — enables pytest fixture discovery across all test directories.
# Add shared fixtures here as the test suite grows.
```

### All `__init__.py` files
All `__init__.py` files should be **empty** (zero bytes). Do not add re-exports or imports.

### `vault/.gitkeep` and `frontend/.gitkeep`
Empty files. The `.gitignore` already ignores `vault/` — add a `!vault/.gitkeep` exception line to `.gitignore` so the directory placeholder is tracked by git.

---

## `.gitignore` Amendment Required

Add this line to `.gitignore` after the `vault/` entry:
```
!vault/.gitkeep
```

---

## `CLAUDE.md` Tree Update Required

Per project rules, update the Tree section in `CLAUDE.md` to reflect the new directories:
```
civicpulse/
  CLAUDE.md
  INDEX.md
  .taskpaper
  todo.taskpaper
  .gitignore
  .python-version
  .env.example
  pyproject.toml
  src/
    civicpulse/
      scraper/
      backend/
  tests/
  vault/
  frontend/
  docs/
  plans/
  context/
```

---

## Implementation Steps (in order)

1. Create `.python-version`
2. Create `pyproject.toml` (verbatim as above)
3. Create `.env.example`
4. Create all directories: `src/civicpulse/scraper/`, `src/civicpulse/backend/api/`, `src/civicpulse/backend/retrieval/`, `tests/scraper/`, `tests/backend/`, `vault/`, `frontend/`
5. Create all empty `__init__.py` files (9 total — see directory tree)
6. Create `src/civicpulse/scraper/models.py` (verbatim as above)
7. Create `src/civicpulse/scraper/base.py`, `cleaner.py`, `chunker.py`, `writer.py`, `indexer.py`, `cli.py` (verbatim as above)
8. Create `src/civicpulse/scraper/SCRAPING_NOTES.md`
9. Create `tests/conftest.py`
10. Create `vault/.gitkeep` and `frontend/.gitkeep`
11. Amend `.gitignore` to add `!vault/.gitkeep`
12. Update `CLAUDE.md` Tree section
13. Run `uv sync` to create `.venv` and `uv.lock`

---

## Verification

Run these commands from the `civicpulse/` working directory to confirm the scaffold is correct:

```bash
# Python version locked correctly
uv run python --version
# Expected: Python 3.13.x

# All Phase 1 runtime imports resolve
uv run python -c "import httpx, bs4, sqlite_utils, frontmatter, yaml, click, slugify, dotenv"
# Expected: no output (no errors)

# Package is importable
uv run python -c "from civicpulse.scraper.models import RawDocument, VaultChunk, Result; print('models ok')"
# Expected: models ok

# CLI entry points are registered and respond to --help
uv run civicpulse-scrape --help
uv run civicpulse-query --help
# Expected: Click help output for each command

# Pytest discovers tests without errors (0 tests collected is fine)
uv run pytest --collect-only
# Expected: collected 0 items (or similar), no errors

# Vault gitkeep is tracked
git status vault/.gitkeep
# Expected: shows as new/tracked file, not ignored
```

---

## Files Created / Modified

| Path | Action |
|------|--------|
| `.python-version` | Create |
| `pyproject.toml` | Create |
| `.env.example` | Create |
| `.gitignore` | Amend (add `!vault/.gitkeep`) |
| `CLAUDE.md` | Amend (update Tree section) |
| `src/civicpulse/__init__.py` | Create (empty) |
| `src/civicpulse/scraper/__init__.py` | Create (empty) |
| `src/civicpulse/scraper/models.py` | Create |
| `src/civicpulse/scraper/base.py` | Create |
| `src/civicpulse/scraper/cleaner.py` | Create |
| `src/civicpulse/scraper/chunker.py` | Create |
| `src/civicpulse/scraper/writer.py` | Create |
| `src/civicpulse/scraper/indexer.py` | Create |
| `src/civicpulse/scraper/cli.py` | Create |
| `src/civicpulse/scraper/SCRAPING_NOTES.md` | Create |
| `src/civicpulse/backend/__init__.py` | Create (empty) |
| `src/civicpulse/backend/api/__init__.py` | Create (empty) |
| `src/civicpulse/backend/retrieval/__init__.py` | Create (empty) |
| `tests/conftest.py` | Create |
| `tests/scraper/__init__.py` | Create (empty) |
| `tests/backend/__init__.py` | Create (empty) |
| `vault/.gitkeep` | Create |
| `frontend/.gitkeep` | Create |
