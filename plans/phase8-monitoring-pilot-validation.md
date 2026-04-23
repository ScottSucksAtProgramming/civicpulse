# Plan: Phase 8 — Monitoring & Pilot Validation

> Source PRD: https://github.com/ScottSucksAtProgramming/civicpulse/issues/12

## Architectural decisions

Durable decisions that apply across all phases:

- **Database**: All new tables written to the same `vault/.index.db` SQLite file used by existing loggers
- **Logger pattern**: Each new logger follows the existing pattern — a class with `ensure_table()` and one or more `log_*()` methods; instantiated in the app lifespan and shared via `app.state`
- **Privacy**: All user-supplied text (feedback comments) passed through `redact()` before storage — same as every other text field in the system
- **Routes**: `POST /feedback` registered before the static file catch-all mount
- **Schema — feedback_log**: `id`, `rating` (TEXT: 'up'/'down'), `redacted_comment` (TEXT nullable), `document_type` (TEXT nullable), `timestamp` (TEXT)
- **Schema — scraper_log**: `id`, `source_name` (TEXT), `url` (TEXT nullable), `error_type` (TEXT nullable — NULL on success), `timestamp` (TEXT)
- **Schema — draft_log change**: add `event_type` (TEXT NOT NULL DEFAULT 'suggestion'); existing rows backfilled via `ALTER TABLE`
- **document_type for feedback**: derived client-side from `sources[0].document_type`; null when response has no sources (soft refusal, etc.)
- **ScraperLogger call site**: CLI entry point, not `BaseScraper` — preserves the clean boundary between the scraper module and the backend database
- **Report**: `scripts/report.py`, on-demand CLI, stdout only, no scheduler

---

## Phase 1: User Feedback

**User stories**: As a resident, I want to rate any assistant response with thumbs up/down; as a resident, I want an optional text box on thumbs down; as a resident, I want unobtrusive feedback UI that doesn't disrupt the conversation; as a resident, I want to know why feedback is collected; as a resident, I want my comment handled with the same privacy care as my queries.

### What to build

A thin end-to-end feedback path: a `feedback_log` table, a `FeedbackLogger`, a `POST /feedback` endpoint, and thumbs up/down icons in the chat UI beneath each assistant response. Clicking thumbs down reveals a small optional text box; clicking thumbs up (or skipping/submitting the text box) fires the endpoint. A static note somewhere on the page explains that feedback helps improve future answers. Comments are run through `redact()` before storage.

### Acceptance criteria

- [ ] `feedback_log` table created on app startup with correct schema
- [ ] `POST /feedback` accepts rating, optional comment, and optional document_type; returns 204
- [ ] Thumbs up/down icons appear below each assistant message; visually unobtrusive
- [ ] Clicking thumbs down reveals an inline optional text box; clicking thumbs up submits immediately
- [ ] Submitting or skipping the text box fires the feedback endpoint
- [ ] Comment containing PII (phone number, email) is redacted before storage
- [ ] Page note explaining feedback purpose is visible on the chat page
- [ ] `document_type` sent from `sources[0].document_type`; null when no sources present

---

## Phase 2: Letter Completion Tracking

**User stories**: As the operator, I want to see how many letter drafts were started vs. actually generated, so that I can calculate the letter flow completion rate and identify drop-off.

### What to build

Close the letter-completion logging gap: add an `event_type` column to `draft_log` and log a `'generation'` row when a letter is actually produced. The frontend already holds `topic` in draft state — it just needs to pass it along with the generate request so generation rows have parity with suggestion rows.

### Acceptance criteria

- [ ] `draft_log` has an `event_type` column; existing rows read as `'suggestion'`
- [ ] `POST /draft/generate` writes a `draft_log` row with `event_type = 'generation'`
- [ ] Generation rows include `recipient`, `topic`, and `abstracted_concern`
- [ ] Frontend passes `topic` from draft state to the `/draft/generate` request
- [ ] Existing suggestion rows (from `/draft/suggest-recipient`) are unaffected

---

## Phase 3: Scraper Health Logging

**User stories**: As the operator, I want to see a scraper health summary (runs, failures, error types per source), so that I can quickly spot data pipeline problems.

### What to build

A `scraper_log` table and a `ScraperLogger` that the CLI entry point calls after each scraper run. On success, a row is written with a null `error_type`. On failure (exception caught at the CLI level), a row is written with the exception class name as `error_type`. This gives the report script queryable failure history without coupling `BaseScraper` to the backend database.

### Acceptance criteria

- [ ] `scraper_log` table created with correct schema
- [ ] CLI entry point wraps each scraper run; writes a success row (null `error_type`) on completion
- [ ] CLI entry point catches scraper exceptions; writes a failure row with the exception class name
- [ ] `BaseScraper` is unchanged — no new SQLite dependency in the scraper module
- [ ] Multiple sources log independently (a failure in one does not prevent logging of others)

---

## Phase 4: Pilot Report Script

**User stories**: As the operator, I want to run a single CLI command and see a complete pilot health summary; query volume; top document types; failure breakdown; letter flow completion rate; soapbox topic summary; scraper health; feedback summary.

### What to build

`scripts/report.py` — an on-demand CLI script that queries `.index.db` directly and prints a human-readable report to stdout. Seven sections in order: (1) query volume by day/week, (2) top queried document types, (3) unanswered failure breakdown by type (with a note that `no_citation` is a citation-proxy, not a semantic grounding check), (4) letter flow — suggestions vs. generations, (5) top soapbox topics, (6) scraper health — runs and failures per source, (7) feedback — thumbs up/down counts and thumbs-down rate by document type.

### Acceptance criteria

- [ ] `python scripts/report.py` runs without arguments and prints all seven sections
- [ ] Query volume section shows total queries and a breakdown by day or week
- [ ] Top document types section lists the most queried types with counts
- [ ] Failure breakdown section covers all five failure types from `unanswered_log`; `no_citation` is labeled as a citation-proxy metric
- [ ] Letter flow section shows suggestion count vs. generation count and the completion rate
- [ ] Soapbox section lists top topics by frequency
- [ ] Scraper health section lists each source with run count, failure count, and most recent error type
- [ ] Feedback section shows thumbs up count, thumbs down count, overall rate, and thumbs-down rate per document type
- [ ] Script exits cleanly if any table is empty (no crashes on a fresh DB)
