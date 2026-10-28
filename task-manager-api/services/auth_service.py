from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from utils.errors import AppError

TOKEN_SALT = 'task-manager-auth'


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=TOKEN_SALT)


def create_token(user):
    return _serializer().dumps({'user_id': user.id})


def read_token(token):
    """Devolve o user_id do token ou levanta AppError 401."""
    try:
        payload = _serializer().loads(token, max_age=current_app.config['TOKEN_TTL_SECONDS'])
    except SignatureExpired:
        raise AppError('Token expirado', 401)
    except BadSignature:
        raise AppError('Token inválido', 401)
    return payload['user_id']
