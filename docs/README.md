# Запуск проекта

## 1. Настроить переменные окружения

```bash
cp .env.example .env
```

## 2. Поднять контейнеры

```bash
docker compose up --build
```

Миграции применяются автоматически.

## 3. Заполнить базу тестовыми данными

```bash
docker compose exec api poetry run python -m app.cli.seed
```

Выведет UUID созданных пользователей – используются в заголовке `X-User-Id`.

## 4. Открыть документацию API

Swagger: http://localhost:8080/docs

## Остановка

```bash
docker compose down          # остановить
docker compose down -v       # остановить и удалить данные
```

## Тесты

```bash
docker compose exec api poetry run pytest
```

## Проверки кода

```bash
docker compose exec api poetry run ruff format --check .
docker compose exec api poetry run ruff check .
docker compose exec api poetry run mypy app
```

## Примеры API-запросов

Базовый URL: `http://localhost:8080`. Каждый защищённый запрос требует заголовок
`X-User-Id: <UUID пользователя>` – подставьте свои значения из вывода `seed`.

### Health check (без заголовка)

```bash
curl -s http://localhost:8080/health
```

```json
{"status": "ok"}
```

### Создание заявки (employee)

```bash
curl -s -X POST http://localhost:8080/requests \
  -H "Content-Type: application/json" \
  -H "X-User-Id: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" \
  -d '{
    "title": "Не работает холодильник",
    "description": "Компрессор не запускается после включения",
    "category": "equipment",
    "priority": "high"
  }'
```

Успех – `201 Created`:

```json
{
  "id": "9f1c2e3a-4b5d-4e6f-8a9b-0c1d2e3f4a5b",
  "facility_id": "11111111-1111-1111-1111-111111111111",
  "author_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "title": "Не работает холодильник",
  "category": "equipment",
  "priority": "high",
  "status": "new",
  "assignee_id": null,
  "created_at": "2026-08-10T03:15:00Z",
  "updated_at": "2026-08-10T03:15:00Z",
  "description": "Компрессор не запускается после включения",
  "result": null,
  "cancellation_reason": null,
  "completed_at": null,
  "cancelled_at": null
}
```

### Список заявок с фильтрами и пагинацией

```bash
curl -s "http://localhost:8080/requests?status=new&limit=10&offset=0" \
  -H "X-User-Id: dddddddd-dddd-dddd-dddd-dddddddddddd"
```

```json
{
  "items": [
    {
      "id": "9f1c2e3a-4b5d-4e6f-8a9b-0c1d2e3f4a5b",
      "facility_id": "11111111-1111-1111-1111-111111111111",
      "author_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      "title": "Не работает холодильник",
      "category": "equipment",
      "priority": "high",
      "status": "new",
      "assignee_id": null,
      "created_at": "2026-08-10T03:15:00Z",
      "updated_at": "2026-08-10T03:15:00Z"
    }
  ],
  "limit": 10,
  "offset": 0,
  "total": 1
}
```

### Карточка заявки с историей

```bash
curl -s http://localhost:8080/requests/9f1c2e3a-4b5d-4e6f-8a9b-0c1d2e3f4a5b \
  -H "X-User-Id: dddddddd-dddd-dddd-dddd-dddddddddddd"
```

```json
{
  "id": "9f1c2e3a-4b5d-4e6f-8a9b-0c1d2e3f4a5b",
  "facility_id": "11111111-1111-1111-1111-111111111111",
  "author_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "title": "Не работает холодильник",
  "category": "equipment",
  "priority": "high",
  "status": "new",
  "assignee_id": null,
  "created_at": "2026-08-10T03:15:00Z",
  "updated_at": "2026-08-10T03:15:00Z",
  "description": "Компрессор не запускается после включения",
  "result": null,
  "cancellation_reason": null,
  "completed_at": null,
  "cancelled_at": null,
  "history": [
    {
      "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "old_status": null,
      "new_status": "new",
      "changed_by": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      "comment": null,
      "created_at": "2026-08-10T03:15:00Z"
    }
  ]
}
```

### Назначение специалиста (manager)

```bash
curl -s -X POST http://localhost:8080/requests/9f1c2e3a-4b5d-4e6f-8a9b-0c1d2e3f4a5b/assign \
  -H "Content-Type: application/json" \
  -H "X-User-Id: dddddddd-dddd-dddd-dddd-dddddddddddd" \
  -d '{"technician_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"}'
```

Успех – `200 OK`, `status` меняется на `"assigned"`, `assignee_id` заполнен (в ответе, как и во
всех командах `assign`/`start`/`complete`/`cancel`, массива `history` нет).

### Начало работы (назначенный technician)

```bash
curl -s -X POST http://localhost:8080/requests/9f1c2e3a-4b5d-4e6f-8a9b-0c1d2e3f4a5b/start \
  -H "X-User-Id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
```

Успех – `200 OK`, `status` → `"in_progress"`.

### Завершение заявки (назначенный technician)

```bash
curl -s -X POST http://localhost:8080/requests/9f1c2e3a-4b5d-4e6f-8a9b-0c1d2e3f4a5b/complete \
  -H "Content-Type: application/json" \
  -H "X-User-Id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" \
  -d '{"result": "Заменён компрессор, работоспособность проверена"}'
```

Успех – `200 OK`, `status` → `"completed"`, заполнены `result` и `completed_at`.

### Отмена заявки (автор или manager)

```bash
curl -s -X POST http://localhost:8080/requests/9f1c2e3a-4b5d-4e6f-8a9b-0c1d2e3f4a5b/cancel \
  -H "Content-Type: application/json" \
  -H "X-User-Id: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" \
  -d '{"reason": "Неисправность устранена сотрудниками объекта"}'
```

Успех – `200 OK`, `status` → `"cancelled"`, заполнены `cancellation_reason` и `cancelled_at`.

### Примеры ошибок

**401 – заголовок отсутствует или не UUID / пользователь не найден:**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/requests
# 401
```

```json
{"message": "Заголовок X-User-Id пустой"}
```

**403 – роль не разрешает операцию** (например, `manager` пытается создать заявку):

```bash
curl -s -X POST http://localhost:8080/requests \
  -H "Content-Type: application/json" \
  -H "X-User-Id: dddddddd-dddd-dddd-dddd-dddddddddddd" \
  -d '{"title":"...","description":"...","category":"equipment","priority":"low"}'
```

```json
{"message": "Роль пользователя не разрешает эту операцию"}
```

**404 – заявка не найдена или недоступна по области доступа** (сотрудник другого объекта):

```json
{"message": "Заявка не найдена"}
```

**409 – нарушение бизнес-правила или перехода статуса** (повторное назначение):

```json
{
  "message": "Заявку можно назначить только в статусе 'new'",
  "details": {"current_status": "assigned"}
}
```

**422 – ошибка схемы запроса** (слишком короткое описание). 

```json
{
  "message": "Ошибка валидации запроса",
  "details": {"field": "description: String should have at least 10 characters"}
}
```