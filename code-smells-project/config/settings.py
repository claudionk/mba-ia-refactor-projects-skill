import os
from pathlib import Path

from dotenv import load_dotenv

# Carrega o .env da raiz do projeto. Variáveis já definidas no ambiente têm prioridade.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


PREFIXO_PLACEHOLDER = "troque-por-"


def _segredo(nome):
    """Placeholder do .env.example nunca vale como credencial."""
    valor = os.environ.get(nome, "")
    return "" if valor.startswith(PREFIXO_PLACEHOLDER) else valor


def _obrigatoria(nome):
    valor = _segredo(nome)
    if not valor:
        raise RuntimeError(
            f"Defina {nome} no ambiente ou no .env. "
            "Gere um valor com: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return valor


class Settings:
    VERSAO = "1.0.0"
    SECRET_KEY = _obrigatoria("SECRET_KEY")
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DB_PATH = os.environ.get("DB_PATH", "loja.db")
    TOKEN_TTL_SEGUNDOS = int(os.environ.get("TOKEN_TTL_SEGUNDOS", str(8 * 3600)))
    # Exigido no header X-Admin-Token. Vazio ou placeholder = operações administrativas desabilitadas.
    ADMIN_TOKEN = _segredo("ADMIN_TOKEN")
    # Lidas só pelo comando criar-admin. Sem valor padrão: o comando falha se estiverem vazias.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
