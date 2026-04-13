import importlib
from typing import Any

from civicpulse.backend.providers.base import LLMError, LLMProvider, Message


class AnthropicProvider(LLMProvider):
    def __init__(self, *, api_key: str, client: Any | None = None) -> None:
        try:
            anthropic_module = importlib.import_module("anthropic")
        except ImportError as exc:
            raise ImportError(
                "Anthropic support is not installed. Install it with "
                "\"pip install 'civicpulse[anthropic]'\"."
            ) from exc

        self._anthropic = anthropic_module
        self._client = client or anthropic_module.Anthropic(api_key=api_key)

    def complete(self, messages: list[Message], model: str) -> str:
        system, anthropic_messages = self._split_system_message(messages)

        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=500,
                system=system,
                messages=anthropic_messages,
            )
            text_parts = [
                block.text
                for block in getattr(response, "content", [])
                if getattr(block, "type", None) == "text" and getattr(block, "text", None)
            ]
            return "\n".join(text_parts).strip()
        except self._sdk_error_types() as exc:
            raise LLMError("Anthropic completion failed") from exc
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            raise LLMError("Anthropic completion returned an invalid response") from exc

    def tool_call(
        self,
        messages: list[Message],
        tool_name: str,
        tool_schema: dict[str, Any],
        model: str,
    ) -> dict[str, Any]:
        system, anthropic_messages = self._split_system_message(messages)

        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=200,
                system=system,
                messages=anthropic_messages,
                tools=[
                    {
                        "name": tool_name,
                        "input_schema": tool_schema,
                    }
                ],
                tool_choice={"type": "tool", "name": tool_name},
            )
            for block in getattr(response, "content", []):
                if (
                    getattr(block, "type", None) == "tool_use"
                    and getattr(block, "name", None) == tool_name
                ):
                    return dict(getattr(block, "input", {}))
            raise ValueError(f"Tool {tool_name} was not returned")
        except self._sdk_error_types() as exc:
            raise LLMError("Anthropic tool call failed") from exc
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            raise LLMError("Anthropic tool call returned an invalid response") from exc

    def _split_system_message(self, messages: list[Message]) -> tuple[str | None, list[Message]]:
        system_parts: list[str] = []
        anthropic_messages: list[Message] = []

        for message in messages:
            if message.get("role") == "system":
                content = message.get("content")
                if isinstance(content, str):
                    system_parts.append(content)
                continue
            anthropic_messages.append(message)

        system = "\n\n".join(system_parts) if system_parts else None
        return system, anthropic_messages

    def _sdk_error_types(self) -> tuple[type[Exception], ...]:
        error_names = ("APIError", "APIStatusError", "APIConnectionError")
        return tuple(
            error_type
            for name in error_names
            if isinstance((error_type := getattr(self._anthropic, name, None)), type)
        )
