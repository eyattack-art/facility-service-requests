class AppError(Exception):
    def __init__(self, message: str, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class UnauthorizedError(AppError):
    """401 — заголовок отсутствует, не UUID, или пользователь не найден."""


class ForbiddenError(AppError):
    """403 — пользователь неактивен или роль не разрешает операцию."""


class NotFoundError(AppError):
    """404 — сущность не найдена или недоступна по области доступа."""


class ConflictError(AppError):
    """409"""
