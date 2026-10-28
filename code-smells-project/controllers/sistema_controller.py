import logging

from config.settings import Settings
from database import get_db, transacao
from models.sistema_model import SistemaModel

logger = logging.getLogger(__name__)


def health():
    return {
        "status": "ok",
        "database": "connected",
        "counts": SistemaModel.contar_registros(get_db()),
        "versao": Settings.VERSAO,
    }


def resetar_banco():
    db = get_db()
    with transacao(db):
        SistemaModel.limpar_tabelas(db)
    logger.warning("Banco de dados resetado via /admin/reset-db")
