from __future__ import annotations

import logging
from os import environ

from pydantic import BaseModel
from typing import Optional


class Config(BaseModel):
    class Running(BaseModel):
        logging_level: int

    class Openai(BaseModel):
        api_key: str
        default_model_ocr: str
        default_model_image: str
        base_url: Optional[str] = None

    openai: Openai
    yandex_ocr_api_key: str

    running: Running

    @staticmethod
    def get_config() -> Config:
        return Config(
            openai=Config.Openai(
                api_key=environ['OPENAI_API_KEY'],
                default_model_ocr=environ['OPENAI_DEFAULT_MODEL_OCR'],
                default_model_image=environ['OPENAI_DEFAULT_MODEL_IMAGE'],
                base_url=environ.get('OPENAI_BASE_URL') or None,
            ),
            yandex_ocr_api_key=environ['YANDEX_OCR_API_KEY'],
            running=Config.Running(
                logging_level=logging.getLevelNamesMapping().get(
                    environ.get('LOGGING_LEVEL', 'INFO').upper(),
                    logging.INFO,
                ),
            ),
        )
