import logging
from types import MappingProxyType
from typing import Mapping

from aiohttp import PAYLOAD_REGISTRY, JsonPayload
from aiohttp.web_app import Application

from file_loader.api.middleware import error_middleware
from file_loader.api.handlers import HANDLERS

logger = logging.getLogger(__name__)


def create_app() -> Application:
    """
    Creates an instance of the application. This one is ready to run.
    """
    app = Application(
        middlewares=[error_middleware, ]
    )

    for handler in HANDLERS:
        logger.debug('Registering handler %r as %r', handler, handler.URL_PATH)
        app.router.add_route('*', handler.URL_PATH, handler)

    PAYLOAD_REGISTRY.register(JsonPayload, (Mapping, MappingProxyType))
    return app
