import uuid

from httpx import AsyncClient

from app.models.user import User

CREATE_REQUEST_PAYLOAD = {
    "title": "Не работает холодильник",
    "description": "Компрессор не запускается после включения",
    "category": "equipment",
    "priority": "high",
}


async def test_missing_header_returns_401(client: AsyncClient) -> None:
    """
    ТЗ: пользователь должен быть идентифицирован через заголовок X-User-Id.
    Проверяет, что запрос без заголовка возвращает 401.
    """

    response = await client.get("/requests")

    assert response.status_code == 401


async def test_invalid_uuid_header_returns_401(client: AsyncClient) -> None:
    """
    ТЗ: X-User-Id должен содержать валидный UUID.
    Проверяет, что некорректный UUID возвращает 401.
    """

    response = await client.get("/requests", headers={"X-User-Id": "not-a-uuid"})

    assert response.status_code == 401


async def test_unknown_user_returns_401(client: AsyncClient) -> None:
    """
    ТЗ: пользователь должен существовать в системе.
    Проверяет, что неизвестный пользователь получает 401.
    """

    response = await client.get("/requests", headers={"X-User-Id": str(uuid.uuid4())})

    assert response.status_code == 401


async def test_inactive_user_returns_403(client: AsyncClient, inactive_employee_user: User) -> None:
    """
    ТЗ: неактивный пользователь не может работать с системой.
    Проверяет, что неактивному пользователю возвращается 403.
    """

    response = await client.get("/requests", headers={"X-User-Id": str(inactive_employee_user.id)})

    assert response.status_code == 403


async def test_wrong_role_cannot_create_request(client: AsyncClient, manager_user: User) -> None:
    """
    ТЗ: создавать заявки может только сотрудник.
    Проверяет, что пользователь с неподходящей ролью получает 403.
    """

    response = await client.post(
        "/requests",
        json=CREATE_REQUEST_PAYLOAD,
        headers={"X-User-Id": str(manager_user.id)},
    )

    assert response.status_code == 403


async def test_wrong_role_cannot_assign_request(client: AsyncClient, employee_user: User) -> None:
    """
    ТЗ: назначать заявки может только менеджер.
    Проверяет, что пользователь с неподходящей ролью получает 403.
    """

    response = await client.post(
        f"/requests/{uuid.uuid4()}/assign",
        json={"technician_id": str(uuid.uuid4())},
        headers={"X-User-Id": str(employee_user.id)},
    )

    assert response.status_code == 403
