from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from civicpulse.backend.api.app import create_app
from civicpulse.backend.providers import LLMError
from civicpulse.scraper.indexer import FTSIndexer
from civicpulse.scraper.models import VaultChunk
from civicpulse.scraper.writer import VaultWriter


def write_chunk(vault: Path, **kwargs) -> Path:
    defaults = dict(
        content="General civic content",
        source_url="https://www.townofbabylonny.gov/default",
        document_type="service-page",
        date="2026-01-01",
        meeting_id=None,
        title="Default Title",
        chunk_index=0,
        slug="default-title-0",
    )
    return VaultWriter(vault).write(VaultChunk(**{**defaults, **kwargs}))


class StubProvider:
    def __init__(
        self,
        *,
        tool_result: dict | None = None,
        completion_text: str | None = None,
        completion_error: Exception | None = None,
    ) -> None:
        self.tool_calls: list[dict] = []
        self.completion_calls: list[dict] = []
        self._tool_result = tool_result or {
            "document_type": None,
            "date_from": None,
            "date_to": None,
        }
        self._completion_text = completion_text or "Grounded answer. [1]"
        self._completion_error = completion_error

    def tool_call(self, *, messages, tool_name, tool_schema, model):
        self.tool_calls.append(
            {
                "messages": messages,
                "tool_name": tool_name,
                "tool_schema": tool_schema,
                "model": model,
            }
        )
        return self._tool_result

    def complete(self, *, messages, model):
        self.completion_calls.append(
            {
                "messages": messages,
                "model": model,
            }
        )
        if self._completion_error is not None:
            raise self._completion_error
        return self._completion_text


def build_test_client(
    vault: Path,
    monkeypatch,
    provider: StubProvider | None = None,
    top_n: int | None = None,
) -> TestClient:
    if top_n is None:
        monkeypatch.delenv("CIVICPULSE_TOP_N", raising=False)
    else:
        monkeypatch.setenv("CIVICPULSE_TOP_N", str(top_n))

    monkeypatch.setenv("CIVICPULSE_PROVIDER", "openai-compatible")
    monkeypatch.setenv("CIVICPULSE_API_KEY", "test-key")
    monkeypatch.delenv("CIVICPULSE_BASE_URL", raising=False)
    monkeypatch.setattr(
        "civicpulse.backend.api.app.get_provider",
        lambda: provider or StubProvider(),
    )
    return TestClient(create_app(vault_path=vault))


