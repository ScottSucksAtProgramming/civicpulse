import datetime
import logging

from civicpulse.backend.providers import LLMError, LLMProvider
from civicpulse.backend.types import FilterSpec

LOGGER = logging.getLogger(__name__)
FILTER_MODEL = "gpt-4o-mini"


class MetadataFilter:
    def __init__(self, provider: LLMProvider, model: str = FILTER_MODEL) -> None:
        self._provider = provider
        self._model = model

    _SYSTEM_TEMPLATE = (
        "You are a query classifier for a civic information retrieval system. "
        "Today's date is {today}. "
        "Given a resident's question, call the classify_query tool to extract any "
        "date range or document type constraints implied by the question. "
        "Use null for fields that are not constrained. "
        "Only set date_from and date_to for specific years or explicit month+year references "
        "(e.g. 'January 2025', 'in 2024'). "
        "For vague relative references like 'last month', 'recently', or 'latest', "
        "set document_type only and leave dates null. "
        "Valid document_type values and when to use them: "
        "agenda — upcoming meeting schedules; "
        "meeting-minutes — written records of past meetings; "
        "meeting-video — questions about what was said, discussed, or decided in town board meetings; "
        "ordinance — zoning rules, building codes, local laws, permit requirements; "
        "service-page — general town services and information; "
        "public-meeting — upcoming public meeting announcements; "
        "clerk-form — the actual application forms and PDFs for permits and licenses "
        "(e.g. dog license, marriage license, building permit, parking permit); "
        "use clerk-form whenever the question is about applying for, obtaining, or renewing a license or permit; "
        "clerk — Town Clerk office general information (hours, contact, procedures, not a specific form); "
        "foil — Freedom of Information Law requests; "
        "council — Town Council information; "
        "department-page — town department information; "
        "planning — planning board information."
    )

    def classify(self, question: str) -> FilterSpec:
        system = self._SYSTEM_TEMPLATE.format(today=datetime.date.today().isoformat())
        try:
            response = self._provider.tool_call(
                messages=[
                    {"role": "system", "content": system},
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
