import base64
import io
import os
import subprocess
import tempfile
from typing import BinaryIO
from logging import Logger

import cairosvg

from ..._stream_info import StreamInfo


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
    cur_pos = file_stream.tell()
    try:
        image_bytes = file_stream.read()
    finally:
        file_stream.seek(cur_pos)

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
            proc = subprocess.run(
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


def encode_base64(file_stream: BinaryIO) -> str:
    cur_pos = file_stream.tell()
    try:
        b64 = base64.b64encode(file_stream.read()).decode("utf-8")
    finally:
        file_stream.seek(cur_pos)

    return b64


def encode_gpt_url(file_stream: BinaryIO) -> str:
    base64_image = encode_base64(file_stream)

    return f'data:image/png;base64,{base64_image}'
