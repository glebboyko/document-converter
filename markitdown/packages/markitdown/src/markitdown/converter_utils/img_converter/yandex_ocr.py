from __future__ import annotations

import json
from typing import BinaryIO
from typing import Optional

import requests
from pydantic import BaseModel

from .image_encoders import encode_base64


class Block(BaseModel):
    class Coordinate(BaseModel):
        x: int
        y: int

    class BoundingBox(BaseModel):
        top_left: Block.Coordinate
        bottom_left: Block.Coordinate
        bottom_right: Block.Coordinate
        top_right: Block.Coordinate

    text: str
    bounding_box: BoundingBox
    orientation: str


class Image(BaseModel):
    width: int
    height: int
    blocks: list[Block]

    @staticmethod
    def from_yandex(data) -> Optional[Image]:
        width = int(data.get('result', {}).get('textAnnotation', {}).get('width', 0))
        height = int(data.get('result', {}).get('textAnnotation', {}).get('height', 0))

        if not data.get('result', {}).get('textAnnotation', {}).get('fullText'):
            return None

        blocks = []

        for raw_block in data['result']['textAnnotation']['blocks']:
            for line in raw_block['lines']:
                vertices = line['boundingBox']['vertices']

                block = Block(
                    text=line['text'],
                    bounding_box=Block.BoundingBox(
                        top_left=Block.Coordinate(
                            x=int(vertices[0]['x']),
                            y=int(vertices[0]['y'])
                        ),
                        bottom_left=Block.Coordinate(
                            x=int(vertices[1]['x']),
                            y=int(vertices[1]['y'])
                        ),
                        bottom_right=Block.Coordinate(
                            x=int(vertices[2]['x']),
                            y=int(vertices[2]['y'])
                        ),
                        top_right=Block.Coordinate(
                            x=int(vertices[3]['x']),
                            y=int(vertices[3]['y'])
                        )
                    ),
                    orientation=line['orientation']
                )

                blocks.append(block)

        return Image(
            width=width,
            height=height,
            blocks=blocks
        )


def process_image(file_stream: BinaryIO, api_key: str) -> Optional[Image]:
    data = {
        'content': encode_base64(file_stream),
        'languageCodes': ['ru', 'en'],
    }
    headers = {
        'Authorization': f'Api-Key {api_key}'
    }

    response = requests.post(
        url='https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText',
        data=json.dumps(data),
        headers=headers
    )

    response.raise_for_status()

    return Image.from_yandex(response.json())
