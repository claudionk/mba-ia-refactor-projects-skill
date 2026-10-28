from flask import g, request

from models.user_model import User
from services.auth_service import read_token
from utils.errors import AppError

PUBLIC_ENDPOINTS = {'index', 'health', 'users.login'}
PUBLIC_ENDPOINT_METHODS = {('users.create_user', 'POST')}


def _is_public():
    endpoint = request.endpoint
    return (
        endpoint is None  # rota inexistente: deixa o Flask responder 404
        or request.method == 'OPTIONS'
        or endpoint in PUBLIC_ENDPOINTS
        or (endpoint, request.method) in PUBLIC_ENDPOINT_METHODS
    )


def _load_current_user():
    header = request.headers.get('Authorization', '')
    scheme, _, token = header.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise AppError('Autenticacao necessaria', 401)
    user = User.get(read_token(token.strip()))
    if not user or not user.active:
        raise AppError('Token inválido', 401)
    return user


def current_user():
    """Usuário autenticado da requisição, ou None nas rotas públicas sem token."""
    return g.get('current_user')


def register_auth(app):
    @app.before_request
    def authenticate():
        if not _is_public():
            g.current_user = _load_current_user()
            return
        try:  # rota pública: token válido identifica o chamador, inválido o trata como anônimo
            g.current_user = _load_current_user()
        except AppError:
            g.current_user = None
