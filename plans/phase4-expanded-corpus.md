# Plan: Phase 4 — Expanded Corpus

> Source PRD: [GitHub Issue #8](https://github.com/ScottSucksAtProgramming/civicpulse/issues/8)

## Architectural Decisions

Durable decisions that apply across all phases:

- **CLI commands**: `civicpulse-import --source [ecode360|ecode360-api] --path <dir>` registered in `pyproject.toml` alongside existing `civicpulse-scrape` and `civicpulse-query`
- **Canonical document types**: `ordinance` (eCode360), `meeting-video` (YouTube), `meeting-minutes` (fix from `minutes` in MetadataFilter), all others unchanged
- **Vault frontmatter additions**: `section_number` field for `ordinance` chunks; `video_id` and `timestamp_start` (seconds) fields for `meeting-video` chunks
- **eCode360 customer ID**: `BA0924` — hardcoded constant, overridable via `CIVICPULSE_ECODE_CUSTOMER` env var
- **YouTube channel**: `UCIYf6QoRXGaBgbqO24thUlg` — hardcoded constant (official Town of Babylon channel)
- **Env vars**: `CIVICPULSE_YOUTUBE_API_KEY` (YouTube Data API v3), `CIVICPULSE_ECODE_API_KEY` + `CIVICPULSE_ECODE_API_SECRET` (future eCode360 API)
- **Chunk strategy**: eCode360 splits on `§` symbol boundaries; YouTube uses 3-minute fixed windows with 30-second overlap
- **Citation format**: YouTube chunks cite `https://youtu.be/{video_id}?t={timestamp_start}` as `source_url`; ordinance chunks cite the canonical eCode360 section URL
- **Data directories** (gitignored): `data/ecode360/` for source PDFs; `data/youtube/no-transcript.txt` for videos missing captions
- **New dependencies**: `markitdown` (PDF→Markdown), `youtube-transcript-api` (caption fetching), `google-api-python-client` (YouTube Data API v3 metadata)

---

## Phase 1: Taxonomy Fix + Import CLI Skeleton

**User stories**: 13, 14, 19

### What to build

Fix the document type mismatch between the vault and MetadataFilter before any new content is added. The MetadataFilter system prompt currently lists `minutes` and omits `meeting-video` — queries for meeting content silently fall back to no filter. Update the system prompt to use all canonical vault types. Add the `civicpulse-import` CLI command as a registered entry point that accepts `--source` and `--path` flags, wired to a stub that prints a "not yet implemented" message for each source. This establishes the CLI contract all subsequent phases slot into.

### Acceptance criteria

- [ ] MetadataFilter system prompt lists exactly: `agenda`, `meeting-minutes`, `ordinance`, `meeting-video`, `service-page`, `public-meeting`, `council`, `clerk`, `clerk-form`, `foil`, `department-page`, `planning`
- [ ] A query like "what were the meeting minutes from last month?" causes MetadataFilter to return `document_type: meeting-minutes` (not `minutes`)
- [ ] A query like "what is the fence height ordinance?" causes MetadataFilter to return `document_type: ordinance`
- [ ] `civicpulse-import --source ecode360 --path ./data/ecode360` runs without error (stub output acceptable)
- [ ] `civicpulse-import --help` documents available `--source` values
- [ ] Existing MetadataFilter tests updated to use `meeting-minutes`; new tests added for `ordinance` and `meeting-video` routing

---

## Phase 2: eCode360 PDF Import

**User stories**: 1, 2, 3, 4, 12, 15

### What to build

A complete end-to-end path from locally-downloaded eCode360 PDFs to queryable vault chunks. The `SectionChunker` converts Markdown output (produced by markitdown) into chunks split on `§` boundaries, with `section_number` extracted into frontmatter. The `ECodeImporter` orchestrates: markitdown converts each PDF to Markdown, `SectionChunker` splits it, `VaultWriter` writes chunks with `document_type: ordinance`, and `FTSIndexer` re-indexes. Wire into `civicpulse-import --source ecode360 --path <dir>`. Move existing PDFs from repo root to `data/ecode360/` and add to `.gitignore`.

After this phase, a resident asking "what is the maximum fence height in a residential district?" receives a grounded answer citing the specific ordinance section (e.g., `§ 120-167`).

### Acceptance criteria

- [ ] `civicpulse-import --source ecode360 --path data/ecode360` processes all PDFs and writes chunks to `vault/ordinance/`
- [ ] Each chunk has `document_type: ordinance`, `section_number`, `source_url` (canonical eCode360 URL), and `title` in frontmatter
- [ ] Sections shorter than the minimum word threshold are merged with the following section rather than written as standalone chunks
- [ ] PDF preamble/header content (page numbers, document headers) is stripped from chunk content
- [ ] `civicpulse-query "fence height residential"` returns chunks from `vault/ordinance/`
- [ ] `SectionChunker` has unit tests: correct split count for multi-section Markdown, merge behaviour for short sections
- [ ] `ECodeImporter` has unit tests: given fixture PDFs, correct `document_type` and `section_number` in output chunks
- [ ] `data/ecode360/` is listed in `.gitignore`

---

## Phase 3: Forms Depth Expansion

**User stories**: 8, 9, 10, 11

### What to build

Increase the crawl depth for the Forms & Publications page from 1 to 2 in the existing `BabylonWebsiteScraper` configuration. At depth 2 the scraper follows links to individual form PDFs and ingests them via the existing `pdfplumber`-based PDF extractor. No new scraper or chunker is needed. Re-run `civicpulse-scrape` to populate the vault with form content under `clerk-form` and related document types.

After this phase, a resident asking "how do I apply for a dog license?" receives a grounded answer that includes the actual form requirements from the PDF, not just the listing page.

### Acceptance criteria

- [ ] `civicpulse-scrape` follows PDF links from `/243/Forms-Publications` and writes chunks to `vault/clerk-form/`
- [ ] At least one form PDF per department category (Assessor, Building, Town Clerk, etc.) appears as vault chunks
- [ ] Crawl depth for the `/243/` seed is 2; all other seeds remain at their current depth
- [ ] Chunks from form PDFs have correct `document_type` (`clerk-form`, `clerk`, etc.) based on existing URL-to-type mapping
- [ ] `civicpulse-query "dog license application"` returns a chunk from a Town Clerk form PDF

---

## Phase 4: YouTube Meeting Transcripts

**User stories**: 5, 6, 7, 12, 14, 17, 18

### What to build

A `YouTubeScraper` that fetches all videos from the official Town of Babylon channel, filters to town board meetings and public hearings by title pattern, retrieves transcripts via `youtube-transcript-api`, and chunks them into 3-minute fixed windows with 30-second overlap. Each chunk's `source_url` deep-links to the exact moment in the video (`youtu.be/{video_id}?t={seconds}`). On first run all available videos are processed; subsequent runs skip video IDs already present in the index state. Videos with no available transcript are skipped from the vault and their ID + title are appended to `data/youtube/no-transcript.txt`. Register `CIVICPULSE_YOUTUBE_API_KEY` in `.env.example`. Wire the scraper into `civicpulse-scrape` (not `civicpulse-import` — it's a live source, not a file import).

