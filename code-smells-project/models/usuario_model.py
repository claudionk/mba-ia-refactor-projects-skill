PUBLICO = "id, nome, email, tipo, criado_em"


class UsuarioModel:
    @staticmethod
    def get_all(db):
        rows = db.execute(f"SELECT {PUBLICO} FROM usuarios ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(db, usuario_id):
        row = db.execute(f"SELECT {PUBLICO} FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_email(db, email):
        row = db.execute(
            "SELECT id, nome, email, senha, tipo FROM usuarios WHERE email = ? ORDER BY id LIMIT 1",
            (email,),
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def create(db, nome, email, senha_hash, tipo="cliente"):
        cursor = db.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, tipo),
        )
        return cursor.lastrowid

    @staticmethod
    def update_senha(db, usuario_id, senha_hash):
        db.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (senha_hash, usuario_id))
