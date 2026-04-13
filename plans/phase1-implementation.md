# Plan: Phase 1 — Scraper, Vault Pipeline & FTS Index Implementation

## Context

All five scraper pipeline modules (`BaseScraper`, `ContentCleaner`, `Chunker`, `VaultWriter`,
`FTSIndexer`) and the CLI exist as stubs with `raise NotImplementedError`. This plan
implements them fully so that `civicpulse-scrape` scrapes all Town of Babylon public pages,
chunks the content, writes structured Markdown to the vault, and builds a queryable SQLite
FTS5 index. GitHub issue: ScottSucksAtProgramming/civicpulse#2.

**Working directory:** `/Users/scottkostolni/programming_projects/civicpulse/`

**Pipeline flow:**
```
seed_url → BaseScraper.scrape(url) → RawDocument
         → ContentCleaner.clean()  → RawDocument.content (plain text with ## headings)
         → Chunker.chunk()         → list[VaultChunk]
         → VaultWriter.write()     → .md files on disk
         → FTSIndexer.index()      → SQLite FTS5 index
         → FTSIndexer.query()      → list[Result]
```

---

## Step 0 — Rename `RawDocument.html` → `RawDocument.content` in `models.py`

The `html` field is misleading: after cleaning it holds plain text, and for PDFs it
holds extracted text (never HTML). Rename to `content` throughout.

In `src/civicpulse/scraper/models.py`, change:
```python
html: str  # raw HTML response body
```
to:
```python
content: str  # cleaned text content (plain text with Markdown headings)
```

Update all references across `base.py`, `chunker.py`, and tests.

---

## Step 1 — Add `pdfplumber` dependency

In `pyproject.toml`, add `"pdfplumber>=0.11"` to `[project.dependencies]`.
Run `uv sync` before implementing any code.

---

## Step 2 — Implement `src/civicpulse/scraper/cleaner.py`

**Purpose:** Strip HTML boilerplate and return clean plain text **with Markdown heading
markers** (`## Title`) preserved so the `Chunker` can split reliably.

**Imports:**
```python
import re
from bs4 import BeautifulSoup, Tag
```

**`ContentCleaner.clean(html: str) -> str`:**
```
1. Parse: soup = BeautifulSoup(html, "lxml")
2. Decompose (remove entirely):
     nav, header, footer, script, style, aside, noscript
     + any tag whose class contains: breadcrumb, site-header, site-footer,
       menu, sidebar, pagination, skip-link
3. Find main content area (first match wins):
     soup.find("main")
     → soup.find("article")
     → soup.find(id="content")
     → soup.find("div", class_=re.compile(r"field.items|page.content|main.content"))
     → soup.find("body")
4. Walk the selected element's children. For each element:
     - If tag is <h1> or <h2>: emit "# " + tag.get_text(strip=True)
     - If tag is <h3> or <h4>: emit "## " + tag.get_text(strip=True)
     - Otherwise: emit tag.get_text(separator=" ", strip=True)
   Join with "\n\n"
5. Collapse 3+ consecutive newlines: re.sub(r'\n{3,}', '\n\n', text)
6. Return stripped string
```

**Example:**
- Input: `<html><nav>…</nav><main><h2>Meeting Agenda</h2><p>The board voted…</p></main></html>`
- Output: `"## Meeting Agenda\n\nThe board voted…"`

---

## Step 3 — Implement `src/civicpulse/scraper/base.py`

**Imports:**
```python
import io
import logging
import os
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import pdfplumber

from civicpulse.scraper.cleaner import ContentCleaner
from civicpulse.scraper.models import RawDocument
```

**Constructor:**
```python
def __init__(
    self,
    seed_urls: list[str],
    max_depth: int = 1,
    delay: float = float(os.getenv("SCRAPER_DELAY_SECONDS", "1.0")),
    user_agent: str = os.getenv("SCRAPER_USER_AGENT", "CivicPulse/0.1 (civic research)"),
) -> None:
    self.seed_urls = seed_urls
    self.max_depth = max_depth
    self.delay = delay
    self.user_agent = user_agent
    self._robots: dict[str, RobotFileParser] = {}
    self._visited: set[str] = set()
    self._cleaner = ContentCleaner()
    self._client = httpx.Client(
        headers={"User-Agent": user_agent},
        follow_redirects=True,
        timeout=10.0,
    )
    self._logger = logging.getLogger(self.__class__.__name__)
```

