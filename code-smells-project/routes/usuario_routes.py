from flask import Blueprint, jsonify, request

from controllers import usuario_controller
from middlewares.auth import requer_admin

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.get("/usuarios")
@requer_admin
def listar_usuarios():
    return jsonify({"dados": usuario_controller.listar(), "sucesso": True}), 200


@usuarios_bp.get("/usuarios/<int:usuario_id>")
@requer_admin
def buscar_usuario(usuario_id):
    return jsonify({"dados": usuario_controller.buscar(usuario_id), "sucesso": True}), 200


@usuarios_bp.post("/usuarios")
def criar_usuario():
    resultado = usuario_controller.criar(request.get_json(silent=True))
    return jsonify({"dados": resultado, "sucesso": True}), 201


@usuarios_bp.post("/login")
def login():
    usuario = usuario_controller.login(request.get_json(silent=True))
    return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200
