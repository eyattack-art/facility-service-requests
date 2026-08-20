from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.requests import router as request_router
from app.core.config import Settings
from app.core.exception import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.infrastructure.database.database_manager import DatabaseManager


def create_app(settings: Settings) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        app.state.database_manager = DatabaseManager(
            url=settings.database.url,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_pre_ping=settings.database.pool_pre_ping,
            pool_recycle=settings.database.pool_recycle,
            pool_timeout=settings.database.pool_timeout,
        )
        yield
        await app.state.database_manager.dispose()

    fastapi_app = FastAPI(lifespan=lifespan, title="Facility requests API")

    _setup_routers(fastapi_app)
    _exception_handler(fastapi_app)

    return fastapi_app


def _setup_routers(app: FastAPI) -> None:
    app.include_router(health_router)
    app.include_router(request_router)


def _exception_handler(app: FastAPI) -> None:

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_exception_handler(
        request: Request, exc: UnauthorizedError
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content={"message": str(exc)})

    @app.exception_handler(ForbiddenError)
    async def forbidden_exception_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"message": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict_exception_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"message": str(exc)})

    @app.exception_handler(NotFoundError)
    async def not_found_exception_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"message": str(exc)})

    @app.exception_handler(Exception)
    async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"message": "Внутренняя ошибка сервера"})