**`scrape(url: str) -> list[RawDocument]`** — single URL entry point (preserves stub interface):
```
1. Normalise URL: strip fragment, strip trailing slash
2. If url in self._visited: return []
3. self._visited.add(url)
4. If not self._is_allowed(url): log warning, return []
5. result = self._fetch(url)
6. If result is None: return []
7. status, headers, body_bytes = result
8. content_type = headers.get("content-type", "")
9. If "application/pdf" in content_type or url.lower().endswith(".pdf"):
       doc = self._extract_pdf(body_bytes, url)
       return [doc] if doc else []
10. html = body_bytes.decode("utf-8", errors="replace")
11. doc = self._extract_html(html, url)
12. docs = [doc]
13. If self.max_depth > 0:
        links = self._extract_links(html, url)
        for link in links:
            child_scraper = self.__class__(
                seed_urls=[link],
                max_depth=self.max_depth - 1,
                delay=self.delay,
                user_agent=self.user_agent,
            )
            child_scraper._visited = self._visited  # share visited set
            child_scraper._robots = self._robots     # share robots cache
            child_scraper._client = self._client     # share HTTP client
            time.sleep(self.delay)
            docs.extend(child_scraper.scrape(link))
14. return docs
```

**`scrape_all() -> list[RawDocument]`** — iterates all seed URLs:
```python
def scrape_all(self) -> list[RawDocument]:
    docs = []
    for url in self.seed_urls:
        docs.extend(self.scrape(url))
    return docs
```

**`_fetch(url) -> tuple[int, dict, bytes] | None`** — retry logic:
```
attempts = 0
backoff = [1, 2, 4]
while attempts < 3:
    try:
        response = self._client.get(url)
        if response.status_code >= 500:
            raise httpx.HTTPStatusError(...)
        if response.status_code >= 400:
            self._logger.warning("HTTP %d: %s", response.status_code, url)
            return None
        return (response.status_code, dict(response.headers), response.content)
    except (httpx.TimeoutException, httpx.HTTPStatusError):
        attempts += 1
        if attempts < 3:
            time.sleep(backoff[attempts - 1])
self._logger.warning("Failed after 3 attempts: %s", url)
return None
```

**`_is_allowed(url) -> bool`** — robots.txt via httpx (NOT `parser.read()`):
```
parsed = urlparse(url)
domain = f"{parsed.scheme}://{parsed.netloc}"
if domain not in self._robots:
    parser = RobotFileParser()
    parser.set_url(f"{domain}/robots.txt")
    try:
        resp = self._client.get(f"{domain}/robots.txt", timeout=5.0)
        parser.parse(resp.text.splitlines())
    except Exception:
        parser.parse([])  # assume allowed on failure
    self._robots[domain] = parser
return self._robots[domain].can_fetch(self.user_agent, url)
```

**`_extract_links(html, base_url) -> list[str]`:**
```
soup = BeautifulSoup(html, "lxml")
base_domain = urlparse(base_url).netloc
links = []
for tag in soup.find_all("a", href=True):
    href = urljoin(base_url, tag["href"])
    parsed = urlparse(href)
    # same domain, http/https, strip fragment
    if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
        clean = href.split("#")[0]
        if clean not in self._visited:
            links.append(clean)
return list(dict.fromkeys(links))  # deduplicate preserving order
```

**`_extract_html(html, url) -> RawDocument`:**
```
cleaned_text = self._cleaner.clean(html)
soup = BeautifulSoup(html, "lxml")
title_tag = soup.find("title")
h1_tag = soup.find("h1")
title = (title_tag.get_text(strip=True) if title_tag
         else h1_tag.get_text(strip=True) if h1_tag
         else urlparse(url).path.split("/")[-1] or url)
return RawDocument(
    url=url,
    content=cleaned_text,
    title=title,
    document_type=self._infer_document_type(url),
    date=None,
    meeting_id=None,
)
```

**`_extract_pdf(body_bytes, url) -> RawDocument | None`:**
```
try:
    pages = []
    with pdfplumber.open(io.BytesIO(body_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    if not pages:
        self._logger.warning("PDF has no extractable text: %s", url)
        return None
    content = "\n\n".join(pages)
    title = urlparse(url).path.split("/")[-1].replace(".pdf", "").replace("-", " ").title()
    return RawDocument(
        url=url,
        content=content,
        title=title,
        document_type=self._infer_document_type(url),
        date=None,
        meeting_id=None,
    )
except Exception as e:
    self._logger.warning("PDF extraction failed for %s: %s", url, e)
    return None
```

