import uuid
from collections.abc import Awaitable, Callable

from httpx import AsyncClient

from app.models.facility import Facility
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.user import User

MakeServiceRequest = Callable[..., Awaitable[ServiceRequest]]


async def test_employee_cannot_access_other_facility_request(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    other_employee_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: сотрудник может видеть заявки только своего объекта.
    Проверяет, что заявка другого объекта недоступна по прямому ID.
    """
    request = await make_service_request(facility=facility, author=employee_user)

    response = await client.get(
        f"/requests/{request.id}",
        headers={"X-User-Id": str(other_employee_user.id)},
    )

    assert response.status_code == 404


async def test_employee_sees_only_own_facility_requests_in_list(
    client: AsyncClient,
    facility: Facility,
    other_facility: Facility,
    employee_user: User,
    other_employee_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: сотрудник видит только заявки своего объекта.
    Проверяет, что в списке отображаются только заявки его объекта.
    """

    own_request = await make_service_request(facility=facility, author=employee_user)
    await make_service_request(facility=other_facility, author=other_employee_user)

    response = await client.get("/requests", headers={"X-User-Id": str(employee_user.id)})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(own_request.id)


async def test_technician_sees_only_assigned_requests(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    technician_user: User,
    other_technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: специалист видит только назначенные ему заявки.
    Проверяет, что в списке отображаются только заявки, назначенные текущему специалисту.
    """
    assigned_to_me = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.ASSIGNED,
        assignee=technician_user,
    )
    await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.ASSIGNED,
        assignee=other_technician_user,
    )
    await make_service_request(facility=facility, author=employee_user)  # status=new, unassigned

    response = await client.get("/requests", headers={"X-User-Id": str(technician_user.id)})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(assigned_to_me.id)


async def test_manager_sees_all_requests(
    client: AsyncClient,
    facility: Facility,
    other_facility: Facility,
    employee_user: User,
    other_employee_user: User,
    manager_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: менеджер имеет доступ ко всем заявкам.
    Проверяет, что менеджер видит заявки всех объектов.
    """

    await make_service_request(facility=facility, author=employee_user)
    await make_service_request(facility=other_facility, author=other_employee_user)

    response = await client.get("/requests", headers={"X-User-Id": str(manager_user.id)})

    assert response.status_code == 200
    assert response.json()["total"] == 2


async def test_other_facility_request_masked_as_404_on_cancel(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    other_employee_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: сотрудник может отменять только заявки своего объекта.
    Проверяет, что заявка другого объекта недоступна для отмены и возвращается 404.
    """

    request = await make_service_request(facility=facility, author=employee_user)

    response = await client.post(
        f"/requests/{request.id}/cancel",
        json={"reason": "Причина отмены заявки другим сотрудником"},
        headers={"X-User-Id": str(other_employee_user.id)},
    )

    assert response.status_code == 404


async def test_technician_cannot_start_unassigned_request(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: специалист может начать только назначенную ему заявку.
    Проверяет, что неназначенная заявка недоступна специалисту для начала работы.
    """

    request = await make_service_request(facility=facility, author=employee_user)

    response = await client.post(
        f"/requests/{request.id}/start",
        headers={"X-User-Id": str(technician_user.id)},
    )

    assert response.status_code == 404

async def test_technician_cannot_start_request_assigned_to_another_technician(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    technician_user: User,
    other_technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: специалист может начать только назначенную ему заявку.
    Проверяет, что специалист не может начать заявку, назначенную другому специалисту.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.ASSIGNED,
        assignee=other_technician_user,
    )

    response = await client.post(
        f"/requests/{request.id}/start",
        headers={"X-User-Id": str(technician_user.id)},
    )

    assert response.status_code == 404

async def test_technician_cannot_complete_request_assigned_to_another_technician(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    technician_user: User,
    other_technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: специалист может завершить только назначенную ему заявку.
    Проверяет, что специалист не может завершить заявку, назначенную другому специалисту.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.IN_PROGRESS,
        assignee=other_technician_user,
    )

    response = await client.post(
        f"/requests/{request.id}/complete",
        json={"result": "Работа выполнена, неисправность устранена"},
        headers={"X-User-Id": str(technician_user.id)},
    )

    assert response.status_code == 404

async def test_employee_cannot_cancel_other_employee_request_same_facility(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    other_employee_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: сотрудник может отменить только свою заявку.
    Проверяет, что сотрудник не может отменить заявку другого сотрудника своего объекта.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
    )

    response = await client.post(
        f"/requests/{request.id}/cancel",
        json={"reason": "Попытка отмены чужой заявки"},
        headers={"X-User-Id": str(other_employee_user.id)},
    )

    assert response.status_code == 404

async def test_assign_rejects_unknown_technician(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    manager_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: заявку можно назначить только существующему специалисту.
    Проверяет, что назначение несуществующего пользователя отклоняется.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
    )

    response = await client.post(
        f"/requests/{request.id}/assign",
        json={"technician_id": str(uuid.uuid4())},
        headers={"X-User-Id": str(manager_user.id)},
    )

    assert response.status_code in (404, 409)

async def test_start_rejects_new_request(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: начать работу можно только по назначенной заявке.
    Проверяет, что заявку в статусе new нельзя перевести сразу в in_progress.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.NEW,
    )

    response = await client.post(
        f"/requests/{request.id}/start",
        headers={"X-User-Id": str(technician_user.id)},
    )

    assert response.status_code == 404

async def test_complete_rejects_new_request(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    technician_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: завершить можно только заявку, находящуюся в работе.
    Проверяет, что заявку в статусе new нельзя сразу завершить.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
        status=RequestStatus.NEW,
    )

    response = await client.post(
        f"/requests/{request.id}/complete",
        json={"result": "Работа выполнена, неисправность устранена"},
        headers={"X-User-Id": str(technician_user.id)},
    )

    assert response.status_code == 404

async def test_cancel_adds_status_history(
    client: AsyncClient,
    facility: Facility,
    employee_user: User,
    make_service_request: MakeServiceRequest,
) -> None:
    """
    ТЗ: изменение статуса заявки должно фиксироваться в истории.
    Проверяет, что при отмене создаётся переход new → cancelled с причиной отмены.
    """

    request = await make_service_request(
        facility=facility,
        author=employee_user,
    )

    response = await client.post(
        f"/requests/{request.id}/cancel",
        json={"reason": "Неисправность устранена своими силами"},
        headers={"X-User-Id": str(employee_user.id)},
    )

    assert response.status_code == 200

    detail_response = await client.get(
        f"/requests/{request.id}",
        headers={"X-User-Id": str(employee_user.id)},
    )

    assert detail_response.status_code == 200

    history = detail_response.json()["history"]

    assert len(history) == 2
    assert history[-1]["old_status"] == "new"
    assert history[-1]["new_status"] == "cancelled"
    assert history[-1]["comment"] == "Неисправность устранена своими силами"