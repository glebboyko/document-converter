import base64
import logging
import mimetypes
import os
from typing import BinaryIO, Any

import openai
from markitdown import (
    MarkItDown,
    DocumentConverter,
    DocumentConverterResult,
    StreamInfo,
)
from redis import Redis

__plugin_interface_version__ = (
    1  # The version of the plugin interface that this plugin uses
)

ACCEPTED_MIME_TYPE_PREFIXES = [
    "image/jpeg",
    "image/png",
]

ACCEPTED_FILE_EXTENSIONS = [".jpg", ".jpeg", ".png"]


def register_converters(markitdown: MarkItDown, **kwargs):
    """
    Called during construction of MarkItDown instances to register converters provided by plugins.
    """

    # Simply create and attach an RtfConverter instance
    markitdown.register_converter(ImageConverter())


class ImageConverter(DocumentConverter):
    """
    Converts images to markdown via description via a multimodal LLM.
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
    def _get_llm_model(request_id: str) -> str:
        with ImageConverter._get_redis() as redis_client:
            llm_model = redis_client.hget(request_id, 'llm_model').decode()

        assert llm_model is not None

        return llm_model

    @staticmethod
    def _get_used_tokens(redis_client: Redis, request_id: str) -> tuple[int, int]:
        in_tokens = redis_client.hget(request_id, 'in_tokens') or 0
        out_tokens = redis_client.hget(request_id, 'out_tokens') or 0

        return int(in_tokens), int(out_tokens)

    @staticmethod
    def _set_used_tokens(redis_client: Redis, request_id: str, in_tokens: int, out_tokens: int):
        redis_client.hset(request_id, 'in_tokens', str(in_tokens))
        redis_client.hset(request_id, 'out_tokens', str(out_tokens))

    @staticmethod
    def _update_used_tokens(request_id: str, in_tokens: int, out_tokens: int):
        with ImageConverter._get_redis() as redis_client:
            curr_in_tokens, curr_out_tokens = ImageConverter._get_used_tokens(redis_client, request_id)
            ImageConverter._set_used_tokens(redis_client, request_id, curr_in_tokens + in_tokens,
                                            curr_out_tokens + out_tokens)

    @staticmethod
    def _convert_to_b64(file_stream: BinaryIO) -> str:
        cur_pos = file_stream.tell()
        try:
            b64 = base64.b64encode(file_stream.read()).decode("utf-8")
        finally:
            file_stream.seek(cur_pos)

        return b64

    def convert(
            self,
            file_stream: BinaryIO,
            stream_info: StreamInfo,
            **kwargs: Any,  # Options to pass to the converter
    ) -> DocumentConverterResult:
        logger = logging.getLogger('IC').getChild('CV')

        try:
            request_id = kwargs.get('request_id')
            prompt = kwargs.get('llm_prompt')

            api_key = kwargs.get('llm_api_key')
            base_url = kwargs.get('llm_base_url')

            llm_client = openai.Client(api_key=api_key, base_url=base_url)
            llm_model = self._get_llm_model(request_id)

            assert prompt is not None

            base_64_image = self._convert_to_b64(file_stream)

            content_type = stream_info.mimetype
            if not content_type:
                content_type, _ = mimetypes.guess_type(
                    "_dummy" + (stream_info.extension or "")
                )
            if not content_type:
                content_type = "application/octet-stream"

            messages = [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'input_text',
                            'text': prompt
                        },
                        {
                            'type': 'input_image',
                            'image_url': f'data:{content_type};base64,{base_64_image}'
                        }
                    ]
                }
            ]

            response = llm_client.responses.create(
                model=llm_model,
                input=messages
            )

            self._update_used_tokens(request_id, response.usage.input_tokens, response.usage.output_tokens)

            md_content = response.output_text

            logger.info(
                f"image converted successfully: {response.id}: {response.usage.input_tokens}, {response.usage.output_tokens}")

            return DocumentConverterResult(
                markdown=md_content,
            )
        except Exception as exc:
            logger.error(f'cannot convert image: {exc}')
            raise