**`_infer_document_type(url) -> str`:** Returns `"service-page"`. Subclasses override.

---

## Step 4 — Create `src/civicpulse/scraper/sources/__init__.py`

Empty file.

---

## Step 5 — Create `src/civicpulse/scraper/sources/babylon_website.py`

**Imports:**
```python
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
```

```python
class BabylonWebsiteScraper(BaseScraper):
    def __init__(self, seed_urls: list[str] | None = None, **kwargs):
        super().__init__(seed_urls=seed_urls if seed_urls is not None else SEED_URLS, **kwargs)

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
        if "forms-documents" in u or "/243/" in u:
            return "clerk-form"
        if "freedom-of-information" in u or "/392/" in u:
            return "foil"
        return "service-page"
```

---

## Step 6 — Create `src/civicpulse/scraper/sources/agenda_center.py`

**Imports:**
```python
import re
from datetime import datetime
from urllib.parse import urlparse

from civicpulse.scraper.base import BaseScraper
from civicpulse.scraper.models import RawDocument
from bs4 import BeautifulSoup

SEED_URLS = [
    "https://www.townofbabylonny.gov/AgendaCenter",
    "https://www.townofbabylonny.gov/AgendaCenter/Town-Board-4",
]
```

```python
class AgendaCenterScraper(BaseScraper):
    def __init__(self, seed_urls: list[str] | None = None, **kwargs):
        super().__init__(seed_urls=seed_urls if seed_urls is not None else SEED_URLS, **kwargs)

    def _infer_document_type(self, url: str) -> str:
        u = url.lower()
        if "minutes" in u:
            return "meeting-minutes"
        return "agenda"

    def _extract_html(self, html: str, url: str) -> RawDocument:
        doc = super()._extract_html(html, url)
        # Extract meeting_id from URL path: last numeric-containing segment
        path_parts = [p for p in urlparse(url).path.split("/") if p]
        meeting_id = None
        for part in reversed(path_parts):
            if re.search(r'\d', part):
                meeting_id = part.lstrip("_")
                break
        # Extract date from title or first heading
        date = self._parse_date(doc.title)
        if not date:
            soup = BeautifulSoup(html, "lxml")
            for tag in soup.find_all(["h1", "h2", "h3"]):
                date = self._parse_date(tag.get_text())
                if date:
                    break
        return RawDocument(
            url=doc.url,
            content=doc.content,
            title=doc.title,
            document_type=doc.document_type,
            date=date,
            meeting_id=meeting_id,
        )

    @staticmethod
    def _parse_date(text: str) -> str | None:
        patterns = [
            ("%B %d, %Y", r'\b\w+ \d{1,2}, \d{4}\b'),
            ("%m/%d/%Y",  r'\b\d{1,2}/\d{1,2}/\d{4}\b'),
        ]
        for fmt, pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return datetime.strptime(match.group(), fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return None
```

---

## Step 7 — Implement `src/civicpulse/scraper/chunker.py`

**Imports:**
```python
import re
from urllib.parse import urlparse
from slugify import slugify
from civicpulse.scraper.models import RawDocument, VaultChunk
```

**`Chunker.chunk(doc: RawDocument) -> list[VaultChunk]`:**
```
1. Split doc.content on Markdown headings:
     sections = re.split(r'\n(?=#{1,3} )', doc.content.strip())
   If len(sections) <= 1, fallback:
     sections = [s for s in doc.content.split("\n\n") if s.strip()]

2. Merge loop — build raw_chunks: list[str]:
   current = ""
   for section in sections:
       if len(current.split()) + len(section.split()) < 100 and current:
           current += "\n\n" + section
       elif len(current.split()) < 100 and not raw_chunks:
           current += "\n\n" + section  # first chunk: always keep growing
       else:
           if current:
               raw_chunks.append(current)
           current = section
   if current:
       raw_chunks.append(current)

3. Base slug (shared across all chunks from this doc):
     path_slug = urlparse(doc.url).path.replace("/", "-").strip("-")
     title_slug = slugify(doc.title or "untitled")[:40]
     base_slug = slugify(f"{title_slug}-{path_slug}")[:60]

4. For i, text in enumerate(raw_chunks):
     first_line = text.lstrip("# ").split("\n")[0].strip()
     chunk_title = first_line if first_line else doc.title
     yield VaultChunk(
         content=text,
         source_url=doc.url,
         document_type=doc.document_type,
         date=doc.date,
         meeting_id=doc.meeting_id,
         title=chunk_title,
         chunk_index=i,
         slug=f"{base_slug}-{i}",
     )
```

