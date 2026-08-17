from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.facility_repository import FacilityRepository
from app.repositories.service_request_repository import ServiceRequestRepository
from app.repositories.status_history_repository import StatusHistoryRepository
from app.repositories.user_repository import UserRepository


class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.user_repository = UserRepository(self._session)
        self.facility_repository = FacilityRepository(self._session)
        self.service_request_repository = ServiceRequestRepository(self._session)
        self.status_history_repository = StatusHistoryRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self._session.rollback()
        else:
            try:
                await self._session.commit()
            except Exception:
                await self._session.rollback()
                raise
        await self._session.close()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("UoW не активен")
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("UoW не активен")
        await self._session.rollback()

    async def flush(self) -> None:
        if self._session is None:
            raise RuntimeError("UoW не активен")
        await self._session.flush()

    async def refresh(self, instance: object) -> None:
        if self._session is None:
            raise RuntimeError("UoW не активен")

        await self._session.refresh(instance)
