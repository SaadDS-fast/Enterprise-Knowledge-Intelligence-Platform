from app.exceptions.codes import ErrorCode


class AppError(Exception):
    def __init__(
        self, code: ErrorCode, message: str, status_code: int = 400, details: dict | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(ErrorCode.NOT_FOUND, message, 404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have permission for this action") -> None:
        super().__init__(ErrorCode.FORBIDDEN, message, 403)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.CONFLICT, message, 409)
