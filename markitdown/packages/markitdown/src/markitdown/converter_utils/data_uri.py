import base64
import io
import re
from typing import BinaryIO

from .._stream_info import StreamInfo


def parse_data_uri(src: str) -> tuple[BinaryIO, StreamInfo]:
    pattern = r"^data:([\w/+.-]+/[\w.+-]+);base64,([a-zA-Z0-9+/=\n\r]+)"

    match = re.match(pattern, src)
    mimetype = match.group(1)
    base64_data = match.group(2)

    return io.BytesIO(base64.b64decode(base64_data)), StreamInfo(mimetype=mimetype)
