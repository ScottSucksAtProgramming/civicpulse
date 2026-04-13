# Plan: CivicPulse

> Source PRD: `CivicPulse_PRD.md` — Civic Engagement & Local Government Intelligence Agent, Town of Babylon pilot

## Architectural decisions

Durable decisions that apply across all phases:

- **Storage**: Knowledge vault — Markdown files with YAML frontmatter, organized as `vault/{document_type}/{year}/{slug}.md`. No vector database.
- **Search index**: SQLite FTS5 (primary) or Typesense for BM25 keyword retrieval over the vault
- **Retrieval flow**: Metadata filter → BM25 keyword search → LLM semantic re-ranking → grounded response with source citation
- **LLM**: Claude Haiku (default) / Claude Sonnet (complex queries) via Anthropic API. Model selection must be swappable without rewriting core logic.
- **Backend**: Python API (FastAPI) orchestrating scraper, retrieval pipeline, LLM calls, and logging
- **Frontend**: Mobile-friendly web chat. No login, no user accounts.
- **Privacy**: No PII stored at any layer. PII redaction pipeline runs before any data is written to storage. Session data is ephemeral.
- **Frontmatter schema**: Every vault document includes `source_url`, `document_type`, `date`, `meeting_id` (where applicable), `chunk_index`, `title`
- **Data sources**: townofbabylonny.gov, eCode360, YouTube Data API (captions only), Town Clerk forms

---

## Phase 1: Knowledge Vault + Scraper Foundation

**User stories**: Residents can eventually get answers grounded in official government documents rather than LLM training data.

### What to build

A web scraper targeting townofbabylonny.gov (main site pages + Agenda Center meeting minutes and agendas). Each scraped document is chunked into meaningful segments and written as a Markdown file with YAML frontmatter into the knowledge vault directory structure. A SQLite FTS5 index is built (and incrementally updated) over the vault. A CLI tool lets you run a raw keyword query against the index and verify that relevant chunks come back with correct source attribution.

The vault directory can be opened as an Obsidian vault for human inspection and curation during development.

### Acceptance criteria

- [ ] Scraper successfully pulls content from townofbabylonny.gov main pages and Agenda Center
- [ ] Each chunk stored as `.md` with correct YAML frontmatter (`source_url`, `document_type`, `date`, `chunk_index`, `title`)
- [ ] Vault directory structure follows `vault/{document_type}/{year}/{slug}.md`
- [ ] SQLite FTS5 index built over vault and reflects current files
- [ ] CLI query returns ranked chunks with source URL and document metadata
- [ ] Scraper respects robots.txt and applies rate limiting
- [x] Vault is openable as an Obsidian vault with readable structure

---

## Phase 2: Core Retrieval Pipeline

**User stories**: Resident asks a civic question and receives a plain-language answer grounded in retrieved official documents. Agent says "I don't know" when no relevant content is found.

### What to build

A retrieval pipeline exposed as a backend API endpoint (`POST /query`). The pipeline applies metadata filters inferred from the query (date range, document type), runs BM25 search over the filtered vault, passes the top-N chunks to Claude Haiku for re-ranking and synthesis, and returns a grounded response with source citations. No UI yet — validated via API calls and automated tests.

### Acceptance criteria

- [ ] `POST /query` accepts a natural language question and returns a grounded answer
- [ ] Metadata filter layer correctly narrows candidate set when date or document type is inferable
- [ ] BM25 retrieval returns top-N relevant chunks
- [ ] LLM response cites source document title and URL for every factual claim
- [ ] Agent returns a "no information found" response (with official source link) when retrieval yields no relevant chunks
- [ ] Claude Haiku is the default model; Sonnet is invokable for complex queries
- [ ] Model selection is configurable without code changes

---

## Phase 3: Web Chat MVP

**User stories**: Resident opens a website, sees a welcoming entry flow, types a civic question, and receives a grounded answer. No account or login required.

### What to build

A minimal mobile-friendly web chat interface wired to the Phase 2 retrieval API. The UI opens with a guided entry flow surfacing 3–4 topic categories (e.g. "Find a service", "Understand a decision", "Learn how government works", "Contact a representative"). Users can bypass the guide and ask free-form questions at any time. A persistent disclaimer notes that responses may contain errors and official sources should be verified. A privacy statement is accessible from the page.

### Acceptance criteria

- [ ] Chat interface is mobile-friendly and loads without login
- [ ] Guided entry flow surfaces 3–4 entry categories with example prompts
- [ ] User can bypass the guide and ask a free-form question at any time
- [ ] Responses render with source citation links
- [ ] Disclaimer is visible on every page
- [ ] Privacy statement is accessible (inline or linked)
- [ ] End-to-end: resident types a question in browser, receives a grounded answer from the vault

---

## Phase 4: Expanded Corpus

**User stories**: Residents can ask about town ordinances and zoning, reference past meeting discussions (from video), and find official forms and documents — not just website pages.

### What to build

