from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DocumentBase64(BaseModel):
    type: Literal["document_base64"]
    document_base64: str
    document_name: str


class Request(BaseModel):
    model: str
    document: DocumentBase64

    id: Optional[str] = None
    pages: Optional[list[int]] = None
    include_image_base64: Optional[bool] = None
    image_limit: Optional[int] = None
    image_min_size: Optional[int] = None


class Page(BaseModel):
    index: int = 0
    markdown: str
    images: list[Any] = Field(default_factory=list)
    dimensions: dict[str, Any] = Field(default_factory=dict)


class UsageInfo(BaseModel):
    pages_processed: int = 1
    doc_size_bytes: int


class Response(BaseModel):
    pages: list[Page]
    model: str
    usage_info: UsageInfo