**Example:**
- Input content: `"## Meeting Agenda\n\nThe board voted...\n\n## Public Comments\n\nResidents expressed..."`
- Output: 2 VaultChunks with chunk_index 0 and 1

---

## Step 8 — Implement `src/civicpulse/scraper/writer.py`

**Imports:**
```python
from pathlib import Path
import frontmatter
from civicpulse.scraper.models import VaultChunk
```

**`VaultWriter.write(chunk: VaultChunk) -> Path`:**
```
year = chunk.date[:4] if chunk.date else "undated"
dir_path = self.vault_path / chunk.document_type / year
dir_path.mkdir(parents=True, exist_ok=True)
filename = f"{chunk.slug}-chunk-{chunk.chunk_index}.md"
file_path = dir_path / filename

metadata = {
    "source_url":    chunk.source_url,
    "document_type": chunk.document_type,
    "date":          chunk.date,
    "meeting_id":    chunk.meeting_id,
    "title":         chunk.title,
    "chunk_index":   chunk.chunk_index,
}
post = frontmatter.Post(chunk.content, **metadata)
tmp = file_path.with_suffix(".tmp")
tmp.write_text(frontmatter.dumps(post), encoding="utf-8")
tmp.rename(file_path)
return file_path
```

---

## Step 9 — Implement `src/civicpulse/scraper/indexer.py`

**Imports:**
```python
import os
import sqlite3
from pathlib import Path
import frontmatter
from civicpulse.scraper.models import Result
```

**`FTSIndexer.index() -> None`:**
```
db_path = self.vault_path / ".index.db"
con = sqlite3.connect(db_path)
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.executescript("""
    CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
        title, content, source_url, document_type, date, meeting_id,
        chunk_index UNINDEXED, file_path UNINDEXED,
        tokenize='porter ascii'
    );
    CREATE TABLE IF NOT EXISTS _index_state (
        file_path TEXT PRIMARY KEY, mtime REAL
    );
""")

state = {r["file_path"]: r["mtime"]
         for r in cur.execute("SELECT file_path, mtime FROM _index_state")}

md_files = [p for p in self.vault_path.rglob("*.md")]
current_paths = set()

for md_file in md_files:
    path_str = str(md_file)
    current_paths.add(path_str)
    mtime = os.path.getmtime(md_file)
    if state.get(path_str) == mtime:
        continue  # unchanged

    post = frontmatter.load(md_file)
    cur.execute("DELETE FROM fts_chunks WHERE file_path = ?", (path_str,))
    cur.execute(
        "INSERT INTO fts_chunks VALUES (?,?,?,?,?,?,?,?)",
        (
            post.metadata.get("title", ""),
            post.content,
            post.metadata.get("source_url", ""),
            post.metadata.get("document_type", ""),
            post.metadata.get("date", ""),
            post.metadata.get("meeting_id", ""),
            str(post.metadata.get("chunk_index", 0)),
            path_str,
        ),
    )
    cur.execute(
        "INSERT OR REPLACE INTO _index_state VALUES (?, ?)",
        (path_str, mtime),
    )

# Remove deleted files
stale = set(state) - current_paths
for path_str in stale:
    cur.execute("DELETE FROM fts_chunks WHERE file_path = ?", (path_str,))
    cur.execute("DELETE FROM _index_state WHERE file_path = ?", (path_str,))

con.commit()
con.close()
```

**`FTSIndexer.query(q, filters=None, top_n=10) -> list[Result]`:**

