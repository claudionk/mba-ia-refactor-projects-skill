import hmac
from functools import wraps

from flask import current_app, request

from controllers.erros import ForbiddenError, UnauthorizedError

HEADER_ADMIN = "X-Admin-Token"


def requer_admin(view):
    @wraps(view)
    def protegida(*args, **kwargs):
        token_esperado = current_app.config["ADMIN_TOKEN"]
        if not token_esperado:
            raise ForbiddenError("Operacao administrativa desabilitada: ADMIN_TOKEN nao configurado")
        token = request.headers.get(HEADER_ADMIN, "")
        if not hmac.compare_digest(token.encode(), token_esperado.encode()):
            raise UnauthorizedError("Token administrativo invalido")
        return view(*args, **kwargs)

    return protegida
