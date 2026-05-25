from fastapi import APIRouter

from .ocr import router as _router_ocr

router = APIRouter(prefix='/v1')

router.include_router(_router_ocr)
