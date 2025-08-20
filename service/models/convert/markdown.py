from typing import Optional

from pydantic import BaseModel


class Request(BaseModel):
    content: str
    extension: str
    llm_model_ocr: Optional[str] = None
    llm_model_image: Optional[str] = None


class Response200(BaseModel):
    class TokenUsage(BaseModel):
        input: int
        output: int

    md: str
    llm_model_ocr: str
    llm_model_image: str
    token_usage: dict[str, TokenUsage]
