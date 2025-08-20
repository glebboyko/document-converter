FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg

WORKDIR /document_converter

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY markitdown_ocr_plugin markitdown_ocr_plugin

RUN pip3 install -e markitdown_ocr_plugin

COPY service service

COPY docs docs

ENTRYPOINT ["uvicorn"]
CMD ["service.__main__:app", "--host", "0.0.0.0", "--port", "8000"]