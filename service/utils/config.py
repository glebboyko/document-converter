from __future__ import annotations

from datetime import timedelta
from os import environ

from pydantic import BaseModel
from typing import Optional


class Config(BaseModel):
    class AuthConfig(BaseModel):
        cache_valid_delta: timedelta
        api_keys_hash: list[str]

    class Running(BaseModel):
        logging_level: int

    class Openai(BaseModel):
        api_key: str
        default_model: str
        base_url: Optional[str] = None


    auth: AuthConfig
    openai: Openai
    running: Running

    @staticmethod
    def get_config() -> Config:
        with open(environ['CONFIG_PATH']) as config_file:
            return Config.model_validate_json(config_file.read())
