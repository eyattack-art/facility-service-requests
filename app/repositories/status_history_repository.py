from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StatusHistory


class StatusHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: StatusHistory) -> StatusHistory:
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_by_request_id(self, request_id: UUID) -> list[StatusHistory]:
        stmt = (
            select(StatusHistory)
            .where(StatusHistory.request_id == request_id)
            .order_by(StatusHistory.created_at, StatusHistory.id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
