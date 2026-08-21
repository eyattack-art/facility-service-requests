from typing import Any

_VALIDATION_MESSAGES: dict[str, str] = {
    "string_too_short": "слишком короткое значение",
    "string_too_long": "слишком длинное значение",
    "missing": "обязательное поле отсутствует",
    "extra_forbidden": "поле не предусмотрено запросом",
    "enum": "недопустимое значение",
    "uuid_parsing": "некорректный UUID",
    "int_parsing": "ожидалось целое число",
    "greater_than_equal": "значение слишком маленькое",
    "less_than_equal": "значение слишком большое",
    "value_error": "некорректное значение",
}


class AppError(Exception):
    def __init__(self, message: str, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class UnauthorizedError(AppError):
    """401 - заголовок отсутствует, не UUID, или пользователь не найден."""


class ForbiddenError(AppError):
    """403 - пользователь неактивен или роль не разрешает операцию."""


class NotFoundError(AppError):
    """404 - сущность не найдена или недоступна по области доступа."""


class ConflictError(AppError):
    """409 - нарушение бизнес-правила или перехода статус"""


def humanize_validation_error(error: dict[str, Any]) -> str:
    field_path = ".".join(str(part) for part in error["loc"][1:]) or str(error["loc"][-1])
    reason = _VALIDATION_MESSAGES.get(error["type"], error["msg"])
    return f"{field_path}: {reason}"
