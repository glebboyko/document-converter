import base64
from typing import BinaryIO

import subprocess
import io


def to_png(file_stream: BinaryIO) -> BinaryIO:
    cur_pos = file_stream.tell()
    try:
        image_bytes = file_stream.read()
    finally:
        file_stream.seek(cur_pos)

    cmd = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "error",
        "-i", "pipe:0",
        "-f", "image2",
        "-c:v", "png",
        "-y",
        "pipe:1"
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=image_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg conversion failed: {e.stderr.decode()}") from e

    return io.BytesIO(proc.stdout)


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