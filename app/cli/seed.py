import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.database.database_manager import DatabaseManager
from app.models import Facility
from app.models.user import User, UserRole

# 0e0e3212-29d8-4117-8c94-31717d44c0ed

SEED_NAMESPACE = uuid.UUID("0e0e3212-29d8-4117-8c94-31717d44c0ed")


def make_uuid(name: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, name)


@dataclass(frozen=True)
class FacilitySeed:
    key: str
    name: str
    address: str


@dataclass(frozen=True)
class UserSeed:
    key: str
    name: str
    role: str
    facility_key: str | None


FACILITIES: list[FacilitySeed] = [
    FacilitySeed(key="facility-1", name="Магазин №1, Тверская", address="Тверская ул., 1"),
    FacilitySeed(key="facility-2", name="Магазин №2, Ленинский", address="Ленинский пр-т, 2"),
]


def build_users() -> list[UserSeed]:
    users: list[UserSeed] = []

    for facility in FACILITIES:
        users.append(
            UserSeed(
                key=f"{facility.key}:employee:1",
                name=f"Сотрудник объекта {facility.name}",
                role=UserRole.EMPLOYEE.value,
                facility_key=facility.key,
            )
        )

    for i in (1, 2):
        users.append(
            UserSeed(
                key=f"technician:{i}",
                name=f"Специалист {i}",
                role=UserRole.TECHNICIAN.value,
                facility_key=None,
            )
        )

    users.append(
        UserSeed(
            key="manager:1",
            name="Менеджер",
            role=UserRole.MANAGER.value,
            facility_key=None,
        )
    )

    return users


async def seed(session: AsyncSession) -> None:
    facility_ids: dict[str, uuid.UUID] = {}

    for facility in FACILITIES:
        facility_id = make_uuid(f"{facility.key}")
        facility_ids[facility.key] = facility_id

        stmt = (
            pg_insert(Facility)
            .values(
                id=facility_id,
                name=facility.name,
                address=facility.address,
                is_active=True,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await session.execute(stmt)
        print(f"Facility '{facility.name}': {facility_id}")

    for user in build_users():
        user_id = make_uuid(f"user:{user.key}")
        user_facility_id = facility_ids[user.facility_key] if user.facility_key else None

        stmt = (
            pg_insert(User)
            .values(
                id=user_id,
                name=user.name,
                role=user.role,
                facility_id=user_facility_id,
                is_active=True,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await session.execute(stmt)
        print(f"User '{user.name}' ({user.role}): {user_id}")

    await session.commit()


async def main() -> None:
    database_manager = DatabaseManager(
        url=settings.database.url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_pre_ping=settings.database.pool_pre_ping,
        pool_recycle=settings.database.pool_recycle,
        pool_timeout=settings.database.pool_timeout,
    )
    session_factory = database_manager.get_session_factory()
    async with session_factory() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
