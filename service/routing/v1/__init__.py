from fastapi import APIRouter

from .convert import router as _router_convert

router = APIRouter(prefix='/api/v1')

router.include_router(_router_convert)
