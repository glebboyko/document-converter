import base64
import os
import tempfile
from datetime import datetime, timezone
from logging import Logger

from markitdown import MarkItDown
from markitdown._exceptions import UnsupportedFormatException
from redis import Redis

from ..config import Config
from ...models.convert.markdown import Request, Response200


def _register_request(redis: Redis, config: Config, request: Request) -> tuple[str, str, str]:
    request_id = str(redis.incr('curr_request_id'))

    ocr_model = request.llm_model_ocr or config.openai.default_model_ocr
    image_model = request.llm_model_image or config.openai.default_model_image

    mapping = {
        'llm_model_ocr': ocr_model,
        'llm_model_image': image_model,
        'created_dt': datetime.now().astimezone(timezone.utc).isoformat()
    }

    redis.hset(request_id, mapping=mapping)

    return request_id, ocr_model, image_model


def _get_used_tokens(redis: Redis, request_id: str) -> tuple[Response200.TokenUsage, Response200.TokenUsage]:
    llm_ocr_in_tokens = redis.hget(request_id, 'llm_ocr_in_tokens') or 0
    llm_ocr_out_tokens = redis.hget(request_id, 'llm_ocr_out_tokens') or 0

    llm_image_in_tokens = redis.hget(request_id, 'llm_image_in_tokens') or 0
    llm_image_out_tokens = redis.hget(request_id, 'llm_image_out_tokens') or 0

    return Response200.TokenUsage(
        input=llm_ocr_in_tokens,
        output=llm_ocr_out_tokens
    ), Response200.TokenUsage(
        input=llm_image_in_tokens,
        output=llm_image_out_tokens
    )


def _end_request(redis: Redis, request_id: str):
    redis.hset(request_id, 'ended_dt', datetime.now().astimezone(timezone.utc).isoformat())


def convert(p_logger: Logger, request: Request) -> Response200:
    logger = p_logger.getChild('CV').getChild('MD')

    try:
        config = Config.get_config()

        with Redis(os.getenv('REDIS_HOST')) as redis:
            request_id, llm_model_ocr, llm_model_image = _register_request(redis, config, request)
            logger.info(f"registered request {request_id}")
    except Exception as exc:
        logger.error(f"cannot register request: {exc}")
        raise

    try:
        markitdown = MarkItDown(enable_plugins=True)

        with tempfile.NamedTemporaryFile(suffix=f'.{request.extension}') as input_file:
            with open(input_file.name, 'wb') as file:
                file.write(base64.b64decode(request.content))

            try:
                converted_document = markitdown.convert(
                    input_file.name,
                    request_id=request_id,
                    ocr_api_key=config.yandex_ocr_api_key,
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
            token_usage_ocr, token_usage_image = _get_used_tokens(redis, request_id)

        token_usage = {
            "llm_model_ocr": token_usage_ocr,
            "llm_model_image": token_usage_image
        }
        logger.info(f"request {request_id} processed successfully: {len(converted_document)} ({token_usage})")
    except Exception as exc:
        logger.error(f"cannot process request: {exc}")
        raise
    finally:
        with Redis(os.getenv('REDIS_HOST')) as redis:
            _end_request(redis, request_id)

    return Response200(
        md=converted_document,
        llm_model_ocr=llm_model_ocr,
        llm_model_image=llm_model_image,
        token_usage=token_usage
    )
