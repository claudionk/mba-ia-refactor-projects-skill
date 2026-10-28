TABELAS = ("produtos", "usuarios", "pedidos")
# Ordem respeita as chaves de dependência entre tabelas.
TABELAS_PARA_LIMPAR = ("itens_pedido", "pedidos", "produtos", "usuarios")


class SistemaModel:
    @staticmethod
    def contar_registros(db):
        return {
            tabela: db.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
            for tabela in TABELAS
        }

    @staticmethod
    def limpar_tabelas(db):
        for tabela in TABELAS_PARA_LIMPAR:
            db.execute(f"DELETE FROM {tabela}")
