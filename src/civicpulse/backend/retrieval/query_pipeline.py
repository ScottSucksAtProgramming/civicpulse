import os
import re

from civicpulse.backend.api.loggers import UnansweredLogger
from civicpulse.backend.retrieval.metadata_filter import MetadataFilter
from civicpulse.backend.retrieval.retriever import Retriever
from civicpulse.backend.retrieval.synthesizer import NO_CONTENT_FALLBACK, Synthesizer
from civicpulse.backend.types import FilterSpec, QueryResponse

PII_REFUSAL_MARKER = "[[CIVICPULSE_PII_REFUSAL]]"
CLARIFYING_MARKER = "[[CIVICPULSE_CLARIFYING]]"


class QueryPipeline:
    def __init__(
        self,
        metadata_filter: MetadataFilter,
        retriever: Retriever,
        synthesizer: Synthesizer,
        unanswered_logger: UnansweredLogger,
    ) -> None:
        self._metadata_filter = metadata_filter
        self._retriever = retriever
        self._synthesizer = synthesizer
        self._unanswered_logger = unanswered_logger
        self._score_floor = self._read_score_floor()

    def run(self, question: str, model: str | None = None) -> tuple[QueryResponse, FilterSpec]:
        filters = self._metadata_filter.classify(question)
        sources = self._retriever.retrieve(question, filters)
        if not sources:
            self._unanswered_logger.log_refusal(
                redacted_query=question,
                failure_type="zero_results",
                document_type=filters.document_type,
            )
            return QueryResponse(answer=NO_CONTENT_FALLBACK, sources=[]), filters

        if self._score_floor is not None:
            top_score = max((source.score or 0.0) for source in sources)
            if top_score < self._score_floor:
                self._unanswered_logger.log_refusal(
                    redacted_query=question,
                    failure_type="low_score",
                    document_type=filters.document_type,
                )
                return QueryResponse(answer=NO_CONTENT_FALLBACK, sources=[]), filters

        response = self._synthesizer.synthesize(question=question, sources=sources, model=model)
        if response.answer.startswith(PII_REFUSAL_MARKER):
            self._unanswered_logger.log_refusal(
                redacted_query=question,
                failure_type="pii_refusal",
                document_type=filters.document_type,
            )
            return (
                QueryResponse(
                    answer=response.answer.removeprefix(PII_REFUSAL_MARKER).strip(),
                    sources=[],
                ),
                filters,
            )

        if response.answer.startswith(CLARIFYING_MARKER):
            self._unanswered_logger.log_refusal(
                redacted_query=question,
                failure_type="evaluative_redirect",
                document_type=filters.document_type,
            )
            return (
                QueryResponse(
                    answer=response.answer.removeprefix(CLARIFYING_MARKER).strip(),
                    sources=[],
                    clarifying=True,
                ),
                filters,
            )

        if not self._has_citation(response.answer) and not self._is_context_refusal(response.answer):
            self._unanswered_logger.log_refusal(
                redacted_query=question,
                failure_type="no_citation",
                document_type=filters.document_type,
            )
            response.sources = sources
        return response, filters

    def _read_score_floor(self) -> float | None:
        raw_value = os.getenv("CIVICPULSE_SCORE_FLOOR")
        if raw_value is None or not raw_value.strip():
            return None
        return float(raw_value)

    def _has_citation(self, answer: str) -> bool:
        return bool(re.search(r"\[\d+\]", answer))

    def _is_context_refusal(self, answer: str) -> bool:
        normalized = answer.lower()
        return any(
            phrase in normalized
            for phrase in (
                "i may not have the latest information",
                "that level of detail isn't in my sources",
                "that level of detail is not in my sources",
                "rather than the town of babylon",
            )
        )
