from routes.pedido_routes import pedidos_bp
from routes.produto_routes import produtos_bp
from routes.relatorio_routes import relatorios_bp
from routes.sistema_routes import sistema_bp
from routes.usuario_routes import usuarios_bp


def registrar_rotas(app):
    for blueprint in (produtos_bp, usuarios_bp, pedidos_bp, relatorios_bp, sistema_bp):
        app.register_blueprint(blueprint)
