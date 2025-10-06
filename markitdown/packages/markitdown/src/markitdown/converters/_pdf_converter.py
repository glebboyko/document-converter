import io
import logging
import sys
from typing import BinaryIO, Any

from pdfminer.layout import LTTextContainer, LTImage, LTFigure

from ._image_converter import ImageConverter
from .._base_converter import DocumentConverter, DocumentConverterResult
from .._exceptions import MissingDependencyException, MISSING_DEPENDENCY_MESSAGE
from .._stream_info import StreamInfo

# Try loading optional (but in this case, required) dependencies
# Save reporting of any exceptions for later
_dependency_exc_info = None
try:
    import pdfminer
    import pdfminer.high_level
except ImportError:
    # Preserve the error and stack trace for later
    _dependency_exc_info = sys.exc_info()

ACCEPTED_MIME_TYPE_PREFIXES = [
    "application/pdf",
    "application/x-pdf",
]

ACCEPTED_FILE_EXTENSIONS = [".pdf"]


class PdfConverter(DocumentConverter):
    """
    Converts PDFs to Markdown. Most style information is ignored, so the results are essentially plain-text.
    """

    def accepts(
            self,
            file_stream: BinaryIO,
            stream_info: StreamInfo,
            **kwargs: Any,  # Options to pass to the converter
    ) -> bool:
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()

        if extension in ACCEPTED_FILE_EXTENSIONS:
            return True

        for prefix in ACCEPTED_MIME_TYPE_PREFIXES:
            if mimetype.startswith(prefix):
                return True

        return False

    def convert(
            self,
            file_stream: BinaryIO,
            stream_info: StreamInfo,
            **kwargs: Any,  # Options to pass to the converter
    ) -> DocumentConverterResult:
        request_id = kwargs.get('request_id')
        logger = logging.getLogger(f'PDF_CONVERTER:{request_id}')

        logger.info("launching pdf converter...")

        # Check the dependencies
        if _dependency_exc_info is not None:
            raise MissingDependencyException(
                MISSING_DEPENDENCY_MESSAGE.format(
                    converter=type(self).__name__,
                    extension=".pdf",
                    feature="pdf",
                )
            ) from _dependency_exc_info[
                1
            ].with_traceback(  # type: ignore[union-attr]
                _dependency_exc_info[2]
            )

        assert isinstance(file_stream, io.IOBase)  # for mypy

        out = io.StringIO()
        for page_no, layout in enumerate(pdfminer.high_level.extract_pages(file_stream), start=1):
            for element in layout:
                if isinstance(element, LTTextContainer):
                    out.write(element.get_text())
                elif isinstance(element, (LTImage, LTFigure)):
                    for img in self._iter_images(element):
                        file_stream = io.BytesIO(img.stream.get_data())

                        try:
                            extension = f".{img.name.split('.')[-1]}"
                        except Exception:
                            extension = None
                        stream_info = StreamInfo(extension=extension)

                        out.write(ImageConverter().convert(file_stream, stream_info, **kwargs).text_content)

        out.seek(0)

        return DocumentConverterResult(
            markdown=out.read(),
        )

    @staticmethod
    def _iter_images(layout_obj):
        # Recursively yield LTImage objects
        if isinstance(layout_obj, LTImage):
            yield layout_obj
        if isinstance(layout_obj, LTFigure):
            for obj in layout_obj:
                yield from PdfConverter._iter_images(obj)
