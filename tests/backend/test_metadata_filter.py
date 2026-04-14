import logging

from civicpulse.backend.providers import LLMError
from civicpulse.backend.retrieval.metadata_filter import FILTER_MODEL, MetadataFilter
from civicpulse.backend.types import FilterSpec


class StubProvider:
    def __init__(self, *, response=None, error: Exception | None = None):
        self.calls: list[dict] = []
        self._response = response
        self._error = error

    def tool_call(self, *, messages, tool_name, tool_schema, model):
        self.calls.append(
            {
                "messages": messages,
                "tool_name": tool_name,
                "tool_schema": tool_schema,
                "model": model,
            }
        )
        if self._error is not None:
            raise self._error
        return self._response

    def complete(self, *, messages, model):
        raise NotImplementedError


def test_metadata_filter_extracts_document_type_from_tool_use():
    provider = StubProvider(
        response={
            "document_type": "meeting-minutes",
            "date_from": None,
            "date_to": None,
        }
    )

    result = MetadataFilter(provider=provider).classify("Show me meeting minutes")

    assert result == FilterSpec(document_type="meeting-minutes", date_from=None, date_to=None)
    call = provider.calls[0]
    assert call["tool_name"] == "classify_query"
    assert call["model"] == FILTER_MODEL
    assert call["messages"][0]["role"] == "system"
    assert "Today's date is" in call["messages"][0]["content"]
    assert call["messages"][1] == {"role": "user", "content": "Show me meeting minutes"}


def test_metadata_filter_extracts_year_range_from_tool_use():
    provider = StubProvider(
        response={
            "document_type": None,
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        }
    )

    result = MetadataFilter(provider=provider).classify("What happened in 2024?")

    assert result == FilterSpec(
        document_type=None,
        date_from="2024-01-01",
        date_to="2024-12-31",
    )


def test_metadata_filter_returns_empty_filter_for_unfiltered_query():
    provider = StubProvider(
        response={
            "document_type": None,
            "date_from": None,
            "date_to": None,
        }
    )

    result = MetadataFilter(provider=provider).classify("How do I get a permit?")

    assert result == FilterSpec(document_type=None, date_from=None, date_to=None)


def test_metadata_filter_logs_warning_and_falls_back_on_llm_error(caplog):
    provider = StubProvider(error=LLMError("rate limited"))

    with caplog.at_level(logging.WARNING):
        result = MetadataFilter(provider=provider).classify("Show me ordinances from 2024")

    assert result == FilterSpec(document_type=None, date_from=None, date_to=None)
    assert "MetadataFilter failed" in caplog.text


def test_metadata_filter_system_prompt_lists_canonical_document_types():
    template = MetadataFilter._SYSTEM_TEMPLATE
    for doc_type in (
        "agenda", "meeting-minutes", "ordinance", "meeting-video",
        "service-page", "public-meeting", "council", "clerk", "clerk-form",
        "foil", "department-page", "planning",
    ):
        assert doc_type in template
    assert "Today's date is {today}" in template
    assert "clerk-form" in template and "license" in template


def test_metadata_filter_extracts_ordinance_document_type_from_tool_use():
    provider = StubProvider(
        response={
            "document_type": "ordinance",
            "date_from": None,
            "date_to": None,
        }
    )

    result = MetadataFilter(provider=provider).classify("What is the fence height ordinance?")

    assert result == FilterSpec(document_type="ordinance", date_from=None, date_to=None)


def test_metadata_filter_extracts_meeting_video_document_type_from_tool_use():
    provider = StubProvider(
        response={
            "document_type": "meeting-video",
            "date_from": None,
            "date_to": None,
        }
    )

    result = MetadataFilter(provider=provider).classify(
        "What did the town board discuss at the public hearing video?"
    )

    assert result == FilterSpec(document_type="meeting-video", date_from=None, date_to=None)
