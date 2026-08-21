import os
import subprocess
from collections.abc import AsyncGenerator, Awaitable, Callable
from types import TracebackType

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    AsyncSessionTransaction,
    async_sessionmaker,
    create_async_engine,
)

from app.core.dependencies import get_session, get_unit_of_work
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.main import app
from app.models.facility import Facility
from app.models.service_request import (
    RequestCategory,
    RequestPriority,
    RequestStatus,
    ServiceRequest,
)
from app.models.status_history import StatusHistory
from app.models.user import User, UserRole
from app.repositories.facility_repository import FacilityRepository
from app.repositories.service_request_repository import ServiceRequestRepository
from app.repositories.status_history_repository import StatusHistoryRepository
from app.repositories.user_repository import UserRepository

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    env = os.environ.copy()
    env["APP_CONFIG__DATABASE__URL"] = TEST_DATABASE_URL
    result = subprocess.run(
        ["poetry", "run", "alembic", "upgrade", "head"],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Migration failed:\n{result.stdout}\n{result.stderr}")


@pytest.fixture(scope="session")
def test_engine() -> AsyncEngine:
    return create_async_engine(TEST_DATABASE_URL)


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
        session = session_factory()

        yield session

        await session.close()
        await transaction.rollback()


class TestUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._nested: AsyncSessionTransaction | None = None

    async def __aenter__(self) -> "TestUnitOfWork":
        self._nested = await self._session.begin_nested()
        self.user_repository = UserRepository(self._session)
        self.facility_repository = FacilityRepository(self._session)
        self.service_request_repository = ServiceRequestRepository(self._session)
        self.status_history_repository = StatusHistoryRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._nested is not None
        if exc_type is not None:
            await self._nested.rollback()
        else:
            await self._session.flush()
            await self._nested.commit()


@pytest_asyncio.fixture(scope="session")
async def app_with_lifespan() -> AsyncGenerator[FastAPI]:
    async with LifespanManager(app):
        yield app


@pytest_asyncio.fixture
async def client(
    app_with_lifespan: FastAPI, db_session: AsyncSession
) -> AsyncGenerator[AsyncClient]:
    async def _override_get_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    def _override_get_unit_of_work() -> UnitOfWork:
        return TestUnitOfWork(db_session)

    app_with_lifespan.dependency_overrides[get_session] = _override_get_session
    app_with_lifespan.dependency_overrides[get_unit_of_work] = _override_get_unit_of_work

    transport = ASGITransport(app=app_with_lifespan, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app_with_lifespan.dependency_overrides.clear()


@pytest_asyncio.fixture
async def facility(db_session: AsyncSession) -> Facility:
    obj = Facility(name="Тестовый объект", address="Тестовый адрес")
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest_asyncio.fixture
async def employee_user(db_session: AsyncSession, facility: Facility) -> User:
    user = User(name="Тестовый сотрудник", role=UserRole.EMPLOYEE, facility_id=facility.id)
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def manager_user(db_session: AsyncSession) -> User:
    user = User(name="Тестовый менеджер", role=UserRole.MANAGER, facility_id=None)
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def technician_user(db_session: AsyncSession) -> User:
    user = User(name="Тестовый специалист", role=UserRole.TECHNICIAN, facility_id=None)
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def inactive_employee_user(db_session: AsyncSession, facility: Facility) -> User:
    user = User(
        name="Неактивный сотрудник",
        role=UserRole.EMPLOYEE,
        facility_id=facility.id,
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def other_technician_user(db_session: AsyncSession) -> User:
    user = User(name="Второй специалист", role=UserRole.TECHNICIAN, facility_id=None)
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def inactive_technician_user(db_session: AsyncSession) -> User:
    user = User(
        name="Неактивный специалист",
        role=UserRole.TECHNICIAN,
        facility_id=None,
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def other_facility(db_session: AsyncSession) -> Facility:
    obj = Facility(name="Второй тестовый объект", address="Второй тестовый адрес")
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest_asyncio.fixture
async def inactive_facility(db_session: AsyncSession) -> Facility:
    obj = Facility(
        name="Неактивный объект",
        address="Адрес неактивного объекта",
        is_active=False,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest_asyncio.fixture
async def other_employee_user(db_session: AsyncSession, other_facility: Facility) -> User:
    user = User(
        name="Сотрудник второго объекта",
        role=UserRole.EMPLOYEE,
        facility_id=other_facility.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def make_service_request(
    db_session: AsyncSession,
) -> Callable[..., Awaitable[ServiceRequest]]:
    """Фабрика для создания заявки напрямую в БД, минуя сервисный слой.

    Полезна там, где важна только видимость/доступ, а не сама бизнес-логика
    переходов статусов.
    """

    async def _make(
        *,
        facility: Facility,
        author: User,
        status: RequestStatus = RequestStatus.NEW,
        assignee: User | None = None,
        title: str = "Тестовая заявка на обслуживание",
        description: str = "Тестовое описание неисправности для проверки доступа",
        category: RequestCategory = RequestCategory.EQUIPMENT,
        priority: RequestPriority = RequestPriority.NORMAL,
    ) -> ServiceRequest:
        request = ServiceRequest(
            facility_id=facility.id,
            author_id=author.id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            status=status,
            assignee_id=assignee.id if assignee else None,
        )
        db_session.add(request)
        await db_session.flush()

        db_session.add(
            StatusHistory(
                request_id=request.id,
                old_status=None,
                new_status=status,
                changed_by=author.id,
                comment=None,
            )
        )
        await db_session.flush()
        await db_session.refresh(request)

        return request

    return _make
