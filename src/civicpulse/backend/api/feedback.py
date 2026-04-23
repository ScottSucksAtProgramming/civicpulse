from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
    comment: str | None = None
    document_type: str | None = None


def build_feedback_router() -> APIRouter:
    router = APIRouter(tags=["feedback"])

    @router.post("/feedback", status_code=204)
    async def feedback(
        request: FeedbackRequest,
        fastapi_request: Request,
    ) -> Response:
        fastapi_request.app.state.feedback_logger.log_feedback(
            rating=request.rating,
            comment=request.comment,
            document_type=request.document_type,
        )
        return Response(status_code=204)

    return router
