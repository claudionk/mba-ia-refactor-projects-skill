COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


class ProdutoModel:
    @staticmethod
    def get_all(db):
        rows = db.execute(f"SELECT {COLUNAS} FROM produtos ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(db, produto_id):
        row = db.execute(f"SELECT {COLUNAS} FROM produtos WHERE id = ?", (produto_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def search(db, termo="", categoria=None, preco_min=None, preco_max=None):
        query = f"SELECT {COLUNAS} FROM produtos WHERE 1=1"
        params = []
        if termo:
            query += " AND (nome LIKE ? OR descricao LIKE ?)"
            params += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            query += " AND categoria = ?"
            params.append(categoria)
        if preco_min is not None:
            query += " AND preco >= ?"
            params.append(preco_min)
        if preco_max is not None:
            query += " AND preco <= ?"
            params.append(preco_max)
        rows = db.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def create(db, nome, descricao, preco, estoque, categoria):
        cursor = db.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
        return cursor.lastrowid

    @staticmethod
    def update(db, produto_id, nome, descricao, preco, estoque, categoria):
        db.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )

    @staticmethod
    def delete(db, produto_id):
        db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))

    @staticmethod
    def decrementar_estoque(db, produto_id, quantidade):
        db.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (quantidade, produto_id))
