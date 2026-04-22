# Plan: Phase 6 — Privacy Hardening, Interaction Logging & Soapbox

> Source PRD: https://github.com/ScottSucksAtProgramming/civicpulse/issues/10

## Architectural decisions

- **Routes**: `/soapbox/followup`, `/soapbox/summarize`, `/soapbox/submit` — registered before the `StaticFiles` catch-all mount
- **Schema**: Two new tables in `vault/.index.db` — `query_log(id INTEGER PRIMARY KEY, document_type TEXT, timestamp TEXT)` and `soapbox_log(id INTEGER PRIMARY KEY, summary TEXT, topic TEXT, timestamp TEXT)`. The `query_log.document_type` column stores the MetadataFilter classification result as a coarse proxy for topic (e.g. `meeting-minutes`, `service-page`). This is intentionally coarse — no extra LLM call is made to derive a semantic topic.
- **Key models**: `SoapboxFollowupRequest {messages: list[dict]}`, `SoapboxFollowupResponse {question: str}`, `SoapboxSummarizeRequest {messages: list[dict]}`, `SoapboxSummary {summary: str, topic: str}`, `SoapboxSubmitRequest {summary: str, topic: str}` — all defined in `backend/types.py`
- **PII redaction**: Regex-only, stateless pure function in `backend/privacy.py`. Replacement token: `[REDACTED]`. No LLM pass. Applied at every DB write site before INSERT. Street address coverage is best-effort (number + street name patterns), not full USPS parsing.
- **Topic logging plumbing**: `QueryPipeline.run()` is modified to return `(QueryResponse, FilterSpec)`. The `/query` endpoint handler logs `filter_spec.document_type` to `query_log` after the pipeline call. If `document_type` is `None` (MetadataFilter fallback), the row is still written with `document_type = null`.
- **Soapbox state**: Separate `soapboxStep` frontend variable — not shared with `draftStep`
- **Privacy page**: Static `frontend/privacy.html` served by existing `StaticFiles` mount — no new FastAPI route
- **Soapbox model**: Configurable via `CIVICPULSE_SOAPBOX_MODEL` env var, defaults to `CIVICPULSE_MODEL`
- **Turn limit**: Configurable via `CIVICPULSE_SOAPBOX_MAX_TURNS` env var, default 3. Enforced client-side and server-side (HTTP 400 on violation).
- **Soapbox opening prompt**: Static string — no LLM call on card tap. Example: "What's on your mind about your community?"
- **Soapbox system prompt**: Instructs the LLM to ask one civic-focused, open-ended, non-leading follow-up question. Must not suggest political positions or advocate for any outcome.

---

## Phase 1: PII Redaction Foundation

**User stories**: 9, 16

### What to build

A standalone, stateless `redact(text: str) -> str` function in `backend/privacy.py` with regex patterns covering phone numbers, email addresses, street addresses (number + street name patterns — best effort, not full USPS parsing), SSNs, and honorific+name patterns (e.g. "Mr. Smith"). Matched PII is replaced with `[REDACTED]`. Wire it into the existing draft logging path so `abstracted_concern` is passed through `redact()` before being written to `draft_log`. No new endpoints, no UI changes.

### Acceptance criteria

- [ ] `redact()` replaces phone numbers (common US formats) with `[REDACTED]`
- [ ] `redact()` replaces email addresses with `[REDACTED]`
- [ ] `redact()` replaces street address patterns with `[REDACTED]`
- [ ] `redact()` replaces SSN patterns with `[REDACTED]`
- [ ] `redact()` replaces honorific + capitalized name patterns with `[REDACTED]`
- [ ] `redact()` leaves non-PII text unchanged
- [ ] `DraftLogger` calls `redact()` on `abstracted_concern` before writing to `draft_log`
- [ ] Unit tests pass for all `redact()` PII categories
- [ ] Integration test confirms a known phone number submitted through the draft flow does not appear in `draft_log`

---

## Phase 2: Privacy Policy

**User stories**: 10, 11

### What to build

A plain-language privacy policy vault document with correct YAML frontmatter so it is indexed by the FTS pipeline. A static `privacy.html` page served by the existing `StaticFiles` mount. A link from the existing privacy disclaimer banner in the chat to `/privacy.html`. No new backend routes.

### Acceptance criteria

- [ ] `vault/privacy/privacy-policy.md` exists with valid frontmatter (`document_type: privacy`, `date`, `title`, `source_url`)
- [ ] Document is indexed into FTS and retrievable via BM25 search
- [ ] Asking the chatbot "what data does CivicPulse collect?" returns an answer that cites the privacy policy document as a source
- [ ] `frontend/privacy.html` exists and renders the full privacy policy
- [ ] The existing privacy disclaimer banner in the chat links to `/privacy.html`
- [ ] `/privacy.html` is accessible in the browser without a 404

---

## Phase 3: Anonymous Interaction Logging

**User stories**: 12, 13, 17

### What to build

Create `query_log` and `soapbox_log` tables in `vault/.index.db` on app startup. Modify `QueryPipeline.run()` to return `(QueryResponse, FilterSpec)`. The `/query` endpoint handler logs `filter_spec.document_type` to `query_log` after the pipeline call — if `document_type` is `None` (MetadataFilter fallback), write the row with `document_type = null`. Letter drafting topic is already captured in `draft_log` — no change needed there. `soapbox_log` is created now and used in Phase 5.

### Acceptance criteria

- [ ] `query_log(id, document_type, timestamp)` table is created on app startup if it does not exist
- [ ] `soapbox_log(id, summary, topic, timestamp)` table is created on app startup if it does not exist
- [ ] `QueryPipeline.run()` returns `(QueryResponse, FilterSpec)` — existing callers updated accordingly
- [ ] Every `/query` request results in a new row in `query_log`; `document_type` is `null` when MetadataFilter falls back
- [ ] `query_log` rows contain no question text or user-identifiable information
- [ ] No extra LLM call is made — `document_type` is extracted from the existing MetadataFilter output
- [ ] Integration test verifies a Q&A query produces a `query_log` row
- [ ] Integration test verifies `query_log` row contains no question text

---

## Phase 4: Soapbox Conversation Loop

**User stories**: 1, 2, 3, 4, 5, 18

### What to build

A `SoapboxPipeline` class in `backend/retrieval/soapbox_pipeline.py` with a `generate_followup(messages: list[dict]) -> str` method. The method prepends a system prompt (civic-focused, non-leading, non-partisan) to the full conversation history and calls `provider.complete()`. A `POST /soapbox/followup` endpoint that validates the user-message count against `CIVICPULSE_SOAPBOX_MAX_TURNS` (HTTP 400 on violation, HTTP 503 on LLM error). A "Share Your Voice" 7th card on the opening screen. A Soapbox frontend state machine with `soapboxStep` and `soapboxMessages` variables. A persistent "Submit my response" button visible throughout. When the turn limit is reached, the UI displays a message like "Feel free to submit whenever you're ready" and stops calling `/soapbox/followup`. No storage in this phase.

### Acceptance criteria

- [ ] A 7th "Share Your Voice" card appears on the opening screen
- [ ] Tapping the card enters Soapbox mode with the static opening prompt
- [ ] User can type a free-form response and send it
- [ ] The system returns a contextual, LLM-generated follow-up question (not a canned string)
- [ ] A persistent "Submit my response" button is visible from the first user response onward
- [ ] After `CIVICPULSE_SOAPBOX_MAX_TURNS` follow-ups, the UI stops requesting new questions and shows a ready-to-submit message
- [ ] `POST /soapbox/followup` request body: `{messages: list[dict]}`; response body: `{question: str}`
- [ ] `POST /soapbox/followup` returns HTTP 400 when user message count exceeds `CIVICPULSE_SOAPBOX_MAX_TURNS`
- [ ] `POST /soapbox/followup` returns HTTP 503 on LLM error
- [ ] Integration test verifies turn limit enforcement (HTTP 400 on violation)
- [ ] Integration test verifies `{question: str}` response shape on valid input

---

## Phase 5: Soapbox Summary, Review & Submission

**User stories**: 6, 7, 8, 14, 15

### What to build

A `SoapboxPipeline.summarize(messages: list[dict]) -> SoapboxSummary` method that uses `provider.tool_call()` to extract `{summary, topic}` from the conversation. A `POST /soapbox/summarize` endpoint. A `SoapboxLogger` class that wraps the `soapbox_log` write and calls `redact()` on the summary before INSERT. A `POST /soapbox/submit` endpoint that calls `SoapboxLogger` (no LLM call — pure storage). In the frontend: after the user hits "Submit my response", call `/soapbox/summarize` and render the summary in an editable text box; after the user approves (editing freely if needed), call `/soapbox/submit`; show an acknowledgment and return to normal chat.

### Acceptance criteria

- [ ] After hitting "Submit my response", the frontend calls `/soapbox/summarize` and displays the summary in an editable text box
- [ ] The resident can freely edit the summary text before approving
- [ ] Approving the summary calls `/soapbox/submit` with `{summary: str, topic: str}`
- [ ] `soapbox_log` receives a new row containing `summary`, `topic`, and `timestamp`
- [ ] `redact()` is applied to the summary before it is written — a known phone number in the input does not appear in the stored row
- [ ] The raw conversation thread is never written to the database
- [ ] After submission, an acknowledgment message appears and the chat returns to normal mode
- [ ] `POST /soapbox/summarize` returns `{summary: str, topic: str}`; HTTP 503 on LLM error
- [ ] `POST /soapbox/submit` accepts `{summary: str, topic: str}`; HTTP 200 on success (no LLM call in this endpoint)
- [ ] Integration test verifies PII in submitted summary is stripped before storage
- [ ] Integration test verifies `soapbox_log` row is created with correct fields
