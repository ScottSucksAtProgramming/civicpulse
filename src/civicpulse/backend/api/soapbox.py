import os

from fastapi import APIRouter, HTTPException, Request

from civicpulse.backend.providers import LLMError
from civicpulse.backend.types import (
    SoapboxFollowupRequest,
    SoapboxFollowupResponse,
    SoapboxSubmitRequest,
    SoapboxSummarizeRequest,
    SoapboxSummary,
)

DEFAULT_SOAPBOX_MAX_TURNS = 3


def read_soapbox_max_turns() -> int:
    raw_value = os.getenv("CIVICPULSE_SOAPBOX_MAX_TURNS")
    if raw_value is None:
        return DEFAULT_SOAPBOX_MAX_TURNS

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("CIVICPULSE_SOAPBOX_MAX_TURNS must be an integer") from exc


def build_soapbox_router() -> APIRouter:
    router = APIRouter(prefix="/soapbox", tags=["soapbox"])

    @router.post("/followup", response_model=SoapboxFollowupResponse)
    async def followup(
        request: SoapboxFollowupRequest,
        fastapi_request: Request,
    ) -> SoapboxFollowupResponse:
        user_message_count = sum(
            1 for message in request.messages if message.get("role") == "user"
        )
        if user_message_count > fastapi_request.app.state.soapbox_max_turns:
            raise HTTPException(status_code=400, detail="Soapbox turn limit exceeded.")

        try:
            question = fastapi_request.app.state.soapbox_pipeline.generate_followup(
                request.messages
            )
        except LLMError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "CivicPulse could not generate an answer right now. "
                    "Please try again shortly."
                ),
            ) from exc

        return SoapboxFollowupResponse(question=question)

    @router.post("/summarize", response_model=SoapboxSummary)
    async def summarize(
        request: SoapboxSummarizeRequest,
        fastapi_request: Request,
    ) -> SoapboxSummary:
        try:
            return fastapi_request.app.state.soapbox_pipeline.summarize(request.messages)
        except LLMError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "CivicPulse could not generate an answer right now. "
                    "Please try again shortly."
                ),
            ) from exc

    @router.post("/submit")
    async def submit(
        request: SoapboxSubmitRequest,
        fastapi_request: Request,
    ) -> dict[str, str]:
        fastapi_request.app.state.soapbox_logger.log_submission(request)
        return {"status": "ok"}

    return router
