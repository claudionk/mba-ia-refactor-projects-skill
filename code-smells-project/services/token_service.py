from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from controllers.erros import UnauthorizedError

SALT_TOKEN = "code-smells-auth"


def _serializador():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT_TOKEN)


def criar_token(usuario_id):
    return _serializador().dumps({"usuario_id": usuario_id})


def ler_token(token):
    """Devolve o usuario_id do token ou levanta UnauthorizedError."""
    try:
        dados = _serializador().loads(token, max_age=current_app.config["TOKEN_TTL_SEGUNDOS"])
    except SignatureExpired as erro:
        raise UnauthorizedError("Token expirado") from erro
    except BadSignature as erro:
        raise UnauthorizedError("Token invalido") from erro
    return dados["usuario_id"]
