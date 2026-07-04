from collections import defaultdict, deque
from time import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..config import get_settings

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if settings.ENABLE_SECURITY_HEADERS:
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
            response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._requests = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if not settings.ENABLE_RATE_LIMITING:
            return await call_next(request)

        client_ip = request.client.host if request.client else 'unknown'
        key = f"{client_ip}:{request.url.path}"
        now = time()
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        limit = settings.RATE_LIMIT_MAX_REQUESTS

        bucket = self._requests[key]
        while bucket and (now - bucket[0]) > window:
            bucket.popleft()

        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={'detail': 'Rate limit exceeded. Please retry shortly.'},
            )

        bucket.append(now)
        return await call_next(request)
