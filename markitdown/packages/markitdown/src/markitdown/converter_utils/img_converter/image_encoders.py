import base64
import io
import os
import subprocess
import tempfile
from dataclasses import dataclass
from logging import Logger
from typing import BinaryIO

import cairosvg
from PIL import Image as PilImage

from ..._stream_info import StreamInfo

MAX_IMAGE_CHUNK_SIZE = 2000
DEFAULT_IMAGE_CHUNK_OVERLAP = 200


@dataclass(frozen=True)
class ImageChunk:
    index: int
    left: int
    top: int
    right: int
    bottom: int
    stream: io.BytesIO


def _read_bytes(file_stream: BinaryIO) -> bytes:
    cur_pos = file_stream.tell()
    try:
        return file_stream.read()
    finally:
        file_stream.seek(cur_pos)


def _calculate_axis_ranges(length: int, block_size: int, overlap: int) -> list[tuple[int, int]]:
    if length <= block_size:
        return [(0, length)]

    if block_size <= overlap:
        raise ValueError("block_size must be greater than overlap")

    stride = block_size - overlap
    ranges = []
    start = 0
    while start < length:
        end = min(start + block_size, length)
        ranges.append((start, end))
        if end == length:
            break
        start += stride

    return ranges


def get_image_size(file_stream: BinaryIO) -> tuple[int, int]:
    image_bytes = _read_bytes(file_stream)

    with PilImage.open(io.BytesIO(image_bytes)) as image:
        return image.width, image.height


def _emf_to_svg(emf_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as outdir:
        source_file = os.path.join(outdir, 'source.emf')
        target_file = os.path.join(outdir, os.path.splitext(os.path.basename(source_file))[0] + '.svg')

        with open(source_file, 'wb') as file:
            file.write(emf_bytes)

        subprocess.run(
            [
                'libreoffice',
                '--headless',
                '--convert-to', 'svg',
                '--outdir', outdir,
                source_file
            ], check=True
        )

        with open(target_file, 'rb') as file:
            return file.read()


def _svg_to_png(svg_bytes: bytes) -> bytes:
    return cairosvg.svg2png(dpi=300, bytestring=svg_bytes)


def to_png(p_logger: Logger, file_stream: BinaryIO, stream_info: StreamInfo) -> BinaryIO:
    logger = p_logger.getChild('TO-PNG')
    image_bytes = _read_bytes(file_stream)

    if stream_info.mimetype == 'image/x-emf':
        svg_bytes = _emf_to_svg(image_bytes)
        png_bytes = _svg_to_png(svg_bytes)
        return io.BytesIO(png_bytes)

    if stream_info.mimetype == 'image/svg+xml':
        png_bytes = _svg_to_png(image_bytes)
        return io.BytesIO(png_bytes)

    with tempfile.TemporaryDirectory() as out_dir:
        cmd = [
            "ffmpeg",
            "-hide_banner", "-loglevel", "error",
            "-i", "pipe:0",
            "-f", "image2",
            "-c:v", "png",
            "-y",
            os.path.join(out_dir, '%03d.png')
        ]
        try:
            subprocess.run(
                cmd,
                input=image_bytes,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg conversion failed: {e.stderr.decode() if e.stderr else None}") from e

        imgs = []
        for file_path in sorted(os.listdir(out_dir)):
            file_path = os.path.join(out_dir, file_path)
            with open(file_path, 'rb') as file:
                imgs.append(io.BytesIO(file.read()))

    return imgs[-1]


def split_to_png_chunks(
        p_logger: Logger,
        file_stream: BinaryIO,
        block_size: int = MAX_IMAGE_CHUNK_SIZE,
        overlap: int = DEFAULT_IMAGE_CHUNK_OVERLAP
) -> list[ImageChunk]:
    logger = p_logger.getChild('SP')

    try:
        image_bytes = _read_bytes(file_stream)

        with PilImage.open(io.BytesIO(image_bytes)) as image:
            normalized_image = image.convert('RGB')
            x_ranges = _calculate_axis_ranges(normalized_image.width, block_size, overlap)
            y_ranges = _calculate_axis_ranges(normalized_image.height, block_size, overlap)

            chunks = []
            chunk_idx = 1
            for top, bottom in y_ranges:
                for left, right in x_ranges:
                    cropped = normalized_image.crop((left, top, right, bottom))
                    chunk_stream = io.BytesIO()
                    cropped.save(chunk_stream, format='PNG')
                    chunk_stream.seek(0)

                    chunks.append(ImageChunk(
                        index=chunk_idx,
                        left=left,
                        top=top,
                        right=right,
                        bottom=bottom,
                        stream=chunk_stream
                    ))
                    chunk_idx += 1

            logger.debug(
                f'split image {normalized_image.width}x{normalized_image.height} into {len(chunks)} '
                f'chunks of up to {block_size}x{block_size} with overlap {overlap}'
            )
            return chunks
    except Exception as exc:
        logger.error(f'cannot split image into chunks: {exc}')
        raise


def encode_base64(file_stream: BinaryIO) -> str:
    b64 = base64.b64encode(_read_bytes(file_stream)).decode("utf-8")

    return b64


def encode_gpt_url(file_stream: BinaryIO) -> str:
    base64_image = encode_base64(file_stream)

    return f'data:image/png;base64,{base64_image}'