Three additional scrapers feeding into the same vault: (1) eCode360 for town code, ordinances, and zoning laws; (2) YouTube Data API for auto-generated captions from Town of Babylon meeting recordings; (3) Town Clerk forms and documents page. Each source gets its own `document_type` value in frontmatter, enabling the retrieval metadata filter to route queries to the appropriate subset of the vault.

### Acceptance criteria

- [ ] eCode360 scraper pulls ordinances and zoning code into vault with `document_type: ordinance`
- [ ] YouTube caption scraper retrieves captions via YouTube Data API (no direct video scraping) with `document_type: meeting-transcript` and `meeting_id`
- [ ] Town Clerk scraper pulls forms and document listings with `document_type: clerk-form`
- [ ] Retrieval metadata filter correctly targets each document type based on query intent
- [ ] All new sources respect robots.txt and rate limits
- [ ] FTS5 index updated to include all new vault documents

---

## Phase 5: Letter Drafting

**User stories**: Resident wants to contact an elected representative. The agent guides them through a brief dialogue, drafts a personalized letter in their voice, and provides a way to send or print it.

### What to build

A multi-turn dialogue flow (within the chat interface) that engages the resident in a short back-and-forth to understand their concern and preferred tone. Claude generates a draft letter based solely on what the resident has expressed — no advocacy or position-taking. The resident can request edits. The final letter is exportable as a PDF. The interface provides the direct link or contact page for the relevant representative.

### Acceptance criteria

- [ ] Agent initiates letter drafting flow when user expresses intent to contact a representative
- [ ] Multi-turn dialogue captures concern, desired tone, and representative target
- [ ] Generated letter is in the resident's voice; agent takes no political position
- [ ] Resident can request revisions within the same session
- [ ] Letter is exportable as a downloadable PDF
- [ ] Representative contact link is surfaced alongside the draft

---

## Phase 6: Privacy, Logging & Soapbox

**User stories**: Residents trust that no personal information is stored. The community's concerns are captured anonymously at aggregate level. Residents can optionally share what matters to them.

### What to build

A PII redaction pipeline that runs before any conversation data is written to storage (pattern matching + Claude-assisted review for names, addresses, phone numbers). Anonymous topic/theme logging that records conversation categories and query themes — never message content or identifiers. A separate aggregate data store for this logging. A "soapbox" feature in the chat UI allowing any user to submit a free-form statement about what matters to them in their community. The agent can answer questions about what data is and is not collected.

### Acceptance criteria

- [ ] PII redaction pipeline applied before any data is written; strips names, addresses, phone numbers, emails
- [ ] Conversation logs store only anonymized topic/theme categories — no message content, no IP, no device ID
- [ ] Aggregate data store is separate from the conversation/retrieval pipeline
- [ ] Soapbox submission UI is accessible from the chat interface
- [ ] Soapbox submissions pass through PII redaction before storage
- [ ] Agent can accurately describe what data is and is not collected when asked
- [ ] Privacy statement on site reflects actual data practices

---

## Phase 7: Guardrails & Hardening

**User stories**: The agent reliably stays within its civic domain, flags when it is uncertain, never fabricates information, and operates within budget limits.

### What to build

Confidence threshold logic that adds a disclaimer and links to the original source when retrieval score is low. Scope guardrails in the system prompt that instruct the agent to redirect off-topic queries. Post-generation grounding checks that verify response claims are supported by retrieved chunks. API budget caps and usage limits configured to prevent runaway costs. Source citation enforcement — responses without citations are blocked from delivery.

### Acceptance criteria

- [ ] Low-confidence responses include a disclaimer and link to original source
- [ ] Off-topic queries are redirected with a brief explanation and scope reminder
- [ ] Post-generation check flags responses that introduce claims not present in retrieved chunks
- [ ] API budget cap is configured; agent degrades gracefully when limit approached
- [ ] No response is delivered without at least one source citation
- [ ] Agent correctly handles adversarial or politically charged prompts without taking a position

---

## Phase 8: Monitoring & Pilot Validation

**User stories**: The team can evaluate whether the pilot is succeeding, identify common failure modes, and make data-driven decisions about Phase 2 expansion.

### What to build

An internal metrics layer tracking: conversation volume, hallucination rate (responses flagged by grounding check), topic diversity, letter draft completion rate, and repeat usage signals. A lightweight internal dashboard or report format for reviewing these metrics. A scraper health monitor that alerts when a data source becomes unreachable or returns unexpected content. A qualitative feedback mechanism (simple thumbs up/down or optional text) surfaced in the chat UI.

### Acceptance criteria

- [ ] Metrics tracked: conversation volume, hallucination flags, topic distribution, letter completions
- [ ] Internal dashboard or periodic report renders key pilot metrics
- [ ] Scraper health monitor detects and logs failures for each data source
- [ ] User feedback mechanism (thumbs up/down) is available in chat UI
- [ ] Feedback is anonymized before storage
- [ ] Team can generate a community insights report from aggregate topic data
