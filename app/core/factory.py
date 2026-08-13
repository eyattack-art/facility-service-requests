from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings
from app.infrastructure.database.database_manager import DatabaseManager


def create_app(settings: Settings) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.database_manager = DatabaseManager(
            url=settings.database.url,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_pre_ping=settings.database.pool_pre_ping,
            pool_recycle=settings.database.pool_recycle,
            pool_timeout=settings.database.pool_timeout
        )
        yield
        await app.state.database_manager.dispose()

    fastapi_app = FastAPI(lifespan=lifespan, title="Facility requests API")

    return fastapi_app