import sqlite3
from pathlib import Path

import frontmatter
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
        tool_error: Exception | None = None,
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
        self._tool_error = tool_error
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
        if self._tool_error is not None:
            raise self._tool_error
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


def read_draft_log_rows(vault: Path) -> list[sqlite3.Row]:
    con = sqlite3.connect(vault / ".index.db")
    con.row_factory = sqlite3.Row
    try:
        return list(
            con.execute(
                """
                SELECT recipient, topic, abstracted_concern, timestamp
                FROM draft_log
                ORDER BY rowid
                """
            )
        )
    finally:
        con.close()


def read_table_names(vault: Path) -> set[str]:
    con = sqlite3.connect(vault / ".index.db")
    try:
        return {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        con.close()


def read_query_log_rows(vault: Path) -> list[sqlite3.Row]:
    con = sqlite3.connect(vault / ".index.db")
    con.row_factory = sqlite3.Row
    try:
        return list(
            con.execute(
                """
                SELECT id, document_type, timestamp
                FROM query_log
                ORDER BY id
                """
            )
        )
    finally:
        con.close()


def read_soapbox_log_rows(vault: Path) -> list[sqlite3.Row]:
    con = sqlite3.connect(vault / ".index.db")
    con.row_factory = sqlite3.Row
    try:
        return list(
            con.execute(
                """
                SELECT id, summary, topic, timestamp
                FROM soapbox_log
                ORDER BY id
                """
            )
        )
    finally:
        con.close()


def test_privacy_policy_document_has_valid_frontmatter():
    policy_path = Path("vault/privacy/privacy-policy.md")

    assert policy_path.exists()
    post = frontmatter.load(policy_path)
    assert post.metadata["document_type"] == "privacy"
    assert post.metadata["date"]
    assert post.metadata["title"]
    assert post.metadata["source_url"]
    assert "what data CivicPulse collect" in post.content


def test_privacy_policy_document_is_retrievable_by_bm25(tmp_path):
    policy_dir = tmp_path / "privacy"
    policy_dir.mkdir()
    policy_text = Path("vault/privacy/privacy-policy.md").read_text()
    (policy_dir / "privacy-policy.md").write_text(policy_text)
    FTSIndexer(tmp_path).index()

    results = FTSIndexer(tmp_path).query("what data CivicPulse collect", top_n=1)

    assert len(results) == 1
    assert results[0].document_type == "privacy"
    assert results[0].title == "CivicPulse Privacy Policy"


def test_post_query_can_cite_privacy_policy_document(tmp_path, monkeypatch):
    policy_dir = tmp_path / "privacy"
    policy_dir.mkdir()
    policy_text = Path("vault/privacy/privacy-policy.md").read_text()
    (policy_dir / "privacy-policy.md").write_text(policy_text)
    FTSIndexer(tmp_path).index()
    provider = StubProvider(
        tool_result={
            "document_type": "privacy",
            "date_from": None,
            "date_to": None,
        },
        completion_text="CivicPulse collects anonymous question text and aggregate logs. [1]",
    )

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post("/query", json={"question": "what data does CivicPulse collect?"})

    assert response.status_code == 200
    assert response.json()["sources"] == [
        {
            "title": "CivicPulse Privacy Policy",
            "url": "/privacy.html",
            "document_type": "privacy",
            "date": "2026-04-22",
        }
    ]


def test_create_app_serves_privacy_page(tmp_path, monkeypatch):
    with build_test_client(tmp_path, monkeypatch) as client:
        response = client.get("/privacy.html")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CivicPulse Privacy Policy" in response.text


def test_frontend_privacy_disclaimer_links_to_privacy_page():
    html = Path("frontend/index.html").read_text()

    assert 'href="/privacy.html"' in html


def test_frontend_includes_soapbox_card_and_separate_state():
    html = Path("frontend/index.html").read_text()

    assert "Share Your Voice" in html
    assert "soapboxStep" in html
    assert "startSoapboxFlow" in html


def test_frontend_includes_soapbox_summary_review_flow():
    html = Path("frontend/index.html").read_text()

    assert "/soapbox/summarize" in html
    assert "/soapbox/submit" in html
    assert "soapboxSummary" in html
    assert "Approve summary" in html
    assert "textarea" in html


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


def test_create_app_creates_anonymous_log_tables(tmp_path, monkeypatch):
    with build_test_client(tmp_path, monkeypatch):
        pass

    table_names = read_table_names(tmp_path)
    assert "query_log" in table_names
    assert "soapbox_log" in table_names


def test_post_query_logs_document_type_without_question_text(tmp_path, monkeypatch):
    write_chunk(
        tmp_path,
        content="The town board approved the zoning variance after public comment.",
        source_url="https://www.townofbabylonny.gov/zoning",
        document_type="meeting-minutes",
        date="2026-02-10",
        title="Town Board Minutes",
        slug="town-board-minutes-0",
    )
    FTSIndexer(tmp_path).index()
    provider = StubProvider(
        tool_result={
            "document_type": "meeting-minutes",
            "date_from": None,
            "date_to": None,
        },
        completion_text="The variance was approved. [1]",
    )
    question = "What happened to the secret zoning variance?"

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post("/query", json={"question": question})

    assert response.status_code == 200
    rows = read_query_log_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["document_type"] == "meeting-minutes"
    assert rows[0]["timestamp"]
    assert set(rows[0].keys()) == {"id", "document_type", "timestamp"}
    assert question not in str(dict(rows[0]))
    assert len(provider.tool_calls) == 1


def test_post_query_logs_null_document_type_when_metadata_filter_falls_back(
    tmp_path, monkeypatch
):
    provider = StubProvider(completion_text="No matching content.")

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post("/query", json={"question": "What is the ferry schedule?"})

    assert response.status_code == 200
    rows = read_query_log_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["document_type"] is None


def test_post_soapbox_followup_returns_question_shape(tmp_path, monkeypatch):
    provider = StubProvider(completion_text="What change would you like to see next?")

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/soapbox/followup",
            json={"messages": [{"role": "user", "content": "The park needs more lighting."}]},
        )

    assert response.status_code == 200
    assert response.json() == {"question": "What change would you like to see next?"}
    assert provider.completion_calls[0]["messages"][0]["role"] == "system"
    assert "non-leading" in provider.completion_calls[0]["messages"][0]["content"]


