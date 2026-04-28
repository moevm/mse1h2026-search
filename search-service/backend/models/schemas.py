from datetime import date, datetime
from typing import Any

from pydantic import (
    BaseModel,
    HttpUrl,
    SerializationInfo,
    field_serializer,
    field_validator,
)


class ArticleResult(BaseModel):
    id: str
    title: str
    authors: list[str]
    abstract: str
    keywords: list[str]
    date: date
    lang: str
    url: HttpUrl

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> date:
        if isinstance(v, str):
            return datetime.strptime(v, "%d-%m-%Y").date()
        return v

    @field_serializer("date")
    def serialize_date(self, v: date, _info: SerializationInfo) -> str:
        return v.strftime("%d-%m-%Y")


class SearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    query: str
    results: list[ArticleResult]


class SuggestResponse(BaseModel):
    suggestions: list[str]
