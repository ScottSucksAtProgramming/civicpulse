# Plan: Multi-Provider LLM Abstraction

> Source PRD: [GitHub Issue #5 — Multi-Provider LLM Abstraction (nano-gpt / OpenAI-compatible)](https://github.com/ScottSucksAtProgramming/civicpulse/issues/5)

## Architectural decisions

Durable decisions that apply across all phases:

- **Provider subpackage**: All provider code lives in `backend/providers/` — `base.py` (protocol + error), `openai_compat.py`, `anthropic.py`, and an `__init__.py` that re-exports `LLMProvider`, `LLMError`, and a `get_provider` factory. Nothing outside this package imports provider SDK types.
- **`LLMProvider` protocol**: Python `typing.Protocol` with two methods: `complete(messages, model) -> str` and `tool_call(messages, tool_name, tool_schema, model) -> dict`. Any class satisfying these signatures implements the protocol — no inheritance required, making mocks trivial.
- **`LLMError`**: All SDK exceptions are caught inside the provider implementation and re-raised as `LLMError`. The rest of the codebase (`MetadataFilter`, `Synthesizer`, API layer) only ever sees `LLMError` — never `openai.APIError` or `anthropic.APIStatusError`.
- **`tool_call` schema convention**: `tool_schema` is the raw JSON Schema dict for the tool's input parameters only (e.g. `FilterSpec.model_json_schema()`). `tool_name` is passed separately. Each provider wraps these into its native envelope internally — callers never construct provider-specific tool formats.
- **Dependency split**: `openai` is a required dependency. `anthropic` moves to an optional `[anthropic]` extra in `pyproject.toml`. The `AnthropicProvider` lazy-imports the SDK inside its constructor so the module loads cleanly when only `openai` is installed.
- **Single provider for the whole pipeline**: One provider instance is constructed at startup and shared by both `MetadataFilter` and `Synthesizer`. There is no per-role provider selection.
- **Env vars**:
  - `CIVICPULSE_PROVIDER` — `openai-compatible` (default) or `anthropic`
  - `CIVICPULSE_BASE_URL` — base URL for OpenAI-compatible provider (default: `https://api.openai.com/v1`; override to `https://nano-gpt.com/api/v1` for nano-gpt)
  - `CIVICPULSE_API_KEY` — API key for OpenAI-compatible provider
  - `CIVICPULSE_MODEL` — default synthesis model (default: `gpt-4o-mini`)
  - `CIVICPULSE_FILTER_MODEL` — model for MetadataFilter classification (defaults to `CIVICPULSE_MODEL` if unset)
  - `ANTHROPIC_API_KEY` — required only when `CIVICPULSE_PROVIDER=anthropic`

---

## Phase 1: Provider Foundation

**User stories**: 2, 6, 7, 11, 12 — developer can instantiate an OpenAI-compatible provider, call `complete()` and `tool_call()` with mocked HTTP, and confirm the interface is testable in isolation.

### What to build

Define the `LLMProvider` protocol and `LLMError` exception class. Implement `OpenAICompatibleProvider` using the `openai` SDK with constructor-injected `base_url` and `api_key`. It handles `complete()` (standard chat completion → returns assistant message text) and `tool_call()` (sends `tools` in OpenAI format, extracts `tool_calls[0].function.arguments` as a dict). All SDK exceptions are caught and re-raised as `LLMError`.

Add `openai>=1.0` to required dependencies. Move `anthropic` to an optional `[anthropic]` extra. Create the `backend/providers/` subpackage with `__init__.py` re-exporting the public surface.

Write unit tests for `OpenAICompatibleProvider` using mocked HTTP (via `respx` or `unittest.mock`). Assert that `complete()` sends the correct message format and returns the assistant text. Assert that `tool_call()` sends the correct `tools` envelope and returns the parsed arguments dict. Assert that an HTTP error is wrapped and raised as `LLMError`.

Nothing in the existing pipeline is touched in this phase.

### Acceptance criteria

- [x] `backend/providers/` subpackage created with `base.py`, `openai_compat.py`, `__init__.py`
- [x] `LLMProvider` protocol defines `complete(messages, model) -> str` and `tool_call(messages, tool_name, tool_schema, model) -> dict`
- [x] `LLMError` defined in `base.py`; all `OpenAICompatibleProvider` SDK exceptions re-raised as `LLMError`
- [x] `OpenAICompatibleProvider` accepts `base_url` and `api_key` at construction; works with any OpenAI-compatible endpoint
- [x] `openai>=1.0` added to required dependencies in `pyproject.toml`
- [x] `anthropic` moved to optional `[anthropic]` extra in `pyproject.toml`
- [x] Unit test: `complete()` sends correct message format, returns assistant text (mocked HTTP)
- [x] Unit test: `tool_call()` sends correct `tools` array, returns parsed arguments dict (mocked HTTP)
- [x] Unit test: HTTP error → `LLMError` raised (not SDK-specific exception type)

---

## Phase 2: Wire Provider into the Pipeline

**User stories**: 1, 3, 4, 5, 9, 10, 14 — developer can run `POST /query` end-to-end against nano-gpt by setting three env vars; no Anthropic API key required.

### What to build

Update `MetadataFilter` to accept a `LLMProvider` instead of the Anthropic client. Rewrite its internal tool-use call to use `provider.tool_call(messages, tool_name, tool_schema, model)`. The catch-and-fallback logic remains unchanged — it now catches `LLMError` instead of a bare `Exception`.

Update `Synthesizer` to accept a `LLMProvider` instead of the Anthropic client. Rewrite its internal completion call to use `provider.complete(messages, model)`. Error handling remains unchanged — `LLMError` propagates to the API layer as HTTP 503.

Update the FastAPI lifespan factory to read `CIVICPULSE_PROVIDER`, `CIVICPULSE_BASE_URL`, `CIVICPULSE_API_KEY`, and construct an `OpenAICompatibleProvider`. Update `CIVICPULSE_MODEL` default to `gpt-4o-mini`. Inject the provider into `MetadataFilter` and `Synthesizer` via the existing constructor-injection pattern. `QueryPipeline` and `Retriever` are untouched.

Update all existing backend tests: replace Anthropic client mocks with mock `LLMProvider` objects (plain objects satisfying the protocol). Add an end-to-end `POST /query` test wired to a mock `LLMProvider` to confirm the full pipeline produces the correct response shape.

### Acceptance criteria

- [x] `MetadataFilter` accepts `LLMProvider`; uses `provider.tool_call()` with OpenAI-format tool schema; catches `LLMError` for fallback
- [x] `Synthesizer` accepts `LLMProvider`; uses `provider.complete()`; `LLMError` propagates as HTTP 503
- [x] App lifespan constructs `OpenAICompatibleProvider` from `CIVICPULSE_PROVIDER`, `CIVICPULSE_BASE_URL`, `CIVICPULSE_API_KEY`
- [x] Default `CIVICPULSE_MODEL` updated to `gpt-4o-mini`
- [x] All existing backend tests updated to use mock `LLMProvider` (no Anthropic client mocks remain)
- [x] End-to-end test via `TestClient`: `POST /query` → HTTP 200 with `answer` + `sources` (mock provider)
- [x] End-to-end test: provider `LLMError` → HTTP 503
- [ ] Manual verification: `POST /query` with `CIVICPULSE_BASE_URL=https://nano-gpt.com/api/v1` returns a grounded answer

---

## Phase 3: AnthropicProvider + Filter Model + Startup Validation

**User stories**: 8, 13, 15 — Anthropic can be activated via env var if an API key is ever obtained; classification model can be pinned cheaply; misconfiguration is caught at startup with a clear message.

### What to build

Implement `AnthropicProvider` in `backend/providers/anthropic.py`. The `anthropic` SDK is lazy-imported inside the constructor — if the SDK is not installed, the constructor raises a clear `ImportError` with install instructions. Translates `complete()` and `tool_call()` calls into Anthropic's message and tool-use format. All SDK exceptions re-raised as `LLMError`.

Add `AnthropicProvider` to the `get_provider` factory, activated when `CIVICPULSE_PROVIDER=anthropic`. Read `ANTHROPIC_API_KEY` for Anthropic construction.

Add `CIVICPULSE_FILTER_MODEL` env var support in the app lifespan. Pass the resolved filter model to `MetadataFilter` at construction (defaulting to `CIVICPULSE_MODEL` if `CIVICPULSE_FILTER_MODEL` is unset).

Add startup validation: if required env vars for the selected provider are missing (`CIVICPULSE_API_KEY` for OpenAI-compatible, `ANTHROPIC_API_KEY` for Anthropic), raise a `ValueError` at lifespan startup with a descriptive message identifying the missing variable. Invalid `CIVICPULSE_PROVIDER` values also raise with a list of valid options.

Write tests: `AnthropicProvider` with `anthropic` SDK absent raises `ImportError` with instructions. Startup with missing `CIVICPULSE_API_KEY` raises `ValueError` at lifespan. `CIVICPULSE_FILTER_MODEL` override is passed correctly to `MetadataFilter`.

### Acceptance criteria

- [x] `AnthropicProvider` implemented in `backend/providers/anthropic.py`; lazy-imports `anthropic` SDK
- [x] `AnthropicProvider` constructor raises `ImportError` with install instructions when SDK is absent
- [x] `AnthropicProvider` activated by `CIVICPULSE_PROVIDER=anthropic`; reads `ANTHROPIC_API_KEY`
- [x] `AnthropicProvider` translates `complete()` and `tool_call()` to Anthropic format; exceptions wrapped as `LLMError`
- [x] `CIVICPULSE_FILTER_MODEL` env var supported; `MetadataFilter` uses it instead of `CIVICPULSE_MODEL` when set
- [x] Startup validation: missing required API key env var → `ValueError` with descriptive message
- [x] Startup validation: invalid `CIVICPULSE_PROVIDER` value → `ValueError` listing valid options
- [x] Test: `AnthropicProvider` with missing SDK → `ImportError` with instructions
- [x] Test: lifespan startup with missing `CIVICPULSE_API_KEY` → `ValueError` at startup (not at first request)
- [x] Test: `CIVICPULSE_FILTER_MODEL` override flows through to `MetadataFilter`
