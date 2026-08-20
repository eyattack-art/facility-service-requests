from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Facility


class FacilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, facility_id: UUID) -> Facility | None:
        return await self._session.get(Facility, facility_id)