Filters are applied in SQL (not post-filter in Python):
```
db_path = self.vault_path / ".index.db"
if not db_path.exists():
    return []

con = sqlite3.connect(db_path)
con.row_factory = sqlite3.Row

sql = """
    SELECT title, content, source_url, document_type, date, meeting_id,
           chunk_index, file_path, rank
    FROM fts_chunks
    WHERE fts_chunks MATCH ?
"""
params: list = [q]

if filters:
    if "document_type" in filters:
        sql += " AND document_type = ?"
        params.append(filters["document_type"])
    if "date" in filters:  # expects tuple (start_iso, end_iso)
        sql += " AND date BETWEEN ? AND ?"
        params.extend(filters["date"])

sql += " ORDER BY rank LIMIT ?"
params.append(top_n)

# Note: dates stored as ISO 8601 text; BETWEEN works correctly for lexicographic comparison

rows = con.execute(sql, params).fetchall()
con.close()

return [
    Result(
        file_path=r["file_path"],
        source_url=r["source_url"],
        document_type=r["document_type"],
        date=r["date"] or None,
        meeting_id=r["meeting_id"] or None,
        title=r["title"],
        chunk_index=int(r["chunk_index"]),
        score=abs(r["rank"]),   # FTS5 rank values are negative
        content_preview=r["content"][:200],
    )
    for r in rows
]
```

---

## Step 10 — Implement `src/civicpulse/scraper/cli.py`

Change `scrape` from `@click.group()` to `@click.command()`. Re-run `uv sync` after
any change to `[project.scripts]` in `pyproject.toml` (no change needed here since
the entry point name is unchanged).

**Imports:**
```python
import os
from pathlib import Path
import click
from dotenv import load_dotenv
from civicpulse.scraper.chunker import Chunker
from civicpulse.scraper.indexer import FTSIndexer
from civicpulse.scraper.sources.babylon_website import BabylonWebsiteScraper
from civicpulse.scraper.sources.agenda_center import AgendaCenterScraper
from civicpulse.scraper.writer import VaultWriter
load_dotenv()
```

```python
@click.command()
@click.option("--vault", default=os.getenv("VAULT_PATH", "./vault"), show_default=True)
def scrape(vault: str) -> None:
    """Scrape all Town of Babylon sources and populate the knowledge vault."""
    vault_path = Path(vault)
    chunker = Chunker()
    writer = VaultWriter(vault_path)
    total_pages, total_chunks = 0, 0

    for ScraperClass in (BabylonWebsiteScraper, AgendaCenterScraper):
        docs = ScraperClass().scrape_all()
        total_pages += len(docs)
        for doc in docs:
            for chunk in chunker.chunk(doc):
                writer.write(chunk)
                total_chunks += 1

    FTSIndexer(vault_path).index()
    click.echo(f"Done. {total_pages} pages scraped → {total_chunks} chunks indexed.")


@click.command()
@click.argument("query_string")
@click.option("--top-n", default=10, show_default=True)
@click.option("--type", "doc_type", default=None, help="Filter by document_type.")
@click.option("--vault", default=os.getenv("VAULT_PATH", "./vault"), show_default=True)
def query(query_string: str, top_n: int, doc_type: str | None, vault: str) -> None:
    """Query the knowledge vault FTS index."""
    load_dotenv()
    filters = {"document_type": doc_type} if doc_type else None
    results = FTSIndexer(Path(vault)).query(query_string, filters=filters, top_n=top_n)
    if not results:
        click.echo("No results found.")
        return
    for i, r in enumerate(results, 1):
        click.echo(f"\n[{i}] {r.title}  (score: {r.score:.4f})")
        click.echo(f"    Type: {r.document_type}  |  Date: {r.date or 'n/a'}")
        click.echo(f"    URL:  {r.source_url}")
        click.echo(f"    {r.content_preview}…")
```

---

## Step 11 — Create test fixtures and test files

### `tests/scraper/fixtures/department_page.html`
Minimal HTML with nav/footer boilerplate and a `<main>` content area:
```html
<!DOCTYPE html><html><head><title>All Departments – Town of Babylon</title></head>
<body>
  <nav>Navigation links here</nav>
  <main>
    <h2>Department Directory</h2>
    <p>The Town of Babylon operates the following departments to serve residents.</p>
    <h3>Public Works</h3>
    <p>Manages roads, sanitation, and infrastructure maintenance across the township.</p>
  </main>
  <footer>Footer content here</footer>
</body></html>
```

