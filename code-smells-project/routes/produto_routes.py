from flask import Blueprint, jsonify, request

from controllers import produto_controller
from middlewares.auth import requer_admin

produtos_bp = Blueprint("produtos", __name__)


@produtos_bp.get("/produtos")
def listar_produtos():
    return jsonify({"dados": produto_controller.listar(), "sucesso": True}), 200


@produtos_bp.get("/produtos/busca")
def buscar_produtos():
    resultados = produto_controller.buscar_com_filtros(
        request.args.get("q", ""),
        request.args.get("categoria"),
        request.args.get("preco_min"),
        request.args.get("preco_max"),
    )
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200


@produtos_bp.get("/produtos/<int:produto_id>")
def buscar_produto(produto_id):
    return jsonify({"dados": produto_controller.buscar(produto_id), "sucesso": True}), 200


@produtos_bp.post("/produtos")
@requer_admin
def criar_produto():
    resultado = produto_controller.criar(request.get_json(silent=True))
    return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Produto criado"}), 201


@produtos_bp.put("/produtos/<int:produto_id>")
@requer_admin
def atualizar_produto(produto_id):
    produto_controller.atualizar(produto_id, request.get_json(silent=True))
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


@produtos_bp.delete("/produtos/<int:produto_id>")
@requer_admin
def deletar_produto(produto_id):
    produto_controller.deletar(produto_id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
