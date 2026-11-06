import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from itsdangerous import URLSafeTimedSerializer

RAIZ = Path(__file__).resolve().parent.parent
TOKEN_ADMIN = "token-admin-usado-apenas-nos-testes"
SENHA = "senha-de-teste"

os.environ.update(
    SECRET_KEY="segredo-usado-apenas-nos-testes",
    DB_PATH=str(Path(tempfile.mkdtemp()) / "testes.db"),
    ADMIN_TOKEN=TOKEN_ADMIN,
    ADMIN_EMAIL="",
    ADMIN_PASSWORD="",
    DEBUG="false",
)

from app import app  # noqa: E402

ADMIN_HEADERS = {"X-Admin-Token": TOKEN_ADMIN}


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        banco = sqlite3.connect(app.config["DB_PATH"])
        banco.execute("DELETE FROM itens_pedido")
        banco.execute("DELETE FROM pedidos")
        banco.execute("DELETE FROM usuarios")
        banco.execute("UPDATE produtos SET estoque = 10")
        banco.commit()
        banco.close()
        self.ana = self._cadastrar("ana")
        self.bia = self._cadastrar("bia")

    def _cadastrar(self, nome):
        email = f"{nome}@x.com"
        resposta = self.client.post("/usuarios", json={"nome": nome, "email": email, "senha": SENHA})
        self.assertEqual(resposta.status_code, 201)
        login = self.client.post("/login", json={"email": email, "senha": SENHA}).get_json()
        return {"id": resposta.get_json()["dados"]["id"], "cabecalho": {"Authorization": f"Bearer {login['token']}"}}

    def _pedido(self, usuario_id, cabecalho=None):
        return self.client.post(
            "/pedidos",
            json={"usuario_id": usuario_id, "itens": [{"produto_id": 1, "quantidade": 1}]},
            headers=cabecalho or {},
        )


class ContratoTest(ApiTestCase):
    def test_rotas_publicas(self):
        for url in ("/", "/health", "/produtos", "/produtos/1", "/produtos/busca?q=Mouse"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_rotas_administrativas_com_token(self):
        for url in ("/usuarios", f"/usuarios/{self.ana['id']}", "/pedidos", "/relatorios/vendas"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, headers=ADMIN_HEADERS).status_code, 200)

    def test_login_mantem_o_formato_e_nao_devolve_senha(self):
        corpo = self.client.post("/login", json={"email": "ana@x.com", "senha": SENHA}).get_json()
        self.assertEqual(corpo["mensagem"], "Login OK")
        self.assertEqual(corpo["dados"]["email"], "ana@x.com")
        self.assertNotIn("senha", corpo["dados"])

    def test_health_nao_expoe_segredo(self):
        self.assertNotIn("secret_key", self.client.get("/health").get_json())

    def test_sql_injection_na_busca_nao_vaza_tabelas(self):
        ataque = "x%') UNION SELECT id,nome,email,senha,tipo,criado_em,NULL,NULL FROM usuarios --"
        resposta = self.client.get("/produtos/busca", query_string={"q": ataque})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json()["dados"], [])


class SegredosTest(ApiTestCase):
    def _rodar(self, codigo, **ambiente):
        return subprocess.run(
            [sys.executable, "-c", codigo], cwd=RAIZ, env={**os.environ, **ambiente}, capture_output=True, text=True
        )

    def test_aplicacao_nao_inicia_sem_segredo_real(self):
        for valor in ("", "troque-por-uma-chave-segura-em-producao"):
            with self.subTest(valor=valor):
                resultado = self._rodar("import app", SECRET_KEY=valor)
                self.assertNotEqual(resultado.returncode, 0)
                self.assertIn("SECRET_KEY", resultado.stderr)

    def test_placeholder_de_admin_token_nao_vale_como_credencial(self):
        codigo = (
            "from app import app\n"
            "h = {'X-Admin-Token': 'troque-por-um-token-admin-forte'}\n"
            "print(app.test_client().get('/usuarios', headers=h).status_code)\n"
        )
        resultado = self._rodar(codigo, ADMIN_TOKEN="troque-por-um-token-admin-forte")
        self.assertEqual(resultado.stdout.strip().splitlines()[-1], "403")

    def test_rotas_admin_negam_sem_token_e_com_token_errado(self):
        self.assertEqual(self.client.get("/usuarios").status_code, 401)
        self.assertEqual(self.client.get("/usuarios", headers={"X-Admin-Token": "errado"}).status_code, 401)

    def test_query_arbitraria_foi_removida(self):
        self.assertEqual(self.client.post("/admin/query", json={"sql": "SELECT 1"}).status_code, 404)


