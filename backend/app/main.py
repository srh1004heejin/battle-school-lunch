import logging
import os
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings
from app.errors import AppError
from app.models import ErrorDetail, ErrorResponse
from app.neis import NeisClient
from app.routes import router

logger = logging.getLogger(__name__)


def _error_response(
    request: Request, status_code: int, code: str, message: str
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    body = ErrorResponse(
        error=ErrorDetail(code=code, message=message, request_id=request_id)
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(by_alias=True))


def create_app(
    settings: Settings | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        runtime_settings = settings or Settings()
        client = NeisClient(runtime_settings, transport=transport)
        app.state.neis_client = client
        try:
            yield
        finally:
            await client.aclose()

    app = FastAPI(title="급식 배틀 API", version="1.0.0", lifespan=lifespan)
    if settings is not None:
        origins = settings.allowed_origins
    else:
        cors_value = os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
        )
        origins = [origin.strip() for origin in cors_value.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "request_failed request_id=%s code=%s status=%s",
            getattr(request.state, "request_id", "unknown"),
            exc.code,
            exc.status_code,
        )
        return _error_response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del exc
        return _error_response(
            request,
            422,
            "INPUT_VALIDATION_ERROR",
            "요청 매개변수가 API 계약을 충족하지 않습니다.",
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        message = (
            "요청한 리소스를 찾을 수 없습니다."
            if exc.status_code == 404
            else "요청을 처리할 수 없습니다."
        )
        return _error_response(request, exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unexpected_error request_id=%s",
            getattr(request.state, "request_id", "unknown"),
            exc_info=exc,
        )
        return _error_response(
            request, 500, "INTERNAL_ERROR", "서버에서 요청을 처리하지 못했습니다."
        )

    app.include_router(router)
    return app


app = create_app()
