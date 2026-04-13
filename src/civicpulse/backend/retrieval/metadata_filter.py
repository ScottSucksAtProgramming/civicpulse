import logging

from civicpulse.backend.providers import LLMError, LLMProvider
from civicpulse.backend.types import FilterSpec

LOGGER = logging.getLogger(__name__)
FILTER_MODEL = "gpt-4o-mini"


class MetadataFilter:
    def __init__(self, provider: LLMProvider, model: str = FILTER_MODEL) -> None:
        self._provider = provider
        self._model = model

    _SYSTEM = (
        "You are a query classifier for a civic information retrieval system. "
        "Given a resident's question, call the classify_query tool to extract any "
        "date range or document type constraints implied by the question. "
        "Use null for fields that are not constrained. "
        "Valid document_type values: agenda, minutes, service-page, public-meeting, council, ordinance."
    )

    def classify(self, question: str) -> FilterSpec:
        try:
            response = self._provider.tool_call(
                messages=[
                    {"role": "system", "content": self._SYSTEM},
                    {
                        "role": "user",
                        "content": question,
                    }
                ],
                tool_name="classify_query",
                tool_schema=FilterSpec.model_json_schema(),
                model=self._model,
            )
            return FilterSpec.model_validate(response)
        except LLMError as exc:
            LOGGER.warning("MetadataFilter failed, falling back to empty filter: %s", exc)

        return FilterSpec()