def test_post_query_returns_grounded_answer_and_sources(tmp_path, monkeypatch):
    write_chunk(
        tmp_path,
        content="The zoning variance was approved by the town board.",
        source_url="https://www.townofbabylonny.gov/zoning",
        document_type="meeting-minutes",
        date="2026-02-10",
        title="Town Board Minutes",
        slug="town-board-minutes-0",
    )
    write_chunk(
        tmp_path,
        content="The capital budget was adopted for the fiscal year.",
        source_url="https://www.townofbabylonny.gov/budget",
        document_type="budget",
        date="2026-03-11",
        title="Budget Adoption",
        chunk_index=1,
        slug="budget-adoption-1",
    )
    FTSIndexer(tmp_path).index()

    with build_test_client(tmp_path, monkeypatch) as client:
        response = client.post("/query", json={"question": "zoning"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Grounded answer. [1]",
        "sources": [
            {
                "title": "Town Board Minutes",
                "url": "https://www.townofbabylonny.gov/zoning",
                "document_type": "meeting-minutes",
                "date": "2026-02-10",
            }
        ],
    }


def test_post_query_respects_top_n_env_var(tmp_path, monkeypatch):
    for chunk_index in range(3):
        write_chunk(
            tmp_path,
            content=f"Recycling schedule update {chunk_index}",
            source_url=f"https://www.townofbabylonny.gov/recycling/{chunk_index}",
            title=f"Recycling Update {chunk_index}",
            chunk_index=chunk_index,
            slug=f"recycling-update-{chunk_index}",
        )
    FTSIndexer(tmp_path).index()

    provider = StubProvider(completion_text="Grounded answer without explicit citations.")
    with build_test_client(tmp_path, monkeypatch, provider=provider, top_n=2) as client:
        response = client.post("/query", json={"question": "recycling"})

    body = response.json()
    assert response.status_code == 200
    assert body["answer"] == "Grounded answer without explicit citations."
    assert len(body["sources"]) == 2


def test_post_query_runs_pipeline_with_single_provider(tmp_path, monkeypatch):
    write_chunk(
        tmp_path,
        content="The town board approved the zoning variance after public comment.",
        source_url="https://www.townofbabylonny.gov/zoning",
        document_type="meeting-minutes",
        date="2026-02-10",
        title="Town Board Minutes",
        slug="town-board-minutes-0",
    )
    write_chunk(
        tmp_path,
        content="The capital budget hearing is scheduled for next month.",
        source_url="https://www.townofbabylonny.gov/budget",
        document_type="budget",
        date="2026-03-11",
        title="Budget Hearing",
        chunk_index=1,
        slug="budget-hearing-1",
    )
    FTSIndexer(tmp_path).index()
    provider = StubProvider(completion_text="The variance was approved after public comment. [1]")

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post("/query", json={"question": "What happened to the zoning variance?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "The variance was approved after public comment. [1]",
        "sources": [
            {
                "title": "Town Board Minutes",
                "url": "https://www.townofbabylonny.gov/zoning",
                "document_type": "meeting-minutes",
                "date": "2026-02-10",
            }
        ],
    }
    assert len(provider.tool_calls) == 1
    assert len(provider.completion_calls) == 1


def test_post_query_returns_no_content_fallback_without_completion_call(tmp_path, monkeypatch):
    provider = StubProvider(completion_text="Should not be used")

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post("/query", json={"question": "What is the ferry schedule?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": (
            "I couldn't find relevant Town of Babylon content for that question. "
            "Please check the official website at https://www.townofbabylonny.gov "
            "for the latest information."
        ),
        "sources": [],
    }
    assert len(provider.tool_calls) == 1
    assert provider.completion_calls == []


def test_post_query_returns_503_when_provider_raises_llm_error(tmp_path, monkeypatch):
    write_chunk(
        tmp_path,
        content="The zoning variance was approved by the town board.",
        source_url="https://www.townofbabylonny.gov/zoning",
        document_type="meeting-minutes",
        date="2026-02-10",
        title="Town Board Minutes",
        slug="town-board-minutes-0",
    )
    FTSIndexer(tmp_path).index()
    provider = StubProvider(completion_error=LLMError("upstream failure"))

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post("/query", json={"question": "What happened to zoning?"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "CivicPulse could not generate an answer right now. Please try again shortly."
    }


def test_post_query_uses_request_model_override_for_synthesis(tmp_path, monkeypatch):
    write_chunk(
        tmp_path,
        content="The zoning variance was approved by the town board.",
        source_url="https://www.townofbabylonny.gov/zoning",
        document_type="meeting-minutes",
        date="2026-02-10",
        title="Town Board Minutes",
        slug="town-board-minutes-0",
    )
    FTSIndexer(tmp_path).index()
    provider = StubProvider()

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/query",
            json={
                "question": "What happened to zoning?",
                "model": "gpt-4.1-mini",
            },
        )

    assert response.status_code == 200
    assert provider.completion_calls[0]["model"] == "gpt-4.1-mini"
    assert provider.tool_calls[0]["model"] == "gpt-4o-mini"


def test_post_query_uses_env_default_model_when_request_omits_model(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVICPULSE_MODEL", "gpt-4.1-mini")
    write_chunk(
        tmp_path,
        content="The zoning variance was approved by the town board.",
        source_url="https://www.townofbabylonny.gov/zoning",
        document_type="meeting-minutes",
        date="2026-02-10",
        title="Town Board Minutes",
        slug="town-board-minutes-0",
    )
    FTSIndexer(tmp_path).index()
    provider = StubProvider()

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post("/query", json={"question": "What happened to zoning?"})

    assert response.status_code == 200
    assert provider.completion_calls[0]["model"] == "gpt-4.1-mini"


def test_create_app_raises_clear_error_for_invalid_top_n(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVICPULSE_PROVIDER", "openai-compatible")
    monkeypatch.setenv("CIVICPULSE_API_KEY", "test-key")
    monkeypatch.setenv("CIVICPULSE_TOP_N", "not-an-int")
    monkeypatch.setattr("civicpulse.backend.api.app.get_provider", lambda: StubProvider())
    app = create_app(vault_path=tmp_path)

    with pytest.raises(ValueError, match="CIVICPULSE_TOP_N must be an integer"):
        with TestClient(app):
            pass


def test_create_app_raises_when_openai_compatible_api_key_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVICPULSE_PROVIDER", "openai-compatible")
    monkeypatch.delenv("CIVICPULSE_API_KEY", raising=False)
    app = create_app(vault_path=tmp_path)

    with pytest.raises(ValueError, match="CIVICPULSE_API_KEY"):
        with TestClient(app):
            pass


def test_create_app_raises_for_invalid_provider_value(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVICPULSE_PROVIDER", "not-a-provider")
    app = create_app(vault_path=tmp_path)

    with pytest.raises(ValueError, match="openai-compatible|anthropic"):
        with TestClient(app):
            pass


def test_create_app_passes_filter_model_override_to_metadata_filter(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVICPULSE_PROVIDER", "openai-compatible")
    monkeypatch.setenv("CIVICPULSE_API_KEY", "test-key")
    monkeypatch.setenv("CIVICPULSE_FILTER_MODEL", "gpt-4.1-nano")
    monkeypatch.setattr("civicpulse.backend.api.app.get_provider", lambda: StubProvider())
    app = create_app(vault_path=tmp_path)

    with TestClient(app):
        assert app.state.pipeline._metadata_filter._model == "gpt-4.1-nano"
