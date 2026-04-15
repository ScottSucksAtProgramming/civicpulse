from civicpulse.backend.providers import LLMProvider
from civicpulse.backend.types import SuggestRecipientResponse

BOARD_OPTIONS = [
    "Town Board",
    "Town Council",
    "Planning Board",
    "Zoning Board of Appeals",
    "Town Clerk",
    "Department",
]
CLASSIFIER_MODEL = "claude-3-5-haiku-latest"


class RecipientClassifier:
    _SYSTEM_PROMPT = (
        "You classify civic concerns for a Town of Babylon letter-drafting assistant. "
        "Call the classify_recipient tool with three fields only: "
        "suggested_recipient, topic, and abstracted_concern. "
        f"Suggested recipient must be one of: {', '.join(BOARD_OPTIONS)}. "
        "Use 'Department' when the concern belongs to a town department rather than a board or clerk. "
        "topic should be a short lowercase tag like zoning, sanitation, roads, permits, or meetings. "
        "abstracted_concern must be a short third-person summary with personal details removed. "
        "Never repeat names, addresses, phone numbers, email addresses, or direct quotes from the resident."
    )

    def __init__(self, provider: LLMProvider, model: str = CLASSIFIER_MODEL) -> None:
        self._provider = provider
        self._model = model

    def classify(self, concern: str) -> SuggestRecipientResponse:
        response = self._provider.tool_call(
            messages=[
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user", "content": concern},
            ],
            tool_name="classify_recipient",
            tool_schema=SuggestRecipientResponse.model_json_schema(),
            model=self._model,
        )
        return SuggestRecipientResponse.model_validate(response)
