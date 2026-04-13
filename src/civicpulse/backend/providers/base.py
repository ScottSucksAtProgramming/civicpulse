from typing import Any, Protocol

Message = dict[str, Any]


class LLMError(Exception):
    """Normalized provider error exposed to the rest of the backend."""


class LLMProvider(Protocol):
    def complete(self, messages: list[Message], model: str) -> str: ...

    def tool_call(
        self,
        messages: list[Message],
        tool_name: str,
        tool_schema: dict[str, Any],
        model: str,
    ) -> dict[str, Any]: ...
