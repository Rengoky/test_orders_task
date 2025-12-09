"""Request ID middleware for correlation."""
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging_config import request_id_ctx_var


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID for correlation."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        """Add request ID to context and headers."""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_ctx_var.set(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response