def test_post_soapbox_followup_uses_soapbox_model_defaulting_to_civicpulse_model(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("CIVICPULSE_MODEL", "default-civic-model")
    provider = StubProvider(completion_text="What would help residents feel heard?")

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/soapbox/followup",
            json={"messages": [{"role": "user", "content": "Meetings feel inaccessible."}]},
        )

    assert response.status_code == 200
    assert provider.completion_calls[0]["model"] == "default-civic-model"


def test_post_soapbox_followup_returns_400_when_turn_limit_exceeded(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("CIVICPULSE_SOAPBOX_MAX_TURNS", "1")

    with build_test_client(tmp_path, monkeypatch) as client:
        response = client.post(
            "/soapbox/followup",
            json={
                "messages": [
                    {"role": "user", "content": "First concern."},
                    {"role": "assistant", "content": "Can you say more?"},
                    {"role": "user", "content": "Second concern."},
                ]
            },
        )

    assert response.status_code == 400


def test_post_soapbox_followup_returns_503_when_provider_raises_llm_error(
    tmp_path, monkeypatch
):
    provider = StubProvider(completion_error=LLMError("upstream failure"))

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/soapbox/followup",
            json={"messages": [{"role": "user", "content": "The town needs safer crossings."}]},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "CivicPulse could not generate an answer right now. Please try again shortly."
    }


def test_post_soapbox_summarize_returns_summary_and_topic(tmp_path, monkeypatch):
    provider = StubProvider(
        tool_result={
            "summary": "A resident wants safer crossings near schools.",
            "topic": "street safety",
        }
    )

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/soapbox/summarize",
            json={"messages": [{"role": "user", "content": "Crosswalks feel unsafe."}]},
        )

    assert response.status_code == 200
    assert response.json() == {
        "summary": "A resident wants safer crossings near schools.",
        "topic": "street safety",
    }
    assert provider.tool_calls[0]["tool_name"] == "summarize_soapbox"


