import logging

import click
from flask import Flask, current_app
from flask.cli import with_appcontext
from flask_cors import CORS

from config.settings import Settings
from controllers import usuario_controller
from controllers.erros import ValidationError
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
    app.cli.add_command(criar_admin)
    return app


@click.command("criar-admin")
@with_appcontext
def criar_admin():
    """Cria a conta admin com ADMIN_EMAIL e ADMIN_PASSWORD do ambiente."""
    try:
        usuario_id = usuario_controller.criar_admin(
            current_app.config["ADMIN_EMAIL"],
            current_app.config["ADMIN_PASSWORD"],
        )
    except ValidationError as erro:
        raise click.ClickException(erro.mensagem) from erro
    click.echo(f"Admin criado: id={usuario_id}")


app = create_app()

if __name__ == "__main__":
    logging.getLogger(__name__).info("Servidor em http://%s:%s", Settings.HOST, Settings.PORT)
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
