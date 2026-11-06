import os
from pathlib import Path

from dotenv import load_dotenv

# Carrega o .env da raiz do projeto. Variáveis já definidas no ambiente têm prioridade.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _obrigatoria(nome):
    valor = os.environ.get(nome)
    if not valor:
        raise RuntimeError(f"Variavel de ambiente obrigatoria nao configurada: {nome}")
    return valor


class Settings:
    VERSAO = "1.0.0"
    SECRET_KEY = _obrigatoria("SECRET_KEY")
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DB_PATH = os.environ.get("DB_PATH", "loja.db")
    # Exigido no header X-Admin-Token. Vazio = operações administrativas desabilitadas.
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
    # Lidas só pelo comando criar-admin. Sem valor padrão: o comando falha se estiverem vazias.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
