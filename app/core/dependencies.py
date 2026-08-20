import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Header, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exception import ForbiddenError, UnauthorizedError
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.models import User
from app.models.service_request import RequestCategory, RequestPriority, RequestStatus
from app.models.user import UserRole
from app.schemas.requests import RequestFiltersSchema
from app.services.service_request_service import ServiceRequestService


async def get_session(request: Request) -> AsyncGenerator[AsyncSession]:
    session_factory = request.app.state.database_manager.get_session_factory()
    async with session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_unit_of_work(request: Request) -> UnitOfWork:
    session_factory = request.app.state.database_manager.get_session_factory()
    return UnitOfWork(session_factory=session_factory)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]


async def get_current_user(
    session: SessionDep, x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None
) -> User:
    if x_user_id is None:
        raise UnauthorizedError("Заголовок X-User-Id пустой")

    try:
        user_id = uuid.UUID(x_user_id)
    except ValueError:
        raise UnauthorizedError("X-User-Id должен быть валидным UUID") from None

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedError("Пользователь не найден")

    if not user.is_active:
        raise ForbiddenError("Пользователь неактивен")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: UserRole) -> Callable[[CurrentUser], Awaitable[User]]:

    async def _check_role(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError("Роль пользователя не разрешает эту операцию")
        return user

    return _check_role


def get_request_filters(
    status: Annotated[RequestStatus | None, Query()] = None,
    category: Annotated[RequestCategory | None, Query()] = None,
    priority: Annotated[RequestPriority | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RequestFiltersSchema:
    return RequestFiltersSchema(
        status=status,
        category=category,
        priority=priority,
        limit=limit,
        offset=offset,
    )


RequestFiltersDep = Annotated[RequestFiltersSchema, Depends(get_request_filters)]


def get_request_service(uow: UnitOfWorkDep) -> ServiceRequestService:
    return ServiceRequestService(uow)


ServiceRequestServiceDep = Annotated[ServiceRequestService, Depends(get_request_service)]
