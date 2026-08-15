from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Facility


class FacilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_facility_by_id(self, facility_id: UUID) -> Facility | None:
        return await self._session.get(Facility, facility_id)

    async def get_facility_by_name(self, facility_name: str) -> Facility | None:
        result = await self._session.execute(select(Facility).where(Facility.name == facility_name))
        return result.scalar_one_or_none()

