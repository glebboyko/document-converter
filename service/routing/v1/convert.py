import asyncio
import logging

from fastapi import Depends
from fastapi.routing import APIRouter

from ..authorization import check_api_key
from ...models.convert.markdown import Request as RequestMarkdown
from ...utils.converter.markdown import convert as convert_markdown

router = APIRouter(prefix='/convert', dependencies=[Depends(check_api_key)])
g_logger = logging.getLogger('EG')


@router.post('/to-markdown')
async def to_markdown(request: RequestMarkdown):
    logger = g_logger.getChild('CV').getChild('TM')

    try:
        return await asyncio.to_thread(convert_markdown, logger, request)
    except Exception as exc:
        logger.error(f"cannot convert to markdown: {exc}")
        raise
