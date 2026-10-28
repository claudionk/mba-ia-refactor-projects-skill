from flask import Blueprint, jsonify

from controllers import relatorio_controller
from middlewares.auth import requer_admin

relatorios_bp = Blueprint("relatorios", __name__)


@relatorios_bp.get("/relatorios/vendas")
@requer_admin
def relatorio_vendas():
    return jsonify({"dados": relatorio_controller.vendas(), "sucesso": True}), 200
