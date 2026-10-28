import logging

from werkzeug.exceptions import HTTPException

from utils.errors import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return {'error': error.message}, error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return error

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.error('Exceção não tratada: %s', error, exc_info=True)
        return {'error': 'Erro interno'}, 500
