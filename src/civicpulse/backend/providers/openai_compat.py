import json
import logging
from typing import Any

import openai
from openai import OpenAI

from civicpulse.backend.providers.base import LLMError, LLMProvider, Message

LOGGER = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        client: OpenAI | Any | None = None,
    ) -> None:
        self._client = client or OpenAI(base_url=base_url, api_key=api_key)

    def complete(self, messages: list[Message], model: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return response.choices[0].message.content or ""
        except openai.APIError as exc:
            raise LLMError("OpenAI-compatible completion failed") from exc
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMError("OpenAI-compatible completion returned an invalid response") from exc

    def tool_call(
        self,
        messages: list[Message],
        tool_name: str,
        tool_schema: dict[str, Any],
        model: str,
    ) -> dict[str, Any]:
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "parameters": tool_schema,
                        },
                    }
                ],
                tool_choice={
                    "type": "function",
                    "function": {"name": tool_name},
                },
            )
            msg = response.choices[0].message
            LOGGER.debug(
                "tool_call raw response: tool_calls=%r content=%r",
                msg.tool_calls,
                getattr(msg, "content", None),
            )
            arguments = msg.tool_calls[0].function.arguments
            return json.loads(arguments)
        except openai.APIError as exc:
            raise LLMError("OpenAI-compatible tool call failed") from exc
        except (AttributeError, IndexError, TypeError, ValueError) as exc:
            raise LLMError(
                f"OpenAI-compatible tool call returned an invalid response: {exc}"
            ) from exc
