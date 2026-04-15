import os
import re

from civicpulse.backend.providers import LLMProvider
from civicpulse.backend.types import QueryResponse, Source

NO_CONTENT_FALLBACK = (
    "I couldn't find relevant Town of Babylon content for that question. "
    "Please check the official website at https://www.townofbabylonny.gov "
    "for the latest information."
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
                        "direct them to the 'Contact a Representative' category card."
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
