import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus

from fastapi import Depends, security
from fastapi import HTTPException

from ..utils.config import Config


@dataclass
class CachedKeys:
    keys: set[str] = field(default_factory=set)
    valid_until: datetime = None


_keys = CachedKeys()


def _sync_keys():
    if _keys.valid_until is None or _keys.valid_until < datetime.now():
        auth_config = Config.get_config().auth
        _keys.valid_until = datetime.now() + auth_config.cache_valid_delta
        _keys.keys = set(auth_config.api_keys_hash)


async def check_api_key(api_key: str = Depends(security.APIKeyHeader(name='api-key', auto_error=False))):
    """
    Проверяет корректность api-ключа
    :param api_key: переданный api-ключ
    :raises HTTPException: (401), если токен не найден
    """

    if api_key is None:
        raise HTTPException(HTTPStatus.UNAUTHORIZED)

    _sync_keys()
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    if key_hash not in _keys.keys:
        raise HTTPException(HTTPStatus.UNAUTHORIZED)
