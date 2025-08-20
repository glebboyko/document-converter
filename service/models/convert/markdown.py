from typing import Optional

from pydantic import BaseModel


class Request(BaseModel):
    content: str
    extension: str
    llm_model: Optional[str] = None


class Response200(BaseModel):
    class TokenUsage(BaseModel):
        input: int
        output: int

    md: str
    llm_model: str
    token_usage: TokenUsage
