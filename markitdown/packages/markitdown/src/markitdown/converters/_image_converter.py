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

    def _convert_single_image(
            self,
            p_logger: logging.Logger,
            request_id: str,
            file_stream: BinaryIO,
            ocr_api_key: str,
            llm_client: openai.Client,
            llm_model_table: str,
            llm_model_image: str
    ) -> tuple[str, dict[str, Any]]:
        logger = p_logger.getChild('SI')
        image_table = None

        ocr_image = yandex_ocr.process_image(file_stream, ocr_api_key)

        if ocr_image:
            logger.info("image contains text. converting to table...")
            image_table, token_usage = gpt_vision.ocr_to_table(ocr_image, llm_client, llm_model_table)
            self._update_used_tokens(request_id, True, token_usage)
            logger.info(f"image converted to table with {llm_model_table}: {token_usage}")

            content, token_usage = gpt_vision.composed_image_to_markdown(
                file_stream,
                image_table,
                llm_client,
                llm_model_image
            )
            self._update_used_tokens(request_id, False, token_usage)
            logger.info(f"image converted to markdown with {llm_model_image}: {token_usage}")
        else:
            logger.info("image does not contain text. converting to markdown...")
            content, token_usage = gpt_vision.graphic_image_to_markdown(file_stream, llm_client, llm_model_image)
            self._update_used_tokens(request_id, False, token_usage)
            logger.info(f"image converted to markdown with {llm_model_image}: {token_usage}")

        return content, {
            'contains_text': ocr_image is not None,
            'ocr_table': image_table,
            'markdown': content.strip()
        }

    def _convert_large_image(
            self,
            p_logger: logging.Logger,
            request_id: str,
            file_stream: BinaryIO,
            ocr_api_key: str,
            llm_client: openai.Client,
            llm_model_table: str,
            llm_model_image: str
    ) -> str:
        logger = p_logger.getChild('LI')
        chunks = image_encoders.split_to_png_chunks(p_logger, file_stream)
        chunk_artifacts = []

        logger.info(f"processing large image in {len(chunks)} overlapping chunks...")
        for chunk in chunks:
            logger.info(
                f"processing chunk {chunk.index}/{len(chunks)}: "
                f"({chunk.left}, {chunk.top}) -> ({chunk.right}, {chunk.bottom})"
            )
            _, chunk_artifact = self._convert_single_image(
                logger,
                request_id,
                chunk.stream,
                ocr_api_key,
                llm_client,
                llm_model_table,
                llm_model_image
            )
            chunk_artifacts.append({
                'chunk_index': chunk.index,
                'bounds': {
                    'left': chunk.left,
                    'top': chunk.top,
                    'right': chunk.right,
                    'bottom': chunk.bottom
                },
                **chunk_artifact
            })

        logger.info("merging chunk artifacts with the full image...")
        content, token_usage = gpt_vision.merge_segmented_image_to_markdown(
            file_stream,
            chunk_artifacts,
            llm_client,
            llm_model_image
        )
        self._update_used_tokens(request_id, False, token_usage)
        logger.info(f"large image merged to markdown with {llm_model_image}: {token_usage}")

        return content

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
            is_page = kwargs.get('image_is_page', False)

            llm_client = openai.Client(api_key=llm_api_key, base_url=base_url)
            llm_model_table, llm_model_image = self._get_llm_models(request_id)

            file_stream = image_encoders.to_png(logger, file_stream, stream_info)
            width, height = image_encoders.get_image_size(file_stream)

            if width > image_encoders.MAX_IMAGE_CHUNK_SIZE or height > image_encoders.MAX_IMAGE_CHUNK_SIZE:
                logger.info(
                    f"image size {width}x{height} exceeds {image_encoders.MAX_IMAGE_CHUNK_SIZE}x"
                    f"{image_encoders.MAX_IMAGE_CHUNK_SIZE}. switching to chunked OCR flow..."
                )
                content = self._convert_large_image(
                    logger,
                    request_id,
                    file_stream,
                    ocr_api_key,
                    llm_client,
                    llm_model_table,
                    llm_model_image
                )
            else:
                content, _ = self._convert_single_image(
                    logger,
                    request_id,
                    file_stream,
                    ocr_api_key,
                    llm_client,
                    llm_model_table,
                    llm_model_image
                )

            result = content.strip() + '\n'
            if not is_page:
                result = '\n```image_description\n' + result + '```\n'
            return DocumentConverterResult(
                markdown=result,
            )
        except Exception as exc:
            logger.error(f'cannot convert image: {exc}')
            raise
