import io
import logging
import os
from typing import BinaryIO, Any

import openai
from redis import Redis

from .._base_converter import DocumentConverter, DocumentConverterResult
from .._stream_info import StreamInfo
from ..converter_utils.img_converter import gpt_vision, yandex_ocr, image_encoders

ACCEPTED_MIME_TYPE_PREFIXES = [
    "image/jpeg",
    "image/png",
]

ACCEPTED_FILE_EXTENSIONS = [".jpg", ".jpeg", ".png"]


class ImageConverter(DocumentConverter):
    """
    Converts images to markdown via extraction of metadata (if `exiftool` is installed), and description via a multimodal LLM (if an llm_client is configured).
    """

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()

        if extension in ACCEPTED_FILE_EXTENSIONS:
            return True

        for prefix in ACCEPTED_MIME_TYPE_PREFIXES:
            if mimetype.startswith(prefix):
                return True

        return False

    @staticmethod
    def _get_redis() -> Redis:
        return Redis(host=os.getenv('REDIS_HOST'))

    @staticmethod
    def _get_llm_models(request_id: str) -> tuple[str, str]:
        with ImageConverter._get_redis() as redis_client:
            llm_model_table = redis_client.hget(request_id, 'llm_model_ocr').decode()
            llm_model_image = redis_client.hget(request_id, 'llm_model_image').decode()

        assert llm_model_table is not None and llm_model_image is not None

        return llm_model_table, llm_model_image

    @staticmethod
    def _get_used_tokens(redis_client: Redis, request_id: str, table_model: bool) -> gpt_vision.TokenUsage:
        in_tokens = redis_client.hget(request_id, 'llm_ocr_in_tokens' if table_model else 'llm_image_in_tokens') or 0
        out_tokens = redis_client.hget(request_id,
                                       'llm_ocr_out_tokens' if table_model else 'llm_image_out_tokens') or 0

        return gpt_vision.TokenUsage(
            input=int(in_tokens),
            output=int(out_tokens)
        )

    @staticmethod
    def _set_used_tokens(redis_client: Redis, request_id: str, table_model: bool, tokens: gpt_vision.TokenUsage):
        redis_client.hset(request_id, 'llm_ocr_in_tokens' if table_model else 'llm_image_in_tokens',
                          str(tokens.input))
        redis_client.hset(request_id, 'llm_ocr_out_tokens' if table_model else 'llm_image_out_tokens',
                          str(tokens.output))

    @staticmethod
    def _update_used_tokens(request_id: str, table_model: bool, tokens: gpt_vision.TokenUsage):
        with ImageConverter._get_redis() as redis_client:
            curr_tokens = ImageConverter._get_used_tokens(redis_client, request_id, table_model)

            result_tokens = gpt_vision.TokenUsage(
                input=curr_tokens.input + tokens.input,
                output=curr_tokens.output + tokens.output
            )

            ImageConverter._set_used_tokens(redis_client, request_id, table_model, result_tokens)

    def convert(
            self,
            file_stream: BinaryIO,
            stream_info: StreamInfo,
            **kwargs: Any,  # Options to pass to the converter
    ) -> DocumentConverterResult:
        logger = logging.getLogger('IC').getChild('CV')

        try:
            request_id = kwargs.get('request_id')

            ocr_api_key = kwargs.get('ocr_api_key')
            llm_api_key = kwargs.get('llm_api_key')
            base_url = kwargs.get('llm_base_url')

            llm_client = openai.Client(api_key=llm_api_key, base_url=base_url)
            llm_model_table, llm_model_image = self._get_llm_models(request_id)

            file_stream = image_encoders.to_png(logger, file_stream, stream_info)

            ocr_image = yandex_ocr.process_image(file_stream, ocr_api_key)

            if ocr_image:
                logger.info("image contain text. converting to table...")
                image_table, token_usage = gpt_vision.ocr_to_table(ocr_image, llm_client, llm_model_table)
                self._update_used_tokens(request_id, True, token_usage)
                logger.info(f"image converted to table with {llm_model_table}: {token_usage}")

                content, token_usage = gpt_vision.composed_image_to_markdown(file_stream, image_table, llm_client, llm_model_image)
                self._update_used_tokens(request_id, False, token_usage)
                logger.info(f"image converted to markdown with {llm_model_image}: {token_usage}")
            else:
                logger.info("image does not contain text. converting to markdown...")
                content, token_usage = gpt_vision.graphic_image_to_markdown(file_stream, llm_client, llm_model_image)
                self._update_used_tokens(request_id, False, token_usage)
                logger.info(f"image converted to markdown with {llm_model_image}: {token_usage}")

            return DocumentConverterResult(
                markdown='\n```image_description\n' + content.strip() + '\n```\n',
            )
        except Exception as exc:
            logger.error(f'cannot convert image: {exc}')
            raise
