import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from controllers.erros import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def erro_de_aplicacao(e):
        return jsonify({"erro": e.mensagem, "sucesso": False}), e.status_code

    @app.errorhandler(HTTPException)
    def erro_http(e):
        return jsonify({"erro": e.description, "sucesso": False}), e.code

    @app.errorhandler(Exception)
    def erro_inesperado(e):
        logger.exception("Erro nao tratado")
        return jsonify({"erro": "Erro interno do servidor", "sucesso": False}), 500
