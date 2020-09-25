import logging
from http import HTTPStatus
from typing import Mapping, Optional

from aiohttp.web_exceptions import (
    HTTPBadRequest, HTTPException, HTTPInternalServerError,
)
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request

from file_loader.utils.exception import ValidationError

log = logging.getLogger(__name__)


def format_http_error(http_error_cls, message: Optional[str] = None,
                      fields: Optional[Mapping] = None) -> HTTPException:
    """
    Formats the error as an HTTP exception
    """
    status = HTTPStatus(http_error_cls.status_code)
    error = {
        'code': http_error_cls.status_code,
        'message': message or status.description
    }

    if fields:
        error['additional_info'] = fields

    return http_error_cls(body={'error': error})


def handle_validation_error(error: ValidationError, *_):
    """
    A data validation error as an HTTP response
    """
    raise format_http_error(HTTPBadRequest, 'Request validation has failed',
                            error.message)


@middleware
async def error_middleware(request: Request, handler):
    try:
        return await handler(request)
    except HTTPException as err:
        raise format_http_error(err.__class__, err.text)

    except ValidationError as err:
        # Validation errors thrown in handlers
        raise handle_validation_error(err)

    except Exception:
        # All other exceptions cannot be displayed to the client
        # as an HTTP response and can reveal internal information.
        log.exception('Unhandled exception')
        raise format_http_error(HTTPInternalServerError)
