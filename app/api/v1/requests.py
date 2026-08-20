from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import (
    CurrentUser,
    RequestFiltersDep,
    ServiceRequestServiceDep,
    require_role,
)
from app.models import User
from app.models.user import UserRole
from app.schemas.requests import (
    AssignRequestSchema,
    CancelRequestSchema,
    CompleteRequestSchema,
    CreateRequestSchema,
    RequestDetailSchema,
    RequestDetailWithHistorySchema,
    RequestListResponseSchema,
    RequestSummarySchema,
)
from app.services.dto import (
    AssignRequestDTO,
    CancelRequestDTO,
    CompleteRequestDTO,
    CreateRequestDTO,
    ListRequestsFilterDTO,
)

router = APIRouter(prefix="/requests", tags=["Requests"])


@router.post("", status_code=201)
async def create_request(
    payload: CreateRequestSchema,
    current_user: Annotated[User, Depends(require_role(UserRole.EMPLOYEE))],
    service: ServiceRequestServiceDep,
) -> RequestDetailSchema:
    dto = CreateRequestDTO(**payload.model_dump())
    request = await service.create_request(current_user, dto)
    return RequestDetailSchema.model_validate(request)


@router.get("")
async def list_requests(
    current_user: CurrentUser,
    filters: RequestFiltersDep,
    service: ServiceRequestServiceDep,
) -> RequestListResponseSchema:
    dto = ListRequestsFilterDTO(
        status=filters.status,
        category=filters.category,
        priority=filters.priority,
        limit=filters.limit,
        offset=filters.offset,
    )
    result = await service.list_requests(current_user, dto)
    return RequestListResponseSchema(
        items=[RequestSummarySchema.model_validate(item) for item in result.items],
        limit=result.limit,
        offset=result.offset,
        total=result.total,
    )


@router.get("/{request_id}")
async def get_request(
    request_id: UUID,
    current_user: CurrentUser,
    service: ServiceRequestServiceDep,
) -> RequestDetailWithHistorySchema:
    request = await service.get_request_by_id(current_user, request_id)
    return RequestDetailWithHistorySchema.model_validate(request)


@router.post("/{request_id}/assign")
async def assign_request(
    request_id: UUID,
    payload: AssignRequestSchema,
    current_user: Annotated[User, Depends(require_role(UserRole.MANAGER))],
    service: ServiceRequestServiceDep,
) -> RequestDetailSchema:
    dto = AssignRequestDTO(**payload.model_dump())
    request = await service.assign_technician(current_user, request_id, dto)
    return RequestDetailSchema.model_validate(request)


@router.post("/{request_id}/start")
async def start_request(
    request_id: UUID,
    current_user: Annotated[User, Depends(require_role(UserRole.TECHNICIAN))],
    service: ServiceRequestServiceDep,
) -> RequestDetailSchema:
    request = await service.start_request(current_user, request_id)
    return RequestDetailSchema.model_validate(request)


@router.post("/{request_id}/complete")
async def complete_request(
    request_id: UUID,
    payload: CompleteRequestSchema,
    current_user: Annotated[User, Depends(require_role(UserRole.TECHNICIAN))],
    service: ServiceRequestServiceDep,
) -> RequestDetailSchema:
    dto = CompleteRequestDTO(**payload.model_dump())
    request = await service.complete_request(current_user, request_id, dto)
    return RequestDetailSchema.model_validate(request)


@router.post("/{request_id}/cancel")
async def cancel_request(
    request_id: UUID,
    payload: CancelRequestSchema,
    current_user: Annotated[User, Depends(require_role(UserRole.MANAGER, UserRole.EMPLOYEE))],
    service: ServiceRequestServiceDep,
) -> RequestDetailSchema:
    dto = CancelRequestDTO(**payload.model_dump())
    request = await service.cancel_request(current_user, request_id, dto)
    return RequestDetailSchema.model_validate(request)
