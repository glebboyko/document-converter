import json
from dataclasses import dataclass
from typing import Any, BinaryIO

from openai import Client as LlmClient

from .image_encoders import encode_gpt_url
from .prompts import (
    OCR_TO_TABLE,
    COMPOSED_IMAGE_TO_MARKDOWN,
    GRAPHIC_IMAGE_TO_MARKDOWN,
    MERGE_SEGMENTED_IMAGE_TO_MARKDOWN
)
from .yandex_ocr import Image

@dataclass
class TokenUsage:
    input: int
    output: int


def ocr_to_table(image: Image, llm_client: LlmClient, llm_model: str) -> tuple[str, TokenUsage]:
    messages = [
        {
            'role': 'system',
            'content': [
                {
                    'type': 'input_text',
                    'text': OCR_TO_TABLE
                }
            ]
        },
        {
            'role': 'user',
            'content': [
                {
                    'type': 'input_text',
                    'text': image.model_dump_json()
                }
            ]
        }
    ]

    response = llm_client.responses.create(
        model=llm_model,
        input=messages
    )

    token_usage = TokenUsage(
        input=response.usage.input_tokens,
        output=response.usage.output_tokens
    )

    return response.output_text, token_usage


def composed_image_to_markdown(file_stream: BinaryIO, image_table: str, llm_client: LlmClient,
                               llm_model: str) -> tuple[str, TokenUsage]:
    messages = [
        {
            'role': 'system',
            'content': [
                {
                    'type': 'input_text',
                    'text': COMPOSED_IMAGE_TO_MARKDOWN
                }
            ]
        },
        {
            'role': 'user',
            'content': [
                {
                    'type': 'input_text',
                    'text': image_table
                },
                {
                    'type': 'input_image',
                    'image_url': encode_gpt_url(file_stream)
                }
            ]
        }
    ]

    response = llm_client.responses.create(
        model=llm_model,
        input=messages
    )

    token_usage = TokenUsage(
        input=response.usage.input_tokens,
        output=response.usage.output_tokens
    )

    return response.output_text, token_usage


def graphic_image_to_markdown(file_stream: BinaryIO, llm_client: LlmClient, llm_model: str) -> \
tuple[str, TokenUsage]:
    messages = [
        {
            'role': 'system',
            'content': [
                {
                    'type': 'input_text',
                    'text': GRAPHIC_IMAGE_TO_MARKDOWN
                }
            ]
        },
        {
            'role': 'user',
            'content': [
                {
                    'type': 'input_image',
                    'image_url': encode_gpt_url(file_stream)
                }
            ]
        }
    ]

    response = llm_client.responses.create(
        model=llm_model,
        input=messages
    )

    token_usage = TokenUsage(
        input=response.usage.input_tokens,
        output=response.usage.output_tokens
    )

    return response.output_text, token_usage


def merge_segmented_image_to_markdown(
        file_stream: BinaryIO,
        chunk_artifacts: list[dict[str, Any]],
        llm_client: LlmClient,
        llm_model: str
) -> tuple[str, TokenUsage]:
    messages = [
        {
            'role': 'system',
            'content': [
                {
                    'type': 'input_text',
                    'text': MERGE_SEGMENTED_IMAGE_TO_MARKDOWN
                }
            ]
        },
        {
            'role': 'user',
            'content': [
                {
                    'type': 'input_text',
                    'text': json.dumps(chunk_artifacts, ensure_ascii=True, indent=2)
                },
                {
                    'type': 'input_image',
                    'image_url': encode_gpt_url(file_stream)
                }
            ]
        }
    ]

    response = llm_client.responses.create(
        model=llm_model,
        input=messages
    )

    token_usage = TokenUsage(
        input=response.usage.input_tokens,
        output=response.usage.output_tokens
    )

    return response.output_text, token_usage
