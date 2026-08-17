from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi.params import Depends

from app.core.dependencies import ServiceRequestServiceDep, require_role
from app.models import User
from app.models.user import UserRole
from app.schemas.requests import AssignRequestSchema, CreateRequestSchema, RequestCardSchema
from app.services.dto import AssignRequestDTO, CreateRequestDTO

router = APIRouter(prefix="/requests", tags=["Requests"])


@router.post("", response_model=RequestCardSchema, status_code=201)
async def create_request(
    payload: CreateRequestSchema,
    current_user: Annotated[User, Depends(require_role(UserRole.EMPLOYEE))],
    service: ServiceRequestServiceDep,
):
    dto = CreateRequestDTO(**payload.model_dump())
    return await service.create_request(current_user, dto)


@router.post("/{request_id}/assign", response_model=RequestCardSchema)
async def assign_request(
    request_id: UUID,
    payload: AssignRequestSchema,
    current_user: Annotated[User, Depends(require_role(UserRole.MANAGER))],
    service: ServiceRequestServiceDep,
):
    dto = AssignRequestDTO(**payload.model_dump())
    return await service.assign_technician(current_user, request_id, dto)
