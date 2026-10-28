import logging

from flask import Flask
from flask_cors import CORS

from config.settings import DEV_SECRET_KEY, Settings
from database import db
from middlewares.auth import register_auth
from middlewares.error_handler import register_error_handlers
from routes.category_routes import category_bp
from routes.report_routes import report_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp
from utils.time_utils import utc_now

logging.basicConfig(level=Settings.LOG_LEVEL, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Settings)
    if Settings.SECRET_KEY == DEV_SECRET_KEY:
        if not Settings.DEBUG:
            raise RuntimeError('Defina SECRET_KEY no ambiente/.env antes de iniciar fora do modo DEBUG.')
        logger.warning('SECRET_KEY não definida; usando chave de desenvolvimento.')

    CORS(app)
    db.init_app(app)

    for blueprint in (task_bp, user_bp, category_bp, report_bp):
        app.register_blueprint(blueprint)
    register_auth(app)
    register_error_handlers(app)

    @app.route('/health')
    def health():
        return {'status': 'ok', 'timestamp': str(utc_now())}

    @app.route('/')
    def index():
        return {'message': 'Task Manager API', 'version': '1.0'}

    with app.app_context():
        import models  # noqa: F401  (registra os models antes do create_all)
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=Settings.DEBUG, host=Settings.HOST, port=Settings.PORT)
