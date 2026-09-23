from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None

    response.data = {
        "error": {
            "code": getattr(exc, "default_code", "api_error"),
            "details": response.data,
        }
    }
    return response
