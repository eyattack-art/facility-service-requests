from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_user_by_name(self, user_name: str) -> User | None:
        result = await self._session.execute(select(User).where(User.name == user_name))
        return result.scalar_one_or_none()

