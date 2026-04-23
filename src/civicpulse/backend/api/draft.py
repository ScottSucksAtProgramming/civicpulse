import datetime
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from civicpulse.backend.privacy import redact
from civicpulse.backend.providers import LLMError
from civicpulse.backend.types import (
    GenerateRequest,
    GenerateResponse,
    ReviseRequest,
    ReviseResponse,
    SuggestRecipientRequest,
    SuggestRecipientResponse,
)


class DraftLogger:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def ensure_table(self) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS draft_log (
                    recipient TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    abstracted_concern TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            columns = {
                row[1]
                for row in con.execute(
                    """
                    PRAGMA table_info(draft_log)
                    """
                )
            }
            if "event_type" not in columns:
                con.execute(
                    """
                    ALTER TABLE draft_log
                    ADD COLUMN event_type TEXT NOT NULL DEFAULT 'suggestion'
                    """
                )
            con.commit()

    def log_suggestion(self, result: SuggestRecipientResponse) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                INSERT INTO draft_log (
                    recipient, topic, abstracted_concern, timestamp, event_type
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    result.suggested_recipient,
                    result.topic,
                    redact(result.abstracted_concern),
                    datetime.datetime.now(datetime.UTC).isoformat(),
                    "suggestion",
                ),
            )
            con.commit()

    def log_generation(
        self,
        recipient: str,
        topic: str | None,
        abstracted_concern: str,
    ) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                INSERT INTO draft_log (
                    recipient, topic, abstracted_concern, timestamp, event_type
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    recipient,
                    topic or "",
                    redact(abstracted_concern),
                    datetime.datetime.now(datetime.UTC).isoformat(),
                    "generation",
                ),
            )
            con.commit()


def build_draft_router() -> APIRouter:
    router = APIRouter(prefix="/draft", tags=["draft"])

    @router.post("/suggest-recipient", response_model=SuggestRecipientResponse)
    async def suggest_recipient(
        request: SuggestRecipientRequest,
        fastapi_request: Request,
    ) -> SuggestRecipientResponse:
        try:
            result = fastapi_request.app.state.recipient_classifier.classify(request.concern)
        except LLMError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "CivicPulse could not generate an answer right now. "
                    "Please try again shortly."
                ),
            ) from exc

        fastapi_request.app.state.draft_logger.log_suggestion(result)
        return result

    @router.post(
        "/generate",
        response_model=GenerateResponse,
        response_model_exclude={"sources": {"__all__": {"content", "score"}}},
    )
    async def generate_letter(
        request: GenerateRequest,
        fastapi_request: Request,
    ) -> GenerateResponse:
        try:
            response = fastapi_request.app.state.letter_generator.generate(
                concern=request.concern,
                outcome=request.outcome,
                tone=request.tone,
                recipient=request.recipient,
            )
        except LLMError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "CivicPulse could not generate an answer right now. "
                    "Please try again shortly."
                ),
            ) from exc
        fastapi_request.app.state.draft_logger.log_generation(
            recipient=request.recipient,
            topic=request.topic,
            abstracted_concern=request.abstracted_concern or request.concern,
        )
        return response

    @router.post("/revise", response_model=ReviseResponse)
    async def revise_letter(
        request: ReviseRequest,
        fastapi_request: Request,
    ) -> ReviseResponse:
        try:
            letter = fastapi_request.app.state.letter_generator.revise(
                current_letter=request.current_letter,
                revision_request=request.revision_request,
                concern=request.concern,
                recipient=request.recipient,
            )
        except LLMError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "CivicPulse could not generate an answer right now. "
                    "Please try again shortly."
                ),
            ) from exc

        return ReviseResponse(letter=letter)

    return router
