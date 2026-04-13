import re

from civicpulse.backend.types import FilterSpec, Source
from civicpulse.scraper.indexer import FTSIndexer


class Retriever:
    def __init__(self, indexer: FTSIndexer, top_n: int = 5) -> None:
        self._indexer = indexer
        self._top_n = top_n

    def retrieve(self, question: str, filters: FilterSpec) -> list[Source]:
        query_filters: dict[str, object] = {}
        if filters.document_type:
            query_filters["document_type"] = filters.document_type
        if filters.date_from and filters.date_to:
            query_filters["date"] = (filters.date_from, filters.date_to)

        results = self._indexer.query(
            self._normalize_query(question),
            filters=query_filters or None,
            top_n=self._top_n,
        )

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

    def _normalize_query(self, question: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9]+", question.lower())
        if not tokens:
            return question
        return " OR ".join(tokens)
