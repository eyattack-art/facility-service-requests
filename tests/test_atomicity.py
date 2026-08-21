import asyncio
import uuid
from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.exception import ConflictError
from app.infrastructure.database.unit_of_work import UnitOfWork
from app.models.facility import Facility
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.status_history import StatusHistory
from app.models.user import User, UserRole
from app.repositories.status_history_repository import StatusHistoryRepository
from app.services.dto import AssignRequestDTO
from app.services.service_request_service import ServiceRequestService

MakeServiceRequest = Callable[..., Awaitable[ServiceRequest]]


async def test_assign_rolls_back_request_if_status_history_repository_fails(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    manager_user: User,
    technician_user: User,
    make_service_request: MakeServiceRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    ТЗ: изменение заявки и запись истории должны выполняться атомарно.
    Проверяет, что при ошибке записи истории изменения заявки откатываются.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
    )
    request_id = request.id

    async def _boom(
        self: StatusHistoryRepository,
        entry: StatusHistory,
    ) -> StatusHistory:
        raise RuntimeError("Симулированный сбой репозитория истории")

    monkeypatch.setattr(StatusHistoryRepository, "add", _boom)

    response = await client.post(
        f"/requests/{request_id}/assign",
        json={"technician_id": str(technician_user.id)},
        headers={"X-User-Id": str(manager_user.id)},
    )

    assert response.status_code == 500

    detail_response = await client.get(
        f"/requests/{request_id}",
        headers={"X-User-Id": str(manager_user.id)},
    )

    assert detail_response.status_code == 200
    data = detail_response.json()

    assert data["status"] == "new"
    assert data["assignee_id"] is None

    assert len(data["history"]) == 1
    assert data["history"][0]["old_status"] is None
    assert data["history"][0]["new_status"] == "new"


async def test_status_history_repository_works_with_postgresql_transaction(
    db_session: AsyncSession,
    facility: Facility,
    employee_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: история изменения статусов должна сохраняться в базе данных.
    Проверяет корректную запись истории в рамках PostgreSQL-транзакции.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
    )

    repository = StatusHistoryRepository(db_session)

    entry = StatusHistory(
        request_id=request.id,
        old_status=RequestStatus.NEW,
        new_status=RequestStatus.ASSIGNED,
        changed_by=employee_user.id,
        comment="Заявка назначена специалисту",
    )

    await repository.add(entry)

    await db_session.commit()

    result = await db_session.execute(
        select(StatusHistory).where(
            StatusHistory.request_id == request.id,
            StatusHistory.new_status == RequestStatus.ASSIGNED,
        )
    )

    history_entry = result.scalar_one()

    assert history_entry.request_id == request.id
    assert history_entry.old_status == RequestStatus.NEW
    assert history_entry.new_status == RequestStatus.ASSIGNED
    assert history_entry.changed_by == employee_user.id
    assert history_entry.comment == "Заявка назначена специалисту"


