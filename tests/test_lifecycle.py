from collections.abc import Awaitable, Callable

from httpx import AsyncClient

from app.models.facility import Facility
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.user import User

MakeServiceRequest = Callable[..., Awaitable[ServiceRequest]]


async def test_full_request_lifecycle_new_to_completed(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    manager_user: User,
    technician_user: User,
) -> None:
    """
    ТЗ: заявка проходит жизненный цикл new → assigned → in_progress → completed.
    Проверяет корректность переходов статусов и ведение истории заявки.
    """

    create_response = await client.post(
        "/requests",
        json={
            "title": "Течёт кран на кухне",
            "description": "Из под крана на кухне капает вода постоянно",
            "category": "plumbing",
            "priority": "normal",
        },
        headers={"X-User-Id": str(employee_user.id)},
    )
    assert create_response.status_code == 201
    request_id = create_response.json()["id"]

    assign_response = await client.post(
        f"/requests/{request_id}/assign",
        json={"technician_id": str(technician_user.id)},
        headers={"X-User-Id": str(manager_user.id)},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["status"] == "assigned"

    start_response = await client.post(
        f"/requests/{request_id}/start",
        headers={"X-User-Id": str(technician_user.id)},
    )
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "in_progress"

    complete_response = await client.post(
        f"/requests/{request_id}/complete",
        json={"result": "Заменена прокладка, течь устранена"},
        headers={"X-User-Id": str(technician_user.id)},
    )
    assert complete_response.status_code == 200
    complete_data = complete_response.json()
    assert complete_data["status"] == "completed"
    assert complete_data["result"] == "Заменена прокладка, течь устранена"
    assert complete_data["completed_at"] is not None

    detail_response = await client.get(
        f"/requests/{request_id}", headers={"X-User-Id": str(manager_user.id)}
    )
    assert detail_response.status_code == 200
    history = detail_response.json()["history"]
    transitions = [(item["old_status"], item["new_status"]) for item in history]
    assert transitions == [
        (None, "new"),
        ("new", "assigned"),
        ("assigned", "in_progress"),
        ("in_progress", "completed"),
    ]
    assert history[-1]["comment"] == "Заменена прокладка, течь устранена"


async def test_assign_rejects_wrong_role(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    manager_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: назначать заявку можно только специалисту.
    Проверяет, что нельзя назначить заявку пользователю с неподходящей ролью.
    """

    request = await make_service_request(facility=facility, author=employee_user)

    response = await client.post(
        f"/requests/{request.id}/assign",
        json={"technician_id": str(employee_user.id)},
        headers={"X-User-Id": str(manager_user.id)},
    )

    assert response.status_code == 409


async def test_assign_rejects_inactive_technician(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    manager_user: User,
    inactive_technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: назначать заявку можно только активному специалисту.
    Проверяет, что назначение неактивному специалисту отклоняется.
    """

    request = await make_service_request(facility=facility, author=employee_user)

    response = await client.post(
        f"/requests/{request.id}/assign",
        json={"technician_id": str(inactive_technician_user.id)},
        headers={"X-User-Id": str(manager_user.id)},
    )

    assert response.status_code == 409


async def test_assign_already_assigned_request_conflicts(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    manager_user: User,
    technician_user: User,
    other_technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: назначить можно только заявку в статусе new.
    Проверяет, что повторное назначение уже назначенной заявки отклоняется.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.ASSIGNED,
        assignee=technician_user,
    )

    response = await client.post(
        f"/requests/{request.id}/assign",
        json={"technician_id": str(other_technician_user.id)},
        headers={"X-User-Id": str(manager_user.id)},
    )

    assert response.status_code == 409


async def test_start_requires_assigned_status(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: начать работу можно только по назначенной заявке.
    Проверяет, что переход в in_progress из другого статуса отклоняется.
    """
    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.IN_PROGRESS,
        assignee=technician_user,
    )

    response = await client.post(
        f"/requests/{request.id}/start",
        headers={"X-User-Id": str(technician_user.id)},
    )

    assert response.status_code == 409


async def test_complete_requires_in_progress_status(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: завершить можно только заявку в работе.
    Проверяет, что переход в completed из статуса assigned отклоняется.
    """
    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.ASSIGNED,
        assignee=technician_user,
    )

    response = await client.post(
        f"/requests/{request.id}/complete",
        json={"result": "Результат работы специалиста"},
        headers={"X-User-Id": str(technician_user.id)},
    )

    assert response.status_code == 409


async def test_complete_rejects_short_result(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: при завершении заявки необходимо указать результат работы.
    Проверяет, что слишком короткий результат отклоняется.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.IN_PROGRESS,
        assignee=technician_user,
    )

    response = await client.post(
        f"/requests/{request.id}/complete",
        json={"result": "ок"},
        headers={"X-User-Id": str(technician_user.id)},
    )

    assert response.status_code == 422


async def test_cancel_rejects_short_reason(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: при отмене заявки необходимо указать причину.
    Проверяет, что слишком короткая причина отмены отклоняется.
    """

    request = await make_service_request(facility=facility, author=employee_user)

    response = await client.post(
        f"/requests/{request.id}/cancel",
        json={"reason": "ок"},
        headers={"X-User-Id": str(employee_user.id)},
    )

    assert response.status_code == 422


async def test_employee_can_cancel_own_new_request(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: сотрудник может отменить свою заявку.
    Проверяет, что сотрудник может отменить собственную заявку в статусе new.
    """

    request = await make_service_request(facility=facility, author=employee_user)

    response = await client.post(
        f"/requests/{request.id}/cancel",
        json={"reason": "Неисправность устранена своими силами"},
        headers={"X-User-Id": str(employee_user.id)},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


async def test_manager_can_cancel_any_active_request(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    manager_user: User,
    technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: менеджер может отменить активную заявку.
    Проверяет, что менеджер может отменить заявку другого сотрудника.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.IN_PROGRESS,
        assignee=technician_user,
    )

    response = await client.post(
        f"/requests/{request.id}/cancel",
        json={"reason": "Отменено менеджером по производственной необходимости"},
        headers={"X-User-Id": str(manager_user.id)},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


async def test_actions_on_completed_request_are_rejected(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    manager_user: User,
    technician_user: User,
    other_technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: завершённая заявка не может быть изменена.
    Проверяет, что назначение, начало работы, повторное завершение и отмена отклоняются.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.COMPLETED,
        assignee=technician_user,
    )

    assign_response = await client.post(
        f"/requests/{request.id}/assign",
        json={"technician_id": str(other_technician_user.id)},
        headers={"X-User-Id": str(manager_user.id)},
    )
    assert assign_response.status_code == 409

    start_response = await client.post(
        f"/requests/{request.id}/start",
        headers={"X-User-Id": str(technician_user.id)},
    )
    assert start_response.status_code == 409

    complete_response = await client.post(
        f"/requests/{request.id}/complete",
        json={"result": "Повторная попытка завершения"},
        headers={"X-User-Id": str(technician_user.id)},
    )
    assert complete_response.status_code == 409

    cancel_response = await client.post(
        f"/requests/{request.id}/cancel",
        json={"reason": "Попытка отменить завершённую заявку"},
        headers={"X-User-Id": str(manager_user.id)},
    )
    assert cancel_response.status_code == 409


async def test_actions_on_cancelled_request_are_rejected(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    manager_user: User,
    technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: отменённая заявка не может быть изменена.
    Проверяет, что назначение и повторная отмена заявки отклоняются.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.CANCELLED,
    )

    assign_response = await client.post(
        f"/requests/{request.id}/assign",
        json={"technician_id": str(technician_user.id)},
        headers={"X-User-Id": str(manager_user.id)},
    )
    assert assign_response.status_code == 409

    cancel_response = await client.post(
        f"/requests/{request.id}/cancel",
        json={"reason": "Повторная попытка отмены уже отменённой заявки"},
        headers={"X-User-Id": str(manager_user.id)},
    )
    assert cancel_response.status_code == 409
