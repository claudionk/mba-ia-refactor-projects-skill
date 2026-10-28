import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# Carrega o .env da raiz do projeto. Variáveis já definidas no ambiente têm prioridade.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings:
    VERSAO = "1.0.0"
    # Sem fallback literal: sem SECRET_KEY no ambiente, uma chave aleatória é gerada a cada boot.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DB_PATH = os.environ.get("DB_PATH", "loja.db")
    # Exigido no header X-Admin-Token. Vazio = operações administrativas desabilitadas.
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
