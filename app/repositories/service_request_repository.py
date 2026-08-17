from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ServiceRequest


class ServiceRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, request: ServiceRequest) -> ServiceRequest:
        self._session.add(request)
        await self._session.flush()
        return request

    async def get_by_id_with_history(self, request_id: UUID) -> ServiceRequest | None:
        result = await self._session.execute(
            select(ServiceRequest)
            .where(ServiceRequest.id == request_id)
            .options(selectinload(ServiceRequest.history))
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, request_id: UUID) -> ServiceRequest | None:
        result = await self._session.execute(
            select(ServiceRequest).where(ServiceRequest.id == request_id).with_for_update()
        )
        return result.scalar_one_or_none()
