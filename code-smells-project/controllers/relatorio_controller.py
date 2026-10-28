from database import get_db
from models.pedido_model import PedidoModel

# (faturamento acima de, percentual de desconto), da faixa mais alta para a mais baixa.
FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))


def vendas():
    resumo = PedidoModel.resumo(get_db())
    faturamento = resumo["faturamento"]
    total_pedidos = resumo["total_pedidos"]
    por_status = resumo["por_status"]
    desconto = calcular_desconto(faturamento)

    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": por_status.get("pendente", 0),
        "pedidos_aprovados": por_status.get("aprovado", 0),
        "pedidos_cancelados": por_status.get("cancelado", 0),
        "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
    }


def calcular_desconto(faturamento):
    for limite, percentual in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * percentual
    return 0
