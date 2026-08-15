import uuid
from collections.abc import AsyncGenerator
from typing import Annotated, Callable, Awaitable

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exception import ForbiddenError, UnauthorizedError
from app.models import User
from app.models.user import UserRole


async def get_session(request: Request) -> AsyncGenerator[AsyncSession]:
    async with request.app.state.database_manager.get_session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


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