def test_post_soapbox_summarize_returns_503_when_provider_raises_llm_error(
    tmp_path, monkeypatch
):
    provider = StubProvider(tool_error=LLMError("upstream failure"))

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/soapbox/summarize",
            json={"messages": [{"role": "user", "content": "Crosswalks feel unsafe."}]},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "CivicPulse could not generate an answer right now. Please try again shortly."
    }


def test_post_soapbox_submit_logs_summary_topic_and_redacts_pii_without_llm_call(
    tmp_path, monkeypatch
):
    provider = StubProvider()

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/soapbox/submit",
            json={
                "summary": "A resident at (631) 555-1212 wants safer crossings.",
                "topic": "street safety",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    rows = read_soapbox_log_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["summary"] == "A resident at [REDACTED] wants safer crossings."
    assert rows[0]["topic"] == "street safety"
    assert rows[0]["timestamp"]
    assert "(631) 555-1212" not in rows[0]["summary"]
    assert provider.tool_calls == []
    assert provider.completion_calls == []


def test_post_draft_suggest_recipient_returns_classification_and_logs_aggregate_record(
    tmp_path, monkeypatch
):
    provider = StubProvider(
        tool_result={
            "suggested_recipient": "Planning Board",
            "topic": "zoning",
            "abstracted_concern": "A resident is concerned about a proposed zoning change.",
        }
    )

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/draft/suggest-recipient",
            json={"concern": "My neighbor wants to build a huge addition next to my house."},
        )

    assert response.status_code == 200
    assert response.json() == {
        "suggested_recipient": "Planning Board",
        "topic": "zoning",
        "abstracted_concern": "A resident is concerned about a proposed zoning change.",
    }
    assert provider.tool_calls[0]["tool_name"] == "classify_recipient"
    rows = read_draft_log_rows(tmp_path)
    assert len(rows) == 1
    assert dict(rows[0]) == {
        "recipient": "Planning Board",
        "topic": "zoning",
        "abstracted_concern": "A resident is concerned about a proposed zoning change.",
        "timestamp": rows[0]["timestamp"],
    }
    assert "neighbor wants to build" not in rows[0]["abstracted_concern"]


def test_post_draft_suggest_recipient_redacts_phone_number_before_logging(
    tmp_path, monkeypatch
):
    provider = StubProvider(
        tool_result={
            "suggested_recipient": "Planning Board",
            "topic": "zoning",
            "abstracted_concern": "A resident at (631) 555-1212 is concerned about zoning.",
        }
    )

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/draft/suggest-recipient",
            json={"concern": "My phone is (631) 555-1212 and I have a zoning concern."},
        )

    assert response.status_code == 200
    rows = read_draft_log_rows(tmp_path)
    assert len(rows) == 1
    assert "(631) 555-1212" not in rows[0]["abstracted_concern"]
    assert rows[0]["abstracted_concern"] == (
        "A resident at [REDACTED] is concerned about zoning."
    )


def test_post_draft_suggest_recipient_returns_503_when_provider_raises_llm_error(
    tmp_path, monkeypatch
):
    provider = StubProvider(tool_error=LLMError("upstream failure"))

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/draft/suggest-recipient",
            json={"concern": "I am worried about a rezoning proposal."},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "CivicPulse could not generate an answer right now. Please try again shortly."
    }


def test_post_draft_generate_returns_letter_and_sources_when_retrieval_hits(
    tmp_path, monkeypatch
):
    write_chunk(
        tmp_path,
        content="The town board discussed a zoning amendment affecting setback rules.",
        source_url="https://www.townofbabylonny.gov/zoning-amendment",
        document_type="meeting-minutes",
        date="2026-03-10",
        title="Town Board Minutes",
        slug="town-board-minutes-0",
    )
    FTSIndexer(tmp_path).index()
    provider = StubProvider(completion_text="Draft letter referencing the recent amendment. [1]")

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/draft/generate",
            json={
                "concern": "I am concerned about the zoning amendment.",
                "outcome": "I want the board to reconsider it.",
                "tone": "Formal",
                "recipient": "Town Board",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "letter": "Draft letter referencing the recent amendment. [1]",
        "sources": [
            {
                "title": "Town Board Minutes",
                "url": "https://www.townofbabylonny.gov/zoning-amendment",
                "document_type": "meeting-minutes",
                "date": "2026-03-10",
            }
        ],
    }


