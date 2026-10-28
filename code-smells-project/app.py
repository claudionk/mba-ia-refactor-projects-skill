import logging

from flask import Flask
from flask_cors import CORS

from config.settings import Settings
from database import init_app
from middlewares.error_handler import register_error_handlers
from routes import registrar_rotas


def create_app():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    app = Flask(__name__)
    app.config.from_object(Settings)
    CORS(app)
    init_app(app)
    register_error_handlers(app)
    registrar_rotas(app)
    return app


app = create_app()

if __name__ == "__main__":
    logging.getLogger(__name__).info("Servidor em http://%s:%s", Settings.HOST, Settings.PORT)
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
