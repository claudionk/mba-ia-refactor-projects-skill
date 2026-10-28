import hmac
import logging

from werkzeug.security import check_password_hash, generate_password_hash

from controllers.erros import NotFoundError, UnauthorizedError, ValidationError
from controllers.validacao import exige_objeto
from database import get_db, transacao
from models.usuario_model import UsuarioModel

logger = logging.getLogger(__name__)

# Prefixos gerados por werkzeug.security. Qualquer outro valor é senha legada em texto puro.
PREFIXOS_HASH = ("scrypt:", "pbkdf2:")


def listar():
    return UsuarioModel.get_all(get_db())


def buscar(usuario_id):
    usuario = UsuarioModel.get_by_id(get_db(), usuario_id)
    if usuario is None:
        raise NotFoundError("Usuário nao encontrado")
    return usuario


def criar(dados):
    dados = exige_objeto(dados)
    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not all(isinstance(valor, str) for valor in (nome, email, senha)):
        raise ValidationError("Nome, email e senha devem ser textos")

    db = get_db()
    with transacao(db):
        usuario_id = UsuarioModel.create(db, nome, email, generate_password_hash(senha))
    return {"id": usuario_id}


def login(dados):
    dados = dados if isinstance(dados, dict) else {}
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")
    if not isinstance(email, str) or not isinstance(senha, str):
        raise ValidationError("Email e senha devem ser textos")

    db = get_db()
    usuario = UsuarioModel.get_by_email(db, email)
    if usuario is None or not _senha_confere(db, usuario, senha):
        logger.warning("Login falhou")
        raise UnauthorizedError("Email ou senha inválidos")

    logger.info("Login bem-sucedido: usuario_id=%s", usuario["id"])
    return {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "tipo": usuario["tipo"],
    }


def _senha_confere(db, usuario, senha):
    armazenada = usuario["senha"] or ""
    if armazenada.startswith(PREFIXOS_HASH):
        return check_password_hash(armazenada, senha)

    # Migração: senha legada em texto puro é validada uma vez e regravada com hash.
    if not hmac.compare_digest(armazenada, senha):
        return False
    with transacao(db):
        UsuarioModel.update_senha(db, usuario["id"], generate_password_hash(senha))
    return True
