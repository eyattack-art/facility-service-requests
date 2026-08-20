from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StatusHistory


class StatusHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: StatusHistory) -> StatusHistory:
        self._session.add(entry)
        await self._session.flush()
        return entry