class PedidosTest(ApiTestCase):
    def test_pedido_exige_login(self):
        self.assertEqual(self._pedido(self.ana["id"]).status_code, 401)
        self.assertEqual(self.client.get(f"/pedidos/usuario/{self.ana['id']}").status_code, 401)

    def test_token_forjado_e_recusado(self):
        for segredo in ("minha-chave-super-secreta-123", "troque-por-uma-chave-segura-em-producao"):
            forjado = URLSafeTimedSerializer(segredo, salt="code-smells-auth").dumps({"usuario_id": self.ana["id"]})
            with self.subTest(segredo=segredo):
                self.assertEqual(self._pedido(self.ana["id"], {"Authorization": f"Bearer {forjado}"}).status_code, 401)

    def test_cliente_cria_e_le_o_proprio_pedido(self):
        self.assertEqual(self._pedido(self.ana["id"], self.ana["cabecalho"]).status_code, 201)
        resposta = self.client.get(f"/pedidos/usuario/{self.ana['id']}", headers=self.ana["cabecalho"])
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.get_json()["dados"]), 1)

    def test_cliente_nao_age_em_nome_de_outro(self):
        self.assertEqual(self._pedido(self.bia["id"], self.ana["cabecalho"]).status_code, 403)
        self.assertEqual(self.client.get(f"/pedidos/usuario/{self.bia['id']}", headers=self.ana["cabecalho"]).status_code, 403)

    def test_quantidade_negativa_e_recusada(self):
        resposta = self.client.post(
            "/pedidos",
            json={"usuario_id": self.ana["id"], "itens": [{"produto_id": 1, "quantidade": -100}]},
            headers=self.ana["cabecalho"],
        )
        self.assertEqual(resposta.status_code, 400)


class SeedEAdminTest(ApiTestCase):
    def test_credenciais_antigas_do_seed_nao_entram(self):
        for email, senha in (("admin@loja.com", "admin123"), ("joao@email.com", "123456"), ("maria@email.com", "senha123")):
            with self.subTest(email=email):
                self.assertEqual(self.client.post("/login", json={"email": email, "senha": senha}).status_code, 401)

    def test_criar_admin_falha_sem_variaveis_e_cria_com_elas(self):
        runner = app.test_cli_runner()
        self.assertNotEqual(runner.invoke(args=["criar-admin"]).exit_code, 0)

        app.config.update(ADMIN_EMAIL="root@x.com", ADMIN_PASSWORD=SENHA)
        self.addCleanup(app.config.update, ADMIN_EMAIL="", ADMIN_PASSWORD="")
        self.assertEqual(runner.invoke(args=["criar-admin"]).exit_code, 0)
        self.assertNotEqual(runner.invoke(args=["criar-admin"]).exit_code, 0)

        login = self.client.post("/login", json={"email": "root@x.com", "senha": SENHA}).get_json()
        self.assertEqual(login["dados"]["tipo"], "admin")
        cabecalho = {"Authorization": f"Bearer {login['token']}"}
        self.assertEqual(self.client.get(f"/pedidos/usuario/{self.ana['id']}", headers=cabecalho).status_code, 200)


if __name__ == "__main__":
    unittest.main()
