from types import SimpleNamespace
from unittest.mock import Mock

import openai
import pytest

from civicpulse.backend.providers import LLMError, OpenAICompatibleProvider


def test_complete_returns_assistant_text_and_passes_messages():
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="Grounded answer."),
            )
        ]
    )

    provider = OpenAICompatibleProvider(
        base_url="https://nano-gpt.com/api/v1",
        api_key="test-key",
        client=client,
    )
    messages = [{"role": "user", "content": "What happened at the meeting?"}]

    result = provider.complete(messages=messages, model="gpt-4o-mini")

    assert result == "Grounded answer."
    client.chat.completions.create.assert_called_once_with(
        model="gpt-4o-mini",
        messages=messages,
    )


def test_tool_call_wraps_schema_and_returns_parsed_arguments():
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(
                            function=SimpleNamespace(
                                arguments='{"document_type":"meeting-minutes","date_from":null,"date_to":null}'
                            )
                        )
                    ]
                )
            )
        ]
    )

    provider = OpenAICompatibleProvider(
        base_url="https://nano-gpt.com/api/v1",
        api_key="test-key",
        client=client,
    )
    messages = [{"role": "user", "content": "Show me meeting minutes"}]
    schema = {
        "type": "object",
        "properties": {
            "document_type": {"type": ["string", "null"]},
            "date_from": {"type": ["string", "null"]},
            "date_to": {"type": ["string", "null"]},
        },
    }

    result = provider.tool_call(
        messages=messages,
        tool_name="classify_query",
        tool_schema=schema,
        model="gpt-4o-mini",
    )

    assert result == {
        "document_type": "meeting-minutes",
        "date_from": None,
        "date_to": None,
    }
    client.chat.completions.create.assert_called_once_with(
        model="gpt-4o-mini",
        messages=messages,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "classify_query",
                    "parameters": schema,
                },
            }
        ],
        tool_choice={
            "type": "function",
            "function": {"name": "classify_query"},
        },
    )


def test_complete_wraps_openai_errors_as_llm_error():
    client = Mock()
    request = Mock()
    client.chat.completions.create.side_effect = openai.APIConnectionError(request=request)

    provider = OpenAICompatibleProvider(
        base_url="https://nano-gpt.com/api/v1",
        api_key="test-key",
        client=client,
    )

    with pytest.raises(LLMError):
        provider.complete(
            messages=[{"role": "user", "content": "What happened?"}],
            model="gpt-4o-mini",
        )
