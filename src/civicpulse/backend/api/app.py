import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from civicpulse.backend.providers import LLMError, get_provider
from civicpulse.backend.retrieval.metadata_filter import MetadataFilter
from civicpulse.backend.retrieval.query_pipeline import QueryPipeline
from civicpulse.backend.retrieval.retriever import Retriever
from civicpulse.backend.retrieval.synthesizer import Synthesizer
from civicpulse.backend.types import QueryResponse
from civicpulse.scraper.indexer import FTSIndexer

DEFAULT_TOP_N = 5


class QueryRequest(BaseModel):
    question: str
    model: str | None = None


def _read_top_n() -> int:
    raw_value = os.getenv("CIVICPULSE_TOP_N")
    if raw_value is None:
        return DEFAULT_TOP_N

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("CIVICPULSE_TOP_N must be an integer") from exc


def create_app(vault_path: Path | None = None) -> FastAPI:
    if vault_path is None:
        vault_path = Path(os.getenv("CIVICPULSE_VAULT_PATH", "./vault"))
    frontend_dir = Path(__file__).resolve().parents[4] / "frontend"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        indexer = FTSIndexer(vault_path)
        top_n = _read_top_n()
        provider = get_provider()
        default_model = os.getenv("CIVICPULSE_MODEL", "gpt-4o-mini")
        filter_model = os.getenv("CIVICPULSE_FILTER_MODEL", default_model)
        retriever = Retriever(indexer=indexer, top_n=top_n)
        synthesizer = Synthesizer(provider=provider, default_model=default_model)
        pipeline = QueryPipeline(
            metadata_filter=MetadataFilter(provider=provider, model=filter_model),
            retriever=retriever,
            synthesizer=synthesizer,
        )
        app.state.indexer = indexer
        app.state.provider = provider
        app.state.pipeline = pipeline
        yield

    app = FastAPI(lifespan=lifespan)

    @app.post(
        "/query",
        response_model=QueryResponse,
        response_model_exclude={"sources": {"__all__": {"content"}}},
        response_model_exclude_none=True,
    )
    async def query(request: QueryRequest) -> QueryResponse:
        try:
            return app.state.pipeline.run(request.question, model=request.model)
        except LLMError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "CivicPulse could not generate an answer right now. "
                    "Please try again shortly."
                ),
            ) from exc

    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app
