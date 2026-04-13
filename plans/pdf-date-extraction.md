# Plan: Fix PDF Date Extraction in AgendaCenterScraper

> Source PRD: [GitHub Issue #3](https://github.com/ScottSucksAtProgramming/civicpulse/issues/3)

## Architectural decisions

- **No model changes**: `RawDocument` and `VaultChunk` dataclasses are unchanged. Use `dataclasses.replace(doc, date=...)` to return an updated instance — do not mutate fields directly.
- **Override pattern**: `AgendaCenterScraper` overrides `_extract_pdf()` following the same pattern already used for `_extract_html()`: call `super()`, then post-process the returned `RawDocument`.
- **`BaseScraper` is untouched**: No hooks, callbacks, or changes to the parent class.
- **Single `_parse_date()` entry point**: The existing static method on `AgendaCenterScraper` is the sole date-parsing implementation for both HTML and PDF paths. No duplication.
- **Full content scan, not page-1 slice**: `BaseScraper._extract_pdf()` joins pages with `"\n\n"`, making page boundaries unrecoverable from `content`. The body-text fallback passes all of `content` to `_parse_date()`, which uses `re.search` and will find a date anywhere in the string.
- **URL pattern scope**: `_date_from_url()` parses only the 8-digit segment pattern (e.g., `Minutes/03152026`). Bare numeric meeting IDs (e.g., `Agenda/1234`) are not treated as dates to avoid false positives.
- **Test infrastructure**: Phase 2 tests require a structurally valid PDF binary fixture (pdfplumber-parseable). Store it in `tests/scraper/fixtures/`. Use pytest `caplog` for warning assertions; the logger name is `AgendaCenterScraper`.

---

## Phase 1: URL-pattern date extraction

**User stories**: 2, 3, 6, 12 (URL first / fast path; no schema changes; named helpers)

### What to build

Add a `_date_from_url(url: str) -> str | None` private helper method to `AgendaCenterScraper` that extracts a date from Agenda Center URL patterns. The target pattern is an 8-digit trailing segment that encodes a date as `MMDDYYYY` (e.g., `AgendaCenter/ViewFile/Minutes/03152026`). The helper returns an ISO-formatted date string (`YYYY-MM-DD`) if the pattern matches and the decoded date is valid, or `None` otherwise.

Override `_extract_pdf(body_bytes, url)` in `AgendaCenterScraper`. The override calls the parent implementation to get a fully-populated `RawDocument` (text extracted, title set, `document_type` inferred). It then calls `_date_from_url(url)` and, if a date is found, returns a new `RawDocument` via `dataclasses.replace(doc, date=date)`. If no URL date is found, it returns the doc unchanged (date remains `None` — body fallback is added in Phase 2).

### Acceptance criteria

- [ ] `_date_from_url("https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Minutes/03152026")` returns `"2026-03-15"`
- [ ] `_date_from_url("https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Agenda/1234")` returns `None` (bare meeting ID, not an 8-digit date)
- [ ] `_date_from_url("https://www.townofbabylonny.gov/AgendaCenter/ViewFile/Minutes/99999999")` returns `None` (invalid date digits)
- [ ] `_date_from_url` with any URL lacking an 8-digit segment returns `None`
- [ ] Scraping a PDF URL with an embedded date produces a `RawDocument` where `date` equals the correctly parsed ISO date
- [ ] `BaseScraper._extract_pdf()` is unchanged and all existing tests pass

---

## Phase 2: Full-content body-text fallback + warning log

**User stories**: 1, 4, 5, 8, 9, 10, 11 (body fallback; warning; tests)

### What to build

Extend the `_extract_pdf()` override from Phase 1: after `_date_from_url()` returns `None`, pass the full `RawDocument.content` string to the existing `_parse_date()` static method. If a date is found, return `dataclasses.replace(doc, date=date)`. If neither strategy yields a date, emit a `WARNING` log including the URL, then return the original doc with `date=None`.

Add a valid PDF binary fixture to `tests/scraper/fixtures/` — a minimal real PDF (created with a tool like `reportlab` or any PDF writer) whose text content includes a date in one of the supported formats. Register it in `tests/scraper/conftest.py`.

Write a `tests/scraper/test_agenda_center.py` file with the following test cases:

- **URL extraction** (reuse Phase 1 unit tests for `_date_from_url()`)
- **Body fallback**: supply a PDF binary fixture whose URL has no date pattern; assert returned `RawDocument.date` matches the date embedded in the PDF text
- **URL takes priority**: supply a PDF whose URL has one date and whose body text has a different date; assert the URL date wins
- **Warning emitted**: supply a PDF whose URL and body text both lack a date; use `caplog` to assert a `WARNING` is logged and the logger name is `AgendaCenterScraper`
- **`VaultWriter` path**: given a `VaultChunk` with a resolved date produced by the scraper, assert the written file lands in `vault/meeting-minutes/{year}/`, not `undated/`

### Acceptance criteria

- [ ] PDF with date-bearing body text and no URL date pattern → `RawDocument.date` set correctly
- [ ] PDF where both URL and body text have a date → URL date takes precedence
- [ ] PDF with no date in URL or body → `RawDocument.date` is `None` and a `WARNING` is logged to logger `AgendaCenterScraper`
- [ ] PDF binary fixture is a structurally valid PDF (pdfplumber opens it without exception)
- [ ] `VaultWriter` writes a dated chunk to `vault/meeting-minutes/2026/`, not `undated/`
- [ ] All Phase 1 tests continue to pass

---

## Phase 3: Acceptance validation

**User stories**: 7 (existing undated chunks overwritten; vault clean after re-scrape)

### What to build

Run the full scraper pipeline against the live Town of Babylon Agenda Center. Inspect the resulting vault to confirm the fix is working end-to-end. No code changes in this phase — this is an operational verification step.

Steps:
1. Run the scraper CLI targeting `AgendaCenterScraper` seed URLs.
2. Rebuild the FTS5 index.
3. Inspect `vault/meeting-minutes/` — confirm new chunks appear under year subdirectories (e.g., `2026/`), not `undated/`.
4. Confirm any previously stale files in `undated/` are inert (not re-indexed).
5. Spot-check 2–3 vault chunks for correct YAML frontmatter (`date`, `document_type`, `meeting_id`).

### Acceptance criteria

- [ ] Zero new meeting-minutes chunks written to `vault/meeting-minutes/undated/` after re-scrape
- [ ] At least one chunk with a correctly dated path (e.g., `vault/meeting-minutes/2026/`) exists
- [ ] Spot-checked chunks have valid `date` frontmatter in `YYYY-MM-DD` format
- [ ] Scraper log contains no unexpected errors; any `WARNING` entries for truly undated documents are expected and acceptable
- [ ] FTS5 index rebuilds without errors