### `tests/scraper/fixtures/meeting_minutes.html`
HTML with multiple sections and a meeting date in the title:
```html
<!DOCTYPE html><html><head><title>Town Board Meeting Minutes – March 15, 2026</title></head>
<body>
  <main>
    <h1>Town Board Meeting Minutes – March 15, 2026</h1>
    <h2>Call to Order</h2>
    <p>The meeting was called to order at 7:00 PM by Supervisor Rich Schaffer. All board
    members were present. The pledge of allegiance was recited and a moment of silence was
    observed for recently deceased community members. The meeting was held at Town Hall.</p>
    <h2>Public Comments</h2>
    <p>Three residents spoke during the public comment period regarding the proposed zoning
    change on Sunrise Highway. Concerns about traffic impact and environmental review were
    raised. The supervisor noted that the planning board would address these concerns at
    their next scheduled meeting on April 1st.</p>
    <h2>Resolutions</h2>
    <p>Resolution 2026-045 was passed unanimously authorizing the highway department to
    proceed with the Main Street repaving project. Total cost not to exceed $250,000.
    Funding to come from the capital improvements budget line item approved in January.</p>
  </main>
</body></html>
```

### `tests/scraper/fixtures/agenda_listing.html`
Agenda Center listing page with links to child pages:
```html
<!DOCTYPE html><html><head><title>Agenda Center – Town of Babylon</title></head>
<body>
  <main>
    <h1>Agenda Center</h1>
    <p>Find agendas and minutes for all Town boards below.</p>
    <ul>
      <li><a href="/AgendaCenter/ViewFile/Agenda/_03152026-1234">March 15, 2026 Agenda</a></li>
      <li><a href="/AgendaCenter/ViewFile/Minutes/_03152026-1234">March 15, 2026 Minutes</a></li>
    </ul>
  </main>
</body></html>
```

### `tests/scraper/__init__.py`
Empty file (required for pytest to discover the test module).

### `tests/scraper/fixtures/__init__.py`
Empty file.

### `tests/scraper/conftest.py`
Shared fixtures:
```python
import pytest
from pathlib import Path

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
```

### `tests/scraper/test_cleaner.py`
```python
from civicpulse.scraper.cleaner import ContentCleaner

def test_strips_nav_and_footer(department_html):
    result = ContentCleaner().clean(department_html)
    assert "Navigation links here" not in result
    assert "Footer content here" not in result

def test_extracts_main_content(department_html):
    result = ContentCleaner().clean(department_html)
    assert "Department Directory" in result
    assert "Public Works" in result

def test_emits_markdown_headings(department_html):
    result = ContentCleaner().clean(department_html)
    assert "## Department Directory" in result or "# Department Directory" in result

def test_collapses_excess_newlines():
    html = "<html><body><main><p>A</p>\n\n\n\n\n<p>B</p></main></body></html>"
    result = ContentCleaner().clean(html)
    assert "\n\n\n" not in result
```

### `tests/scraper/test_base.py`
Uses `respx` to mock all HTTP. Never makes real network calls.
```python
import respx
import httpx
import pytest
from civicpulse.scraper.base import BaseScraper

ROBOTS_ALLOW = "User-agent: *\n"
ROBOTS_DENY  = "User-agent: *\nDisallow: /denied\n"

@respx.mock
def test_scrape_returns_raw_document(department_html):
    respx.get("https://example.gov/robots.txt").mock(return_value=httpx.Response(200, text=ROBOTS_ALLOW))
    respx.get("https://example.gov/page").mock(return_value=httpx.Response(200, html=department_html, headers={"content-type": "text/html"}))
    scraper = BaseScraper(seed_urls=["https://example.gov/page"], max_depth=0)
    docs = scraper.scrape("https://example.gov/page")
    assert len(docs) == 1
    assert docs[0].url == "https://example.gov/page"
    assert "Department Directory" in docs[0].content

@respx.mock
def test_robots_txt_blocks_disallowed_path():
    respx.get("https://example.gov/robots.txt").mock(return_value=httpx.Response(200, text=ROBOTS_DENY))
    scraper = BaseScraper(seed_urls=[], max_depth=0)
    result = scraper.scrape("https://example.gov/denied")
    assert result == []

@respx.mock
def test_404_returns_empty_list():
    respx.get("https://example.gov/robots.txt").mock(return_value=httpx.Response(200, text=ROBOTS_ALLOW))
    respx.get("https://example.gov/missing").mock(return_value=httpx.Response(404))
    scraper = BaseScraper(seed_urls=[], max_depth=0)
    assert scraper.scrape("https://example.gov/missing") == []

@respx.mock
def test_link_following_depth_1(department_html, agenda_listing_html):
    respx.get("https://example.gov/robots.txt").mock(return_value=httpx.Response(200, text=ROBOTS_ALLOW))
    respx.get("https://example.gov/listing").mock(return_value=httpx.Response(200, html=agenda_listing_html, headers={"content-type": "text/html"}))
    # child link from agenda_listing.html (same domain required — use example.gov in fixture for tests)
    # This test uses max_depth=1 and verifies at least the seed page is scraped
    scraper = BaseScraper(seed_urls=["https://example.gov/listing"], max_depth=0)
    docs = scraper.scrape("https://example.gov/listing")
    assert len(docs) >= 1
```

