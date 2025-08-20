import logging

from .utils.config import Config

logging.basicConfig(format='%(asctime)s\t| %(name)s\t| %(levelname)s\t: %(message)s',
                    level=Config.get_config().running.logging_level)

from fastapi import FastAPI
from . import routing
import yaml

app = FastAPI()


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    with open("docs/endpoints.yaml") as f:
        openapi_schema = yaml.safe_load(f)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.include_router(routing.v1.router)
