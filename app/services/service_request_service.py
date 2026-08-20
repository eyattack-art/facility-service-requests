from datetime import UTC, datetime
from uuid import UUID

from app.core.exception import ConflictError, NotFoundError
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.models import ServiceRequest, StatusHistory, User
from app.models.service_request import RequestStatus
from app.models.user import UserRole
from app.services.dto import (
    AssignRequestDTO,
    CancelRequestDTO,
    CompleteRequestDTO,
    CreateRequestDTO,
    ListRequestsFilterDTO,
    ListRequestsResultDTO,
)


class ServiceRequestService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create_request(self, current_user: User, data: CreateRequestDTO) -> ServiceRequest:
        async with self._uow as uow:
            assert current_user.facility_id is not None

            facility = await uow.facility_repository.get_by_id(current_user.facility_id)
            if facility is None or not facility.is_active:
                raise ConflictError("Объект неактивен")

            request = ServiceRequest(
                facility_id=current_user.facility_id,
                author_id=current_user.id,
                title=data.title,
                description=data.description,
                category=data.category,
                priority=data.priority,
                status=RequestStatus.NEW,
            )
            await uow.service_request_repository.add(request)

            history_entry = StatusHistory(
                request_id=request.id,
                old_status=None,
                new_status=RequestStatus.NEW,
                changed_by=current_user.id,
                comment=None,
            )
            await uow.status_history_repository.add(history_entry)

            return request

    async def list_requests(
        self, current_user: User, filters: ListRequestsFilterDTO
    ) -> ListRequestsResultDTO:
        async with self._uow as uow:
            items, total = await uow.service_request_repository.list_with_filters(
                current_user, filters
            )

            return ListRequestsResultDTO(
                items=items, total=total, limit=filters.limit, offset=filters.offset
            )

    async def get_request_by_id(self, current_user: User, request_id: UUID) -> ServiceRequest:
        async with self._uow as uow:
            request = await uow.service_request_repository.get_by_id_with_history(request_id)

            if request is None:
                raise NotFoundError("Заявка не найдена")
            if not self._has_access(current_user, request):
                raise NotFoundError("Заявка не найдена")

            return request

    async def assign_technician(
        self, current_user: User, request_id: UUID, data: AssignRequestDTO
    ) -> ServiceRequest:
        async with self._uow as uow:
            request = await self._get_request_for_update_or_404(uow, request_id)

            if request.status != RequestStatus.NEW:
                raise ConflictError(
                    "Заявку можно назначить только в статусе 'new'",
                    details={"current_status": request.status.value},
                )

            technician = await uow.user_repository.get_by_id(data.technician_id)

            if (
                technician is None
                or technician.role != UserRole.TECHNICIAN
                or not technician.is_active
            ):
                raise ConflictError("Специалист не найден или неактивен")

            request.assignee_id = technician.id

            await self._change_status(
                uow=uow,
                request=request,
                new_status=RequestStatus.ASSIGNED,
                changed_by=current_user.id,
            )

            return request

    async def start_request(self, current_user: User, request_id: UUID) -> ServiceRequest:
        async with self._uow as uow:
            request = await self._get_request_for_update_or_404(uow, request_id)

            if request.assignee_id != current_user.id:
                raise NotFoundError("Заявка не найдена")
            if request.status != RequestStatus.ASSIGNED:
                raise ConflictError(
                    "Заявка должна быть в статусе 'assigned' для начала работы",
                    details={"current_status": request.status},
                )

            await self._change_status(
                uow=uow,
                request=request,
                new_status=RequestStatus.IN_PROGRESS,
                changed_by=current_user.id,
            )

            return request

    async def complete_request(
        self, current_user: User, request_id: UUID, data: CompleteRequestDTO
    ) -> ServiceRequest:
        async with self._uow as uow:
            request = await self._get_request_for_update_or_404(uow, request_id)

            if request.assignee_id != current_user.id:
                raise NotFoundError("Заявка не найдена")
            if request.status != RequestStatus.IN_PROGRESS:
                raise ConflictError(
                    "Заявка должна быть в статусе 'in_progress' для завершения работы работы",
                    details={"current_status": request.status.value},
                )

            request.result = data.result
            request.completed_at = datetime.now(UTC)

            await self._change_status(
                uow=uow,
                request=request,
                new_status=RequestStatus.COMPLETED,
                changed_by=current_user.id,
                comment=request.result,
            )

            return request

    async def cancel_request(
        self, current_user: User, request_id: UUID, data: CancelRequestDTO
    ) -> ServiceRequest:
        async with self._uow as uow:
            request = await self._get_request_for_update_or_404(uow, request_id)

            if not (request.author_id == current_user.id or current_user.role == UserRole.MANAGER):
                raise NotFoundError("Заявка не найдена")
            if request.status not in (
                RequestStatus.NEW,
                RequestStatus.ASSIGNED,
                RequestStatus.IN_PROGRESS,
            ):
                raise ConflictError(
                    "Заявку можно отменить только в статусе 'new', 'assigned' или 'in_progress'",
                    details={"current_status": request.status.value},
                )

            request.cancellation_reason = data.reason
            request.cancelled_at = datetime.now(UTC)

            await self._change_status(
                uow=uow,
                request=request,
                new_status=RequestStatus.CANCELLED,
                changed_by=current_user.id,
                comment=data.reason,
            )

            return request

    @staticmethod
    def _has_access(current_user: User, request: ServiceRequest) -> bool:
        if current_user.role == UserRole.MANAGER:
            return True
        if current_user.role == UserRole.EMPLOYEE:
            return request.facility_id == current_user.facility_id
        if current_user.role == UserRole.TECHNICIAN:
            return request.assignee_id == current_user.id
        return False

    @staticmethod
    async def _get_request_for_update_or_404(uow: UnitOfWork, request_id: UUID) -> ServiceRequest:
        request = await uow.service_request_repository.get_by_id_for_update(request_id)
        if request is None:
            raise NotFoundError("Заявка не найдена")
        return request

    @staticmethod
    async def _change_status(
        uow: UnitOfWork,
        request: ServiceRequest,
        new_status: RequestStatus,
        changed_by: UUID,
        comment: str | None = None,
    ) -> None:
        old_status = request.status
        request.status = new_status

        history_entry = StatusHistory(
            request_id=request.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            comment=comment,
        )
        await uow.status_history_repository.add(history_entry)
        await uow.flush()
        await uow.refresh(request)
