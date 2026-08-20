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

Выведет UUID созданных пользователей — используются в заголовке `X-User-Id`.

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