import base64
import os
import tempfile
from datetime import datetime, timezone
from logging import Logger

from markitdown import MarkItDown
from markitdown._exceptions import UnsupportedFormatException
from redis import Redis

from ..config import Config
from ..prompts import BASIC_PROMPT
from ...models.convert.markdown import Request, Response200


def _register_request(redis: Redis, config: Config, request: Request) -> tuple[str, str]:
    request_id = str(redis.incr('curr_request_id'))

    model = request.llm_model or config.openai.default_model

    mapping = {
        'llm_model': model,
        'created_dt': datetime.now().astimezone(timezone.utc).isoformat()
    }

    redis.hset(request_id, mapping=mapping)

    return request_id, model


def _get_used_tokens(redis: Redis, request_id: str) -> Response200.TokenUsage:
    in_tokens = redis.hget(request_id, 'in_tokens') or 0
    out_tokens = redis.hget(request_id, 'out_tokens') or 0

    return Response200.TokenUsage(
        input=int(in_tokens),
        output=int(out_tokens)
    )


def _end_request(redis: Redis, request_id: str):
    redis.hset(request_id, 'ended_dt', datetime.now().astimezone(timezone.utc).isoformat())


def convert(p_logger: Logger, request: Request) -> Response200:
    logger = p_logger.getChild('CV').getChild('MD')

    try:
        config = Config.get_config()

        with Redis(os.getenv('REDIS_HOST')) as redis:
            request_id, llm_model = _register_request(redis, config, request)
            logger.info(f"registered request {request_id}")
    except Exception as exc:
        logger.error(f"cannot register request: {exc}")
        raise

    try:
        markitdown = MarkItDown(enable_plugins=True)

        with tempfile.NamedTemporaryFile(suffix=request.extension) as input_file:
            with open(input_file.name, 'wb') as file:
                file.write(base64.b64decode(request.content))

            try:
                converted_document = markitdown.convert(
                    input_file.name,
                    request_id=request_id,
                    llm_prompt=BASIC_PROMPT,
                    llm_api_key=config.openai.api_key,
                    llm_base_url=config.openai.base_url
                ).text_content
            except UnsupportedFormatException as exc:
                logger.warning(f"file {request.extension} is not supported: {exc}")
                try:
                    with open(input_file.name) as file:
                        converted_document = file.read()
                except UnicodeDecodeError:
                    logger.warning("cannot decode file")
                    raise

        with Redis(os.getenv('REDIS_HOST')) as redis:
            token_usage = _get_used_tokens(redis, request_id)
            logger.info(f"request {request_id} processed successfully: {len(converted_document)} ({token_usage})")
    except Exception as exc:
        logger.error(f"cannot process request: {exc}")
        raise
    finally:
        with Redis(os.getenv('REDIS_HOST')) as redis:
            _end_request(redis, request_id)

    return Response200(
        md=converted_document,
        llm_model=llm_model,
        token_usage=token_usage
    )