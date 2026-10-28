class AppError(Exception):
    """Erro de negócio/validação convertido em resposta HTTP pelo middleware."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValidationError(AppError):
    def __init__(self, message):
        super().__init__(message, 400)


class NotFoundError(AppError):
    def __init__(self, message):
        super().__init__(message, 404)


class ConflictError(AppError):
    def __init__(self, message):
        super().__init__(message, 409)
