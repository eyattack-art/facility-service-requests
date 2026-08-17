from uuid import UUID

from app.core.exception import ConflictError, NotFoundError
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.models import ServiceRequest, StatusHistory, User
from app.models.service_request import RequestStatus
from app.models.user import UserRole
from app.services.dto import AssignRequestDTO, CreateRequestDTO


class ServiceRequestService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_request(self, current_user: User, data: CreateRequestDTO) -> ServiceRequest:
        async with self.uow as uow:
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

    async def assign_technician(
        self, current_user: User, request_id: UUID, data: AssignRequestDTO
    ) -> ServiceRequest:
        async with self.uow as uow:
            request = await uow.service_request_repository.get_by_id_for_update(request_id)
            if request is None:
                raise NotFoundError("Заявка не найдена")

            if request.status != RequestStatus.NEW:
                raise ConflictError(
                    "Заявку можно назначить только в статусе 'new'",
                    details={"current_status": request.status},
                )

            technician = await uow.user_repository.get_by_id(data.technician_id)
            if (
                technician is None
                or technician.role != UserRole.TECHNICIAN
                or not technician.is_active
            ):
                raise ConflictError("Специалист не найден или неактивен")

            old_status = request.status
            request.assignee_id = technician.id
            request.status = RequestStatus.ASSIGNED

            history_entry = StatusHistory(
                request_id=request.id,
                old_status=old_status,
                new_status=RequestStatus.ASSIGNED,
                changed_by=current_user.id,
                comment=None,
            )
            await uow.status_history_repository.add(history_entry)
            await uow.flush()
            await uow.refresh(request)

            return request
