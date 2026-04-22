import os
import re

from civicpulse.backend.providers import LLMProvider
from civicpulse.backend.types import QueryResponse, Source

NO_CONTENT_FALLBACK = (
    "I couldn't find reliable Town of Babylon information for that question. "
    "CivicPulse can help with meeting minutes, town ordinances, town services, "
    "and contacting a representative. For the latest information, check "
    "https://www.townofbabylonny.gov."
)
DEFAULT_MODEL = "gpt-4o-mini"


class Synthesizer:
    def __init__(self, provider: LLMProvider, default_model: str | None = None) -> None:
        self._provider = provider
        self._default_model = default_model or os.getenv("CIVICPULSE_MODEL", DEFAULT_MODEL)

    def synthesize(
        self,
        question: str,
        sources: list[Source],
        model: str | None = None,
    ) -> QueryResponse:
        if not sources:
            return QueryResponse(answer=NO_CONTENT_FALLBACK, sources=[])

        prompt = self._build_prompt(question, sources)
        answer = self._provider.complete(
            model=model or self._default_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer only from the provided CivicPulse source excerpts. "
                        "Cite supporting excerpts only by bracketed reference number such as [1]. "
                        "If the user asks to draft a letter, write to a representative, or contact an official, "
                        "direct them to the 'Contact a Representative' category card. "
                        "If the sources are present but cannot answer a future or upcoming event question, "
                        "say: 'I may not have the latest information - check townofbabylonny.gov "
                        "directly for current schedules.' "
                        "If the user asks for hyperlocal street-level detail not in the sources, "
                        "say: 'That level of detail isn't in my sources - contact Town Hall directly "
                        "at https://www.townofbabylonny.gov/.' "
                        "If the user asks about a county, state, or federal topic outside Town of Babylon, "
                        "say that it may fall under that jurisdiction rather than the Town of Babylon "
                        "and provide a relevant official link. "
                        "Refuse queries seeking private information about a private individual who is "
                        "not a public official, elected representative, or named town employee acting "
                        "in an official capacity. Public officials are in scope for factual questions "
                        "about official actions, voting records, and public statements. Prefix that "
                        "refusal with [[CIVICPULSE_PII_REFUSAL]] and use this copy after the marker: "
                        "I only cover public government records and official Town of Babylon documents "
                        "- I'm not able to look up information about private individuals. "
                        "Detect explicit evaluative framing about officials or town decisions, such as "
                        "'doing a good job', 'how well is X performing', 'is X effective', or "
                        "'good leader'. Factual questions mentioning an official by name are not "
                        "evaluative. For explicit evaluative framing, prefix a criteria question with "
                        "[[CIVICPULSE_CLARIFYING]], asking what matters most to the user, for example "
                        "budget management, infrastructure improvements, or responsiveness to residents. "
                        "In all responses, never use evaluative language such as good, bad, successful, "
                        "or failed about any official or decision. "
                        "Remain strictly non-partisan. For politically framed questions, answer only "
                        "with retrieved facts and citations, and never take a political position, "
                        "advocate for or against an official, or tell the user how to vote."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        cited_sources = self._select_sources(answer, sources)
        return QueryResponse(answer=answer, sources=cited_sources)

    def _build_prompt(self, question: str, sources: list[Source]) -> str:
        chunks = []
        for index, source in enumerate(sources, start=1):
            chunks.append(
                f"[{index}] Title: {source.title}\n"
                f"URL: {source.url}\n"
                f"Document type: {source.document_type}\n"
                f"Date: {source.date or 'unknown'}\n"
                f"Excerpt: {source.content or ''}"
            )
        joined_chunks = "\n\n".join(chunks)
        return f"Question: {question}\n\nSources:\n{joined_chunks}"

    def _select_sources(self, answer: str, sources: list[Source]) -> list[Source]:
        cited_indexes = {
            int(match)
            for match in re.findall(r"\[(\d+)\]", answer)
            if 1 <= int(match) <= len(sources)
        }
        if not cited_indexes:
            return sources
        return [source for idx, source in enumerate(sources, start=1) if idx in cited_indexes]