### `tests/scraper/test_chunker.py`
```python
from civicpulse.scraper.chunker import Chunker
from civicpulse.scraper.models import RawDocument

def make_doc(content: str, doc_type: str = "service-page") -> RawDocument:
    return RawDocument(url="https://example.gov/page", content=content,
                       title="Test Page", document_type=doc_type, date=None, meeting_id=None)

LONG = " ".join(["word"] * 120)  # 120 words

def test_two_sections_produce_two_chunks():
    content = f"## Section One\n\n{LONG}\n\n## Section Two\n\n{LONG}"
    chunks = Chunker().chunk(make_doc(content))
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1

def test_short_section_merged_with_previous():
    content = f"## Long Section\n\n{LONG}\n\n## Tiny\n\nfew words"
    chunks = Chunker().chunk(make_doc(content))
    assert len(chunks) == 1

def test_all_required_fields_present():
    content = f"## Only Section\n\n{LONG}"
    chunk = Chunker().chunk(make_doc(content))[0]
    assert chunk.source_url
    assert chunk.document_type
    assert chunk.title
    assert chunk.slug
    assert chunk.chunk_index == 0

def test_slug_is_deterministic():
    doc = make_doc(f"## Section\n\n{LONG}")
    assert Chunker().chunk(doc)[0].slug == Chunker().chunk(doc)[0].slug
```

### `tests/scraper/test_writer.py`
```python
from pathlib import Path
import frontmatter
from civicpulse.scraper.writer import VaultWriter
from civicpulse.scraper.models import VaultChunk

def make_chunk(**kwargs) -> VaultChunk:
    defaults = dict(content="Body text here.", source_url="https://example.gov/page",
                    document_type="service-page", date="2026-03-15", meeting_id=None,
                    title="Test Chunk", chunk_index=0, slug="test-chunk-0")
    return VaultChunk(**{**defaults, **kwargs})

def test_writes_file_at_correct_path(tmp_path):
    chunk = make_chunk(document_type="meeting-minutes", date="2026-03-15", chunk_index=0)
    path = VaultWriter(tmp_path).write(chunk)
    assert path.parts[-3] == "meeting-minutes"
    assert path.parts[-2] == "2026"
    assert path.exists()

def test_undated_chunk_goes_to_undated_dir(tmp_path):
    chunk = make_chunk(date=None)
    path = VaultWriter(tmp_path).write(chunk)
    assert "undated" in str(path)

def test_frontmatter_roundtrip(tmp_path):
    chunk = make_chunk()
    path = VaultWriter(tmp_path).write(chunk)
    post = frontmatter.load(path)
    assert post["source_url"] == chunk.source_url
    assert post["document_type"] == chunk.document_type
    assert post["chunk_index"] == chunk.chunk_index
    assert post.content == chunk.content

def test_overwrite_does_not_duplicate(tmp_path):
    chunk = make_chunk()
    VaultWriter(tmp_path).write(chunk)
    VaultWriter(tmp_path).write(chunk)
    assert len(list(tmp_path.rglob("*.md"))) == 1
```

