from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ServiceRequest, User
from app.models.user import UserRole
from app.services.dto import ListRequestsFilterDTO


class ServiceRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, request: ServiceRequest) -> ServiceRequest:
        self._session.add(request)
        await self._session.flush()
        return request

    async def list_with_filters(
        self,
        current_user: User,
        filters: ListRequestsFilterDTO,
    ) -> tuple[list[ServiceRequest], int]:
        stmt = select(ServiceRequest)

        if current_user.role == UserRole.EMPLOYEE:
            stmt = stmt.where(ServiceRequest.facility_id == current_user.facility_id)
        elif current_user.role == UserRole.TECHNICIAN:
            stmt = stmt.where(ServiceRequest.assignee_id == current_user.id)

        if filters.status is not None:
            stmt = stmt.where(ServiceRequest.status == filters.status)
        if filters.category is not None:
            stmt = stmt.where(ServiceRequest.category == filters.category)
        if filters.priority is not None:
            stmt = stmt.where(ServiceRequest.priority == filters.priority)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            stmt.order_by(ServiceRequest.created_at.desc(), ServiceRequest.id.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

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
