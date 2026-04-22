from civicpulse.backend.providers import LLMProvider
from civicpulse.backend.types import SoapboxSummary


class SoapboxPipeline:
    _SYSTEM_PROMPT = (
        "You are helping a Town of Babylon resident express civic feedback. "
        "Ask one civic-focused, open-ended, non-leading follow-up question. "
        "Do not suggest political positions, advocate for any outcome, or steer the resident "
        "toward a specific policy preference."
    )

    def __init__(self, provider: LLMProvider, model: str) -> None:
        self._provider = provider
        self._model = model

    def generate_followup(self, messages: list[dict]) -> str:
        return self._provider.complete(
            messages=[{"role": "system", "content": self._SYSTEM_PROMPT}, *messages],
            model=self._model,
        )

    def summarize(self, messages: list[dict]) -> SoapboxSummary:
        response = self._provider.tool_call(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize the resident's civic feedback into a concise, neutral "
                        "summary and a short topic label."
                    ),
                },
                *messages,
            ],
            tool_name="summarize_soapbox",
            tool_schema=SoapboxSummary.model_json_schema(),
            model=self._model,
        )
        return SoapboxSummary.model_validate(response)