async def test_concurrent_assign_only_one_wins(
    test_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    ТЗ, раздел 11: "Вторая команда после получения блокировки обязана повторно
    проверить актуальный статус и при конфликте вернуть HTTP 409".

    Два менеджера одновременно пытаются назначить заявку в статусе `new` на
    двух РАЗНЫХ специалистов. Ожидаем:
      - ровно одна команда успевает (заявка переходит в assigned);
      - вторая получает ConflictError, а не тихо перезаписывает исполнителя;
      - в истории статусов остаётся ровно одна новая запись о переходе
        new -> assigned (а не две, и не ноль).
    """
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    unique = uuid.uuid4().hex[:8]
    async with session_factory() as setup_session:
        facility = Facility(name=f"Конкурентный тест объект {unique}", address="Тестовый адрес")
        setup_session.add(facility)
        await setup_session.flush()

        employee = User(name="Сотрудник", role=UserRole.EMPLOYEE, facility_id=facility.id)
        manager = User(name="Менеджер", role=UserRole.MANAGER, facility_id=None)
        technician_a = User(name="Специалист A", role=UserRole.TECHNICIAN, facility_id=None)
        technician_b = User(name="Специалист B", role=UserRole.TECHNICIAN, facility_id=None)
        setup_session.add_all([employee, manager, technician_a, technician_b])
        await setup_session.flush()

        service_request = ServiceRequest(
            facility_id=facility.id,
            author_id=employee.id,
            title="Заявка для конкурентного теста",
            description="Проверка блокировки строки при одновременном назначении",
            category="equipment",
            priority="normal",
            status=RequestStatus.NEW,
        )
        setup_session.add(service_request)
        await setup_session.flush()

        setup_session.add(
            StatusHistory(
                request_id=service_request.id,
                old_status=None,
                new_status=RequestStatus.NEW,
                changed_by=employee.id,
                comment=None,
            )
        )
        await setup_session.commit()

        request_id = service_request.id
        manager_id = manager.id
        technician_a_id = technician_a.id
        technician_b_id = technician_b.id
        facility_id = facility.id
        employee_id = employee.id

    try:
        original_add = StatusHistoryRepository.add

        async def _slow_add(self: StatusHistoryRepository, entry: StatusHistory) -> StatusHistory:
            await asyncio.sleep(0.4)
            return await original_add(self, entry)

        monkeypatch.setattr(StatusHistoryRepository, "add", _slow_add)

        async def _assign(technician_id: uuid.UUID) -> ServiceRequest:
            lookup_uow = UnitOfWork(session_factory=session_factory)
            async with lookup_uow as active_lookup_uow:
                manager_user = await active_lookup_uow.user_repository.get_by_id(manager_id)
            assert manager_user is not None

            uow = UnitOfWork(session_factory=session_factory)
            service = ServiceRequestService(uow)
            return await service.assign_technician(
                manager_user, request_id, AssignRequestDTO(technician_id=technician_id)
            )

        results = await asyncio.gather(
            _assign(technician_a_id), _assign(technician_b_id), return_exceptions=True
        )

        successes = [r for r in results if isinstance(r, ServiceRequest)]
        conflicts = [r for r in results if isinstance(r, ConflictError)]
        other_errors = [r for r in results if not isinstance(r, ServiceRequest | ConflictError)]

        assert other_errors == [], f"Неожиданные ошибки: {other_errors}"
        assert len(successes) == 1, "Ровно одна из двух команд должна успешно назначить заявку"
        assert len(conflicts) == 1, (
            "Вторая команда должна получить конфликт (409), а не тихо победить"
        )

        winner_technician_id = successes[0].assignee_id
        assert winner_technician_id in {technician_a_id, technician_b_id}

        async with session_factory() as verify_session:
            final_request = (
                await verify_session.execute(
                    select(ServiceRequest).where(ServiceRequest.id == request_id)
                )
            ).scalar_one()

            assert final_request.status == RequestStatus.ASSIGNED
            assert final_request.assignee_id == winner_technician_id

            history = (
                (
                    await verify_session.execute(
                        select(StatusHistory)
                        .where(StatusHistory.request_id == request_id)
                        .order_by(StatusHistory.created_at)
                    )
                )
                .scalars()
                .all()
            )

            assert len(history) == 2
            assert history[0].new_status == RequestStatus.NEW
            assert history[1].old_status == RequestStatus.NEW
            assert history[1].new_status == RequestStatus.ASSIGNED
    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(
                delete(StatusHistory).where(StatusHistory.request_id == request_id)
            )
            await cleanup_session.execute(
                delete(ServiceRequest).where(ServiceRequest.id == request_id)
            )
            await cleanup_session.execute(
                delete(User).where(
                    User.id.in_([employee_id, manager_id, technician_a_id, technician_b_id])
                )
            )
            await cleanup_session.execute(delete(Facility).where(Facility.id == facility_id))
            await cleanup_session.commit()
