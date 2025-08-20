FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg

WORKDIR /document_converter

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY markitdown/packages/markitdown markitdown

RUN pip3 install ./markitdown[all]

COPY service service

COPY docs docs

ENTRYPOINT ["uvicorn"]
CMD ["service.__main__:app", "--host", "0.0.0.0", "--port", "8000"]