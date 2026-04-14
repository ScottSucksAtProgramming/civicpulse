# CivicPulse

A conversational AI agent that helps Town of Babylon, NY residents understand and engage with their local government.

CivicPulse answers plain-language questions about bills, ordinances, meeting agendas, zoning decisions, local services, and civic processes — all grounded in retrieved official documents, never LLM training data. It also helps residents draft letters to their elected representatives.

**It informs without agenda. It never tells you what to think or how to vote.**

---

## Features

- **Civic Q&A** — Ask about town board votes, budgets, zoning, public hearings, and more. Every answer cites its source.
- **Plain-language document explainer** — Breaks down legal and bureaucratic language from official government documents.
- **Local services finder** — Helps residents discover financial assistance, adult education, community events, permits, and more.
- **Letter drafting assistant** — Guides residents through drafting personalized communications to elected officials.
- **Civic education** — Explains how local government works: how bills pass, how to attend hearings, how to file a FOIL request.
- **Anonymous aggregate insights** — Conversation topics are logged (never personal data) to surface what issues matter most to the community.

## How It Works

1. **Scraper** — Nightly jobs pull content from `townofbabylonny.gov`, Agenda Center, eCode360, Town Clerk documents, and YouTube meeting transcripts via the YouTube Data API.
2. **Knowledge vault** — Content is chunked into structured Markdown files with YAML frontmatter (`source_url`, `document_type`, `date`, `chunk_index`) and stored in a hierarchical vault directory. No vector database required.
3. **Retrieval pipeline** — On each query:
   - LLM extracts metadata filters (date range, document type) from the question
   - BM25 keyword search (SQLite FTS5) retrieves top-N candidate chunks
   - LLM re-ranks and synthesizes a grounded response with numbered source citations
4. **Backend API** — FastAPI app orchestrates the pipeline. Supports Anthropic and any OpenAI-compatible provider.
5. **Frontend** — Mobile-friendly web chat, no login required. *(In development)*

## Privacy

Privacy is non-negotiable:

- No names, email addresses, phone numbers, IP addresses, or device identifiers are collected or stored.
- If a user volunteers personal information in conversation, it is used only within that session and never stored.
- All conversation logs pass through a PII redaction pipeline before any storage.
- Only anonymized topics and themes are retained for aggregate analysis.

CivicPulse is an independent tool, not affiliated with or endorsed by the Town of Babylon.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13+ |
| Backend | FastAPI + Uvicorn |
| Search | SQLite FTS5 (BM25) |
| LLM | Claude Haiku (default) / Claude Sonnet (complex) via Anthropic API |
| Alt provider | Any OpenAI-compatible API |
| Scraping | httpx, BeautifulSoup4, pdfplumber |
| Storage | Markdown files with YAML frontmatter (no vector DB) |

## Setup

**Requirements:** Python 3.13+, `uv`

```bash
git clone <repo>
cd civicpulse

# Install dependencies
uv sync --extra anthropic

# Configure environment
cp .env.example .env
# Edit .env with your API key and settings
```

### Environment Variables

```
CIVICPULSE_PROVIDER=anthropic          # "anthropic" or "openai-compatible"
ANTHROPIC_API_KEY=sk-ant-...           # Required for Anthropic provider
CIVICPULSE_MODEL=claude-haiku-4-5-...  # Model for response generation
CIVICPULSE_FILTER_MODEL=...            # Model for metadata filtering (defaults to CIVICPULSE_MODEL)
CIVICPULSE_TOP_N=5                     # Number of chunks returned by BM25 search
CIVICPULSE_VAULT_PATH=./vault          # Path to the knowledge vault
```

### Run the API

```bash
uvicorn civicpulse.backend.api:create_app --factory --reload
```

### Run the Scraper

```bash
civicpulse-scrape
```

### Run Tests

```bash
uv run pytest
```

## Project Status

- Phase 1 (Pilot): Core scraper and RAG pipeline complete. Frontend in development.
- Phase 2: Hallucination monitoring, qualitative feedback, open-source model evaluation.
- Phase 3: Expansion to additional Long Island municipalities.

## Data Sources

| Source | Content |
|---|---|
| townofbabylonny.gov | Official town website, departments, services |
| Agenda Center | Town Board, Planning Board, Zoning Board agendas and minutes |
| eCode360 | Town code, ordinances, and zoning laws |
| YouTube (Town channel) | Meeting recordings and auto-generated transcripts |
| Town Clerk | Forms, documents, FOIL resources |
