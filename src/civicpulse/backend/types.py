from pydantic import BaseModel, ConfigDict


class FilterSpec(BaseModel):
    document_type: str | None = None
    date_from: str | None = None
    date_to: str | None = None


class Source(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    url: str
    document_type: str
    date: str | None = None
    content: str | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]


class SuggestRecipientRequest(BaseModel):
    concern: str


class SuggestRecipientResponse(BaseModel):
    suggested_recipient: str
    topic: str
    abstracted_concern: str


class GenerateRequest(BaseModel):
    concern: str
    outcome: str
    tone: str
    recipient: str


class GenerateResponse(BaseModel):
    letter: str
    sources: list[Source]


class ReviseRequest(BaseModel):
    current_letter: str
    revision_request: str
    concern: str
    recipient: str


class ReviseResponse(BaseModel):
    letter: str


class SoapboxFollowupRequest(BaseModel):
    messages: list[dict]


class SoapboxFollowupResponse(BaseModel):
    question: str


class SoapboxSummarizeRequest(BaseModel):
    messages: list[dict]


class SoapboxSummary(BaseModel):
    summary: str
    topic: str


class SoapboxSubmitRequest(BaseModel):
    summary: str
    topic: str
