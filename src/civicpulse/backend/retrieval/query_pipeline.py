from civicpulse.backend.retrieval.metadata_filter import MetadataFilter
from civicpulse.backend.retrieval.retriever import Retriever
from civicpulse.backend.retrieval.synthesizer import Synthesizer
from civicpulse.backend.types import FilterSpec, QueryResponse


class QueryPipeline:
    def __init__(
        self,
        metadata_filter: MetadataFilter,
        retriever: Retriever,
        synthesizer: Synthesizer,
    ) -> None:
        self._metadata_filter = metadata_filter
        self._retriever = retriever
        self._synthesizer = synthesizer

    def run(self, question: str, model: str | None = None) -> tuple[QueryResponse, FilterSpec]:
        filters = self._metadata_filter.classify(question)
        sources = self._retriever.retrieve(question, filters)
        response = self._synthesizer.synthesize(question=question, sources=sources, model=model)
        return response, filters