After this phase, a resident asking "what did the town board discuss about the waterfront rezoning?" receives a grounded answer with a clickable timestamp link to the relevant moment in the meeting video.

### Acceptance criteria

- [ ] `civicpulse-scrape` fetches videos from channel `UCIYf6QoRXGaBgbqO24thUlg` and writes chunks to `vault/meeting-video/`
- [ ] Each chunk has `document_type: meeting-video`, `video_id`, `video_title`, `published_at`, `timestamp_start`, and `source_url` (deep-link format) in frontmatter
- [ ] Chunks are 3-minute windows with 30-second overlap; no chunk exceeds ~200 words
- [ ] Re-running `civicpulse-scrape` does not re-process already-indexed video IDs
- [ ] Videos with no available transcript are absent from the vault; their ID and title appear in `data/youtube/no-transcript.txt`
- [ ] `CIVICPULSE_YOUTUBE_API_KEY` is documented in `.env.example`; scraper raises a clear error at startup if the key is missing
- [ ] `YouTubeScraper` unit tests: given mocked API + transcript responses, assert correct chunk count, overlap, and deep-link `source_url` format
- [ ] `YouTubeScraper` unit test: given a mocked video with no transcript, assert vault is empty and no-transcript log is written
- [ ] `civicpulse-query "waterfront rezoning"` returns chunks from `vault/meeting-video/`

---

## Phase 5: eCode360 API Stub

**User stories**: 16

### What to build

An `ECodeScraper` that implements the same `RawDocument`-returning interface as existing scrapers, but queries the eCode360 EcodeGateway REST API instead of local PDFs. It walks the structure tree from `ROOT` via `GET /customer/{customer}/structure/{guid}`, fetches section content via `GET /customer/{customer}/code/content/{guid}`, and produces `RawDocument` objects with `document_type: ordinance`. Authentication uses `api-key` and `api-secret` headers from env vars. Register under `civicpulse-import --source ecode360-api`. The scraper is built and tested but **not activated in production** until API credentials are obtained from the Town of Babylon.

### Acceptance criteria

- [ ] `civicpulse-import --source ecode360-api` is a valid command; without credentials it exits with a clear "API key not configured" message
- [ ] `ECodeScraper` unit tests: given mocked EcodeGateway responses, assert correct `RawDocument` output with `document_type: ordinance` and `section_number`
- [ ] `ECodeScraper` respects `CIVICPULSE_ECODE_CUSTOMER` env var override (defaults to `BA0924`)
- [ ] `CIVICPULSE_ECODE_API_KEY` and `CIVICPULSE_ECODE_API_SECRET` documented in `.env.example`
- [ ] `ECodeScraper` output passes through the same `SectionChunker` → `VaultWriter` → `FTSIndexer` pipeline as the PDF importer

---

## Phase 6: Retrieval Validation Golden Set

**User stories**: 20

### What to build

A `tests/retrieval/golden_set.yaml` file with 10–15 hand-written Q&A pairs, at least 2 per source type (`ordinance`, `meeting-video`, `meeting-minutes`, `clerk-form`, `agenda`, `service-page`). Each entry includes the question, the expected `document_type` the top result should come from, and a hint about the expected source (e.g., section number or video title keyword). This is a manual benchmark, not an automated assertion — it documents what "good retrieval" looks like and provides a repeatable checklist for validating pipeline changes.

### Acceptance criteria

- [ ] `tests/retrieval/golden_set.yaml` exists with at least 10 entries
- [ ] Each entry has `question`, `expected_document_type`, and `source_hint` fields
- [ ] At least 2 entries per source type: `ordinance`, `meeting-video`, `meeting-minutes`, `clerk-form`
- [ ] A `README` or inline comment in the YAML explains how to run manual validation using `civicpulse-query`
- [ ] All 10+ queries return at least one result from the expected `document_type` against the populated vault
