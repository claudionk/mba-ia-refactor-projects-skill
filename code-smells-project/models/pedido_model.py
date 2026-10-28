class PedidoModel:
    @staticmethod
    def get_all(db):
        return _listar(db)

    @staticmethod
    def get_by_usuario(db, usuario_id):
        return _listar(db, "WHERE p.usuario_id = ?", (usuario_id,))

    @staticmethod
    def create(db, usuario_id, total):
        cursor = db.execute("INSERT INTO pedidos (usuario_id, total) VALUES (?, ?)", (usuario_id, total))
        return cursor.lastrowid

    @staticmethod
    def add_item(db, pedido_id, produto_id, quantidade, preco_unitario):
        db.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            (pedido_id, produto_id, quantidade, preco_unitario),
        )

    @staticmethod
    def update_status(db, pedido_id, status):
        db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))

    @staticmethod
    def resumo(db):
        total_pedidos, faturamento = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM pedidos"
        ).fetchone()
        por_status = {
            row["status"]: row["quantidade"]
            for row in db.execute("SELECT status, COUNT(*) AS quantidade FROM pedidos GROUP BY status")
        }
        return {"total_pedidos": total_pedidos, "faturamento": faturamento, "por_status": por_status}


def _listar(db, where="", params=()):
    # Uma única query com JOIN: evita 1 + N + N*M consultas.
    rows = db.execute(
        f"""
        SELECT p.id AS pedido_id, p.usuario_id, p.status, p.total, p.criado_em,
               ip.produto_id, ip.quantidade, ip.preco_unitario, pr.nome AS produto_nome
        FROM pedidos p
        LEFT JOIN itens_pedido ip ON ip.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = ip.produto_id
        {where}
        ORDER BY p.id, ip.id
        """,
        params,
    ).fetchall()

    pedidos = {}
    for row in rows:
        pedido = pedidos.setdefault(row["pedido_id"], {
            "id": row["pedido_id"],
            "usuario_id": row["usuario_id"],
            "status": row["status"],
            "total": row["total"],
            "criado_em": row["criado_em"],
            "itens": [],
        })
        if row["produto_id"] is not None:
            pedido["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] or "Desconhecido",
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(pedidos.values())
