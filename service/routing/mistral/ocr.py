import asyncio
import base64
import logging
import os

from fastapi import HTTPException
from fastapi.routing import APIRouter

from ...models.convert.markdown import Request as RequestMarkdown
from ...models.ocr.mistral import Page, Request, Response, UsageInfo
from ...utils.converter.markdown import convert as convert_markdown

router = APIRouter()
g_logger = logging.getLogger('EG')


@router.post('/ocr', response_model=Response)
async def ocr(request: Request) -> Response:
    logger = g_logger.getChild('OCR').getChild('MS')

    _, ext = os.path.splitext(request.document.document_name)
    extension = ext.lstrip('.').lower()
    if not extension:
        raise HTTPException(
            status_code=422,
            detail="document_name must include a file extension",
        )

    try:
        doc_size_bytes = len(base64.b64decode(request.document.document_base64, validate=True))
    except (ValueError, base64.binascii.Error) as exc:
        raise HTTPException(status_code=422, detail=f"invalid base64 content: {exc}")

    internal_request = RequestMarkdown(
        content=request.document.document_base64,
        extension=extension,
        llm_model_ocr=request.model,
        llm_model_image=None,
    )

    try:
        result = await asyncio.to_thread(convert_markdown, logger, internal_request)
    except Exception as exc:
        logger.error(f"cannot convert to markdown: {exc}")
        raise

    return Response(
        pages=[Page(markdown=result.md)],
        model=request.model,
        usage_info=UsageInfo(doc_size_bytes=doc_size_bytes),
    )
