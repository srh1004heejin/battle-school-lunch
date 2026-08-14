from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import json
import logging
import time
import uuid

import httpx
from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .errors import ApiError
from .models import ErrorResponse, HealthResponse, MealSearchResponse, SchoolSearchResponse
from .neis_client import NeisClient
from .settings import Settings
from .validation import parse_api_date, validate_date_range, validate_school_identifier, validate_search_query

logger = logging.getLogger("battle_school_lunch")


def create_app(
    settings: Settings | None = None,
    neis_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    config = settings or Settings.from_env()
    neis_client = NeisClient(config, transport=neis_transport)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            await neis_client.aclose()

    app = FastAPI(title=config.app_name, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.settings = config
    app.state.neis_client = neis_client

    if config.backend_cors_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[config.backend_cors_origin],
            allow_credentials=False,
            allow_methods=["GET"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        started_at = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )
        return response

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        logger.warning(
            "api_error",
            extra={
                "request_id": request.state.request_id,
                "path": request.url.path,
                "status_code": exc.status_code,
                "error_code": exc.code,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error={
                    "code": exc.code,
                    "message": exc.message,
                    "requestId": request.state.request_id,
                }
            ).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        logger.warning(
            "request_validation_error",
            extra={
                "request_id": request.state.request_id,
                "path": request.url.path,
                "status_code": 422,
                "error_code": "INVALID_REQUEST",
            },
        )
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error={
                    "code": "INVALID_REQUEST",
                    "message": "요청 형식이 올바르지 않습니다.",
                    "requestId": request.state.request_id,
                }
            ).model_dump(mode="json"),
        )

    def custom_openapi() -> dict[str, object]:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_path = Path(__file__).resolve().parents[2] / "src" / "openapi.json"
        app.openapi_schema = json.loads(openapi_path.read_text(encoding="utf-8"))
        return app.openapi_schema

    app.openapi = custom_openapi

    def get_neis_client(request: Request) -> NeisClient:
        return request.app.state.neis_client

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/api/schools",
        response_model=SchoolSearchResponse,
        responses={
            400: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            502: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            504: {"model": ErrorResponse},
        },
    )
    async def search_schools(query: str = Query(...), client: NeisClient = Depends(get_neis_client)) -> SchoolSearchResponse:
        normalized_query = validate_search_query(query)
        schools = await client.search_schools(normalized_query)
        return SchoolSearchResponse(schools=schools)

    @app.get(
        "/api/schools/{education_office_code}/{school_code}/meals",
        response_model=MealSearchResponse,
        response_model_exclude_none=True,
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            502: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            504: {"model": ErrorResponse},
        },
    )
    async def get_meals(
        education_office_code: str,
        school_code: str,
        from_date_value: str = Query(..., alias="from"),
        to_date_value: str = Query(..., alias="to"),
        meal_type: str = Query(..., alias="mealType"),
        client: NeisClient = Depends(get_neis_client),
    ) -> MealSearchResponse:
        normalized_education_office_code = validate_school_identifier(education_office_code, "educationOfficeCode")
        normalized_school_code = validate_school_identifier(school_code, "schoolCode")

        if meal_type != "lunch":
            raise ApiError(422, "UNSUPPORTED_MEAL_TYPE", "현재는 중식 조회만 지원합니다.")

        from_date = parse_api_date(from_date_value, "from")
        to_date = parse_api_date(to_date_value, "to")
        validate_date_range(from_date, to_date, config.max_date_range_days)

        school = await client.get_school(normalized_education_office_code, normalized_school_code)
        if school is None:
            raise ApiError(404, "SCHOOL_NOT_FOUND", "선택한 학교를 찾을 수 없습니다.")

        meals = await client.get_lunch_meals(
            normalized_education_office_code,
            normalized_school_code,
            from_date.isoformat(),
            to_date.isoformat(),
        )

        return MealSearchResponse.model_validate(
            {
                "school": school.model_dump(),
                "from": from_date,
                "to": to_date,
                "meals": [meal.model_dump(mode="json") for meal in meals],
            }
        )

    return app


app = create_app()