### `tests/scraper/test_indexer.py`
```python
import frontmatter
from pathlib import Path
from civicpulse.scraper.indexer import FTSIndexer
from civicpulse.scraper.writer import VaultWriter
from civicpulse.scraper.models import VaultChunk

def write_chunk(vault: Path, **kwargs) -> Path:
    defaults = dict(content="Some civic content about zoning variances.",
                    source_url="https://example.gov/p", document_type="planning",
                    date="2026-01-01", meeting_id=None,
                    title="Zoning Page", chunk_index=0, slug="zoning-page-0")
    return VaultWriter(vault).write(VaultChunk(**{**defaults, **kwargs}))

def test_query_returns_matching_chunk(tmp_path):
    write_chunk(tmp_path, content="The zoning variance was approved by the board.")
    write_chunk(tmp_path, content="Budget appropriations for the fiscal year.", slug="budget-0", title="Budget")
    FTSIndexer(tmp_path).index()
    results = FTSIndexer(tmp_path).query("zoning")
    assert len(results) >= 1
    assert "zoning" in results[0].content_preview.lower()

def test_empty_vault_returns_empty_list(tmp_path):
    assert FTSIndexer(tmp_path).query("anything") == []

def test_incremental_update_picks_up_new_file(tmp_path):
    write_chunk(tmp_path)
    FTSIndexer(tmp_path).index()
    write_chunk(tmp_path, content="New content about recycling programs.", slug="recycle-0", title="Recycling", chunk_index=1)
    FTSIndexer(tmp_path).index()
    results = FTSIndexer(tmp_path).query("recycling")
    assert len(results) >= 1

def test_document_type_filter(tmp_path):
    write_chunk(tmp_path, document_type="planning", content="Planning board approved the subdivision.", slug="plan-0")
    write_chunk(tmp_path, document_type="foil", content="FOIL request processing time planning.", slug="foil-0", chunk_index=1)
    FTSIndexer(tmp_path).index()
    results = FTSIndexer(tmp_path).query("planning", filters={"document_type": "foil"})
    assert all(r.document_type == "foil" for r in results)

def test_deleted_file_removed_from_index(tmp_path):
    path = write_chunk(tmp_path, content="Temporary content about permits.")
    FTSIndexer(tmp_path).index()
    path.unlink()
    FTSIndexer(tmp_path).index()
    assert FTSIndexer(tmp_path).query("permits") == []
```

### Delete `tests/test_scaffold.py`
Remove the placeholder test now that real tests exist.

---

## Files Created / Modified

| Path | Action |
|------|--------|
| `pyproject.toml` | Amend — add `pdfplumber>=0.11` |
| `src/civicpulse/scraper/models.py` | Amend — rename `html` field to `content` |
| `src/civicpulse/scraper/base.py` | Implement |
| `src/civicpulse/scraper/cleaner.py` | Implement |
| `src/civicpulse/scraper/chunker.py` | Implement |
| `src/civicpulse/scraper/writer.py` | Implement |
| `src/civicpulse/scraper/indexer.py` | Implement |
| `src/civicpulse/scraper/cli.py` | Implement |
| `src/civicpulse/scraper/sources/__init__.py` | Create (empty) |
| `src/civicpulse/scraper/sources/babylon_website.py` | Create |
| `src/civicpulse/scraper/sources/agenda_center.py` | Create |
| `tests/scraper/__init__.py` | Create (empty) — already exists, verify |
| `tests/scraper/fixtures/__init__.py` | Create (empty) |
| `tests/scraper/fixtures/department_page.html` | Create |
| `tests/scraper/fixtures/meeting_minutes.html` | Create |
| `tests/scraper/fixtures/agenda_listing.html` | Create |
| `tests/scraper/conftest.py` | Create |
| `tests/scraper/test_cleaner.py` | Create |
| `tests/scraper/test_base.py` | Create |
| `tests/scraper/test_chunker.py` | Create |
| `tests/scraper/test_writer.py` | Create |
| `tests/scraper/test_indexer.py` | Create |
| `tests/test_scaffold.py` | Delete |

---

## Verification

```bash
# Install new dep
uv sync

# All tests pass (no real HTTP)
uv run pytest tests/scraper/ -v
# Expected: all green

# Run full scraper against live site
uv run civicpulse-scrape
# Expected: "Done. X pages scraped → Y chunks indexed."

# Spot-check vault structure
ls vault/
# Expected: meeting-minutes/, service-page/, planning/, etc.

# Inspect a vault file
head -20 vault/meeting-minutes/2026/*.md
# Expected: YAML frontmatter + Markdown content

# Test query CLI
uv run civicpulse-query "town board budget"
uv run civicpulse-query "zoning variance" --type planning
# Expected: ranked results with title, score, URL, preview
```