def test_post_draft_generate_returns_letter_with_empty_sources_when_no_retrieval_hits(
    tmp_path, monkeypatch
):
    provider = StubProvider(completion_text="Draft letter without retrieved sources.")

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/draft/generate",
            json={
                "concern": "I am concerned about a neighborhood issue.",
                "outcome": "I want follow-up from the town.",
                "tone": "Friendly",
                "recipient": "Department",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "letter": "Draft letter without retrieved sources.",
        "sources": [],
    }


def test_post_draft_generate_returns_503_when_provider_raises_llm_error(
    tmp_path, monkeypatch
):
    provider = StubProvider(completion_error=LLMError("upstream failure"))

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/draft/generate",
            json={
                "concern": "I am concerned about a zoning change.",
                "outcome": "I want more review.",
                "tone": "Firm",
                "recipient": "Planning Board",
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "CivicPulse could not generate an answer right now. Please try again shortly."
    }


def test_post_draft_revise_returns_revised_letter(tmp_path, monkeypatch):
    provider = StubProvider(
        completion_text=(
            "Dear Planning Board,\n\nPlease defer a vote until the traffic study is "
            "complete.\n\nSincerely,\nA Resident"
        )
    )

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/draft/revise",
            json={
                "current_letter": (
                    "Dear Planning Board,\n\nPlease review this matter.\n\nSincerely,\nA Resident"
                ),
                "revision_request": "Make it more specific and mention the traffic study.",
                "concern": "I am concerned about traffic impacts.",
                "recipient": "Planning Board",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "letter": (
            "Dear Planning Board,\n\nPlease defer a vote until the traffic study is "
            "complete.\n\nSincerely,\nA Resident"
        )
    }
    assert response.json()["letter"] != (
        "Dear Planning Board,\n\nPlease review this matter.\n\nSincerely,\nA Resident"
    )


def test_post_draft_revise_returns_503_when_provider_raises_llm_error(
    tmp_path, monkeypatch
):
    provider = StubProvider(completion_error=LLMError("upstream failure"))

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/draft/revise",
            json={
                "current_letter": "Current draft",
                "revision_request": "Shorten it.",
                "concern": "I am concerned about a zoning change.",
                "recipient": "Planning Board",
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "CivicPulse could not generate an answer right now. Please try again shortly."
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


def test_post_query_includes_letter_drafting_redirect_in_synthesizer_prompt(
    tmp_path, monkeypatch
):
    write_chunk(
        tmp_path,
        content=(
            "Residents can contact the planning board representative about zoning "
            "applications and related review requests."
        ),
        source_url="https://www.townofbabylonny.gov/planning",
        document_type="planning",
        date="2026-03-10",
        title="Planning Board Overview",
        slug="planning-board-overview-0",
    )
    FTSIndexer(tmp_path).index()
    provider = StubProvider()

    with build_test_client(tmp_path, monkeypatch, provider=provider) as client:
        response = client.post(
            "/query",
            json={"question": "I want to write a letter to my representative"},
        )

    assert response.status_code == 200
    assert (
        "Contact a Representative" in provider.completion_calls[0]["messages"][0]["content"]
    )


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


def test_create_app_serves_frontend_index_from_root(tmp_path, monkeypatch):
    with build_test_client(tmp_path, monkeypatch) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CivicPulse" in response.text
    assert "Ask me anything about Town of Babylon government" in response.text


def test_create_app_serves_frontend_assets_from_absolute_path(tmp_path, monkeypatch):
    original_cwd = Path.cwd()
    monkeypatch.chdir(tmp_path)

    try:
        with build_test_client(tmp_path, monkeypatch) as client:
            response = client.get("/styles.css")
    finally:
        monkeypatch.chdir(original_cwd)

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


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
