import importlib
from types import SimpleNamespace

import pytest

from civicpulse.backend.providers import LLMError
from civicpulse.backend.providers.anthropic import AnthropicProvider


class FakeAPIStatusError(Exception):
    pass


class FakeAnthropicModule:
    APIError = FakeAPIStatusError
    APIStatusError = FakeAPIStatusError
    APIConnectionError = FakeAPIStatusError

    class Anthropic:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key


def test_anthropic_provider_raises_import_error_with_install_instructions(monkeypatch):
    real_import_module = importlib.import_module

    def fake_import_module(name, package=None):
        if name == "anthropic":
            raise ImportError("No module named 'anthropic'")
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    with pytest.raises(ImportError, match="pip install 'civicpulse\\[anthropic\\]'"):
        AnthropicProvider(api_key="test-key")


def test_anthropic_provider_complete_translates_system_message(monkeypatch):
    monkeypatch.setattr(importlib, "import_module", lambda name, package=None: FakeAnthropicModule)
    client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(
                call=kwargs,
                content=[SimpleNamespace(type="text", text="Grounded answer.")],
            )
        )
    )

    provider = AnthropicProvider(api_key="test-key", client=client)
    messages = [
        {"role": "system", "content": "Answer from sources only."},
        {"role": "user", "content": "What happened?"},
    ]

    result = provider.complete(messages=messages, model="claude-3-5-haiku-latest")

    assert result == "Grounded answer."


def test_anthropic_provider_tool_call_translates_tools(monkeypatch):
    monkeypatch.setattr(importlib, "import_module", lambda name, package=None: FakeAnthropicModule)
    captured: dict = {}

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    name="classify_query",
                    input={"document_type": "meeting-minutes", "date_from": None, "date_to": None},
                )
            ]
        )

    client = SimpleNamespace(messages=SimpleNamespace(create=create))

    provider = AnthropicProvider(api_key="test-key", client=client)
    result = provider.tool_call(
        messages=[{"role": "user", "content": "Show me meeting minutes"}],
        tool_name="classify_query",
        tool_schema={"type": "object", "properties": {}},
        model="claude-3-5-haiku-latest",
    )

    assert result == {"document_type": "meeting-minutes", "date_from": None, "date_to": None}
    assert captured["tools"] == [
        {
            "name": "classify_query",
            "input_schema": {"type": "object", "properties": {}},
        }
    ]
    assert captured["tool_choice"] == {"type": "tool", "name": "classify_query"}


def test_anthropic_provider_wraps_sdk_errors_as_llm_error(monkeypatch):
    monkeypatch.setattr(importlib, "import_module", lambda name, package=None: FakeAnthropicModule)
    client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **kwargs: (_ for _ in ()).throw(FakeAPIStatusError("rate limited"))
        )
    )

    provider = AnthropicProvider(api_key="test-key", client=client)

    with pytest.raises(LLMError):
        provider.complete(
            messages=[{"role": "user", "content": "What happened?"}],
            model="claude-3-5-haiku-latest",
        )
