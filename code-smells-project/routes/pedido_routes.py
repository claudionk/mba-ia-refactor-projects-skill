from flask import Blueprint, jsonify, request

from controllers import pedido_controller
from middlewares.auth import requer_admin

pedidos_bp = Blueprint("pedidos", __name__)


@pedidos_bp.post("/pedidos")
def criar_pedido():
    resultado = pedido_controller.criar(request.get_json(silent=True))
    return jsonify({
        "dados": resultado,
        "sucesso": True,
        "mensagem": "Pedido criado com sucesso",
    }), 201


@pedidos_bp.get("/pedidos")
@requer_admin
def listar_todos_pedidos():
    return jsonify({"dados": pedido_controller.listar_todos(), "sucesso": True}), 200


@pedidos_bp.get("/pedidos/usuario/<int:usuario_id>")
def listar_pedidos_usuario(usuario_id):
    return jsonify({"dados": pedido_controller.listar_por_usuario(usuario_id), "sucesso": True}), 200


@pedidos_bp.put("/pedidos/<int:pedido_id>/status")
@requer_admin
def atualizar_status_pedido(pedido_id):
    pedido_controller.atualizar_status(pedido_id, request.get_json(silent=True))
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
