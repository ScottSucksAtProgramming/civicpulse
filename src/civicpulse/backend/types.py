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
