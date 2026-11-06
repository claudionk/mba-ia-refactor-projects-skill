import hmac
from functools import wraps

from flask import current_app, g, request

from controllers.erros import ForbiddenError, UnauthorizedError
from database import get_db
from models.usuario_model import UsuarioModel
from services.token_service import ler_token

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


def requer_usuario(view):
    @wraps(view)
    def protegida(*args, **kwargs):
        esquema, _, token = request.headers.get("Authorization", "").partition(" ")
        if esquema.lower() != "bearer" or not token:
            raise UnauthorizedError("Autenticacao necessaria")
        usuario = UsuarioModel.get_by_id(get_db(), ler_token(token.strip()))
        if usuario is None:
            raise UnauthorizedError("Token invalido")
        g.usuario_atual = usuario
        return view(*args, **kwargs)

    return protegida


def usuario_atual():
    return g.usuario_atual
