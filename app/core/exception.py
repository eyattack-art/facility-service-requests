class AppError(Exception):
    pass


class UnauthorizedError(AppError):
    """401 — заголовок отсутствует, не UUID, или пользователь не найден."""


class ForbiddenError(AppError):
    """403 — пользователь неактивен или роль не разрешает операцию."""
