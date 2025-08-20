import base64
from typing import BinaryIO
from markitdown import StreamInfo
import mimetypes

def encode_base64(file_stream: BinaryIO) -> str:
    cur_pos = file_stream.tell()
    try:
        b64 = base64.b64encode(file_stream.read()).decode("utf-8")
    finally:
        file_stream.seek(cur_pos)

    return b64

def encode_gpt_url(file_stream: BinaryIO, stream_info: StreamInfo) -> str:
    base64_image = encode_base64(file_stream)

    content_type = stream_info.mimetype
    if not content_type:
        content_type, _ = mimetypes.guess_type(
            "_dummy" + (stream_info.extension or "")
        )
    if not content_type:
        content_type = "application/octet-stream"

    return f'data:{content_type};base64,{base64_image}'