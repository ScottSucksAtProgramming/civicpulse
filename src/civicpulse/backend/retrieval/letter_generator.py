import re

from civicpulse.backend.providers import LLMProvider
from civicpulse.backend.types import GenerateResponse, Source
from civicpulse.scraper.indexer import FTSIndexer

class LetterGenerator:
    def __init__(
        self,
        provider: LLMProvider,
        indexer: FTSIndexer,
        top_n: int = 5,
        model: str = "gpt-4o-mini",
    ) -> None:
        self._provider = provider
        self._indexer = indexer
        self._top_n = top_n
        self._model = model

    def generate(
        self,
        *,
        concern: str,
        outcome: str,
        tone: str,
        recipient: str,
    ) -> GenerateResponse:
        sources = self._retrieve_sources(concern)
        prompt = self._build_generation_prompt(
            concern=concern,
            outcome=outcome,
            tone=tone,
            recipient=recipient,
            sources=sources,
        )
        letter = self._provider.complete(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Draft a clear resident letter to a Town of Babylon recipient. "
                        "Stay non-partisan and do not add facts beyond the provided inputs and sources. "
                        "When sources are provided, cite supporting facts with bracketed references like [1]. "
                        "When no sources are provided, do not invent or cite any town records."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return GenerateResponse(letter=letter, sources=self._select_sources(letter, sources))

    def revise(
        self,
        *,
        current_letter: str,
        revision_request: str,
        concern: str,
        recipient: str,
    ) -> str:
        return self._provider.complete(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Revise a resident's civic letter. Preserve the intended recipient and overall position "
                        "unless the revision request explicitly changes them. Return only the revised letter text."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Recipient: {recipient}\n"
                        f"Resident concern: {concern}\n"
                        f"Revision request: {revision_request}\n\n"
                        f"Current letter:\n{current_letter}"
                    ),
                },
            ],
        )

    def _retrieve_sources(self, concern: str) -> list[Source]:
        query = self._normalize_query(concern)
        if not query:
            return []

        results = self._indexer.query(query, top_n=self._top_n)
        return [
            Source(
                title=result.title,
                url=result.source_url,
                document_type=result.document_type,
                date=result.date,
                content=result.content_preview,
            )
            for result in results
        ]

    def _normalize_query(self, concern: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9]+", concern.lower())
        if not tokens:
            return concern
        return " OR ".join(tokens)

    def _build_generation_prompt(
        self,
        *,
        concern: str,
        outcome: str,
        tone: str,
        recipient: str,
        sources: list[Source],
    ) -> str:
        request = (
            f"Recipient: {recipient}\n"
            f"Resident concern: {concern}\n"
            f"Desired outcome: {outcome}\n"
            f"Tone: {tone}\n"
        )
        if not sources:
            return request + "\nSources:\nNone"

        chunks = []
        for index, source in enumerate(sources, start=1):
            chunks.append(
                f"[{index}] Title: {source.title}\n"
                f"URL: {source.url}\n"
                f"Document type: {source.document_type}\n"
                f"Date: {source.date or 'unknown'}\n"
                f"Excerpt: {source.content or ''}"
            )
        return request + "\nSources:\n" + "\n\n".join(chunks)

    def _select_sources(self, letter: str, sources: list[Source]) -> list[Source]:
        cited_indexes = {
            int(match)
            for match in re.findall(r"\[(\d+)\]", letter)
            if 1 <= int(match) <= len(sources)
        }
        if not cited_indexes:
            return []
        return [source for idx, source in enumerate(sources, start=1) if idx in cited_indexes]
