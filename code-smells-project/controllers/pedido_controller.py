import logging

from controllers.erros import ValidationError
from controllers.validacao import eh_inteiro, exige_objeto
from database import get_db, transacao
from models.pedido_model import PedidoModel
from models.produto_model import ProdutoModel

logger = logging.getLogger(__name__)

STATUS_PEDIDO = ("pendente", "aprovado", "enviado", "entregue", "cancelado")


def criar(dados):
    dados = exige_objeto(dados)
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not eh_inteiro(usuario_id):
        raise ValidationError("Usuario ID deve ser inteiro")
    if not isinstance(itens, list) or not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    itens_validados = [_validar_item(item) for item in itens]

    db = get_db()
    with transacao(db):
        total = 0
        linhas = []
        necessario = {}
        for produto_id, quantidade in itens_validados:
            produto = ProdutoModel.get_by_id(db, produto_id)
            if produto is None:
                raise ValidationError(f"Produto {produto_id} nao encontrado")
            # Soma por produto: o mesmo item repetido nao pode estourar o estoque.
            necessario[produto_id] = necessario.get(produto_id, 0) + quantidade
            if produto["estoque"] < necessario[produto_id]:
                raise ValidationError(f"Estoque insuficiente para {produto['nome']}")
            total += produto["preco"] * quantidade
            linhas.append((produto_id, quantidade, produto["preco"]))

        pedido_id = PedidoModel.create(db, usuario_id, total)
        for produto_id, quantidade, preco in linhas:
            PedidoModel.add_item(db, pedido_id, produto_id, quantidade, preco)
            ProdutoModel.decrementar_estoque(db, produto_id, quantidade)

    logger.info("Pedido %s criado para usuario_id=%s", pedido_id, usuario_id)
    return {"pedido_id": pedido_id, "total": total}


def listar_todos():
    return PedidoModel.get_all(get_db())


def listar_por_usuario(usuario_id):
    return PedidoModel.get_by_usuario(get_db(), usuario_id)


def atualizar_status(pedido_id, dados):
    dados = dados if isinstance(dados, dict) else {}
    novo_status = dados.get("status", "")
    if novo_status not in STATUS_PEDIDO:
        raise ValidationError("Status inválido")

    db = get_db()
    with transacao(db):
        PedidoModel.update_status(db, pedido_id, novo_status)
    logger.info("Status do pedido %s atualizado para %s", pedido_id, novo_status)


def _validar_item(item):
    if not isinstance(item, dict):
        raise ValidationError("Item do pedido inválido")
    produto_id = item.get("produto_id")
    quantidade = item.get("quantidade")
    if not eh_inteiro(produto_id):
        raise ValidationError("produto_id deve ser inteiro")
    if not eh_inteiro(quantidade) or quantidade <= 0:
        raise ValidationError("Quantidade deve ser maior que zero")
    return produto_id, quantidade
