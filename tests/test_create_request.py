from httpx import AsyncClient

from app.models.facility import Facility
from app.models.user import User


async def test_create_request_success(
    client: AsyncClient,
    employee_user: User,
    facility: Facility,
) -> None:
    """
    ТЗ: сотрудник может создавать заявку для своего объекта.
    Проверяет успешное создание заявки и добавление начальной записи в историю статусов.
    """

    payload = {
        "title": "Не работает холодильник",
        "description": "Компрессор не запускается после включения",
        "category": "equipment",
        "priority": "high",
    }

    response = await client.post(
        "/requests",
        json=payload,
        headers={"X-User-Id": str(employee_user.id)},
    )

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "new"
    assert data["facility_id"] == str(facility.id)
    assert data["author_id"] == str(employee_user.id)

    # Проверяем, что при создании заявки появилась
    # первая запись в истории изменения статуса.
    request_id = data["id"]

    detail_response = await client.get(
        f"/requests/{request_id}",
        headers={"X-User-Id": str(employee_user.id)},
    )

    assert detail_response.status_code == 200

    detail_data = detail_response.json()
    history = detail_data["history"]

    assert len(history) == 1
    assert history[0]["old_status"] is None
    assert history[0]["new_status"] == "new"


async def test_create_request_rejected_for_inactive_facility(
    client: AsyncClient,
    employee_user: User,
    facility: Facility,
) -> None:
    """
    ТЗ: заявки нельзя создавать для неактивного объекта.
    Проверяет, что при неактивном объекте создание заявки возвращает 409.
    """

    facility.is_active = False

    payload = {
        "title": "Не работает холодильник",
        "description": "Компрессор не запускается после включения",
        "category": "equipment",
        "priority": "high",
    }

    response = await client.post(
        "/requests",
        json=payload,
        headers={"X-User-Id": str(employee_user.id)},
    )

    assert response.status_code == 409
