import asyncio
from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine

from app.models.facility import Facility
from app.models.service_request import ServiceRequest, RequestStatus, RequestCategory, RequestPriority
from app.models.status_history import StatusHistory
from app.models.user import User, UserRole
from app.repositories.status_history_repository import StatusHistoryRepository

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
