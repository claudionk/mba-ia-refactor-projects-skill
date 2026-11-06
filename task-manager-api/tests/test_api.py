import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from itsdangerous import URLSafeTimedSerializer

RAIZ = Path(__file__).resolve().parent.parent
SECRET_KEY = 'segredo-usado-apenas-nos-testes'

os.environ.update(
    SECRET_KEY=SECRET_KEY,
    DATABASE_URL=f"sqlite:///{(Path(tempfile.mkdtemp()) / 'testes.db').as_posix()}",
    ADMIN_EMAIL='',
    ADMIN_PASSWORD='',
    DEBUG='false',
)

from app import app  # noqa: E402
from database import db  # noqa: E402
from models.category_model import Category  # noqa: E402
from models.task_model import Task  # noqa: E402
from models.user_model import User  # noqa: E402
import seed  # noqa: E402

SENHA = 'senha-de-teste'


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()
            self.ids = {}
            for name, role in (('admin', 'admin'), ('gerente', 'manager'), ('ana', 'user'), ('bia', 'user')):
                user = User(name=name, email=f'{name}@x.com', role=role)
                user.set_password(SENHA)
                db.session.add(user)
                db.session.flush()
                self.ids[name] = user.id
            task = Task(title='Task da Bia', user_id=self.ids['bia'])
            category = Category(name='Backend')
            db.session.add_all([task, category])
            db.session.commit()
            self.task_id, self.category_id = task.id, category.id
        self.tokens = {name: self._login(name) for name in self.ids}

    def _login(self, name):
        resposta = self.client.post('/login', json={'email': f'{name}@x.com', 'password': SENHA})
        self.assertEqual(resposta.status_code, 200)
        return resposta.get_json()['token']

    def _como(self, name):
        return {'Authorization': f'Bearer {self.tokens[name]}'}

    def _status(self, method, url, name=None, **kwargs):
        headers = self._como(name) if name else {}
        return self.client.open(url, method=method, headers=headers, **kwargs).status_code


class ContratoTest(ApiTestCase):
    def test_rotas_publicas(self):
        self.assertEqual(self._status('GET', '/'), 200)
        self.assertEqual(self._status('GET', '/health'), 200)

    def test_rotas_respondem_para_admin(self):
        rotas = [
            ('GET', '/tasks'), ('GET', f'/tasks/{self.task_id}'), ('GET', '/tasks/search?q=Task'),
            ('GET', '/tasks/stats'), ('GET', '/users'), ('GET', f"/users/{self.ids['bia']}"),
            ('GET', f"/users/{self.ids['bia']}/tasks"), ('GET', '/categories'), ('GET', '/reports/summary'),
            ('GET', f"/reports/user/{self.ids['bia']}"),
        ]
        for method, url in rotas:
            with self.subTest(url=url):
                self.assertEqual(self._status(method, url, 'admin'), 200)

    def test_crud_de_task_do_proprio_usuario(self):
        criada = self.client.post('/tasks', json={'title': 'Minha task'}, headers=self._como('ana'))
        self.assertEqual(criada.status_code, 201)
        self.assertEqual(criada.get_json()['user_id'], self.ids['ana'])
        url = f"/tasks/{criada.get_json()['id']}"
        self.assertEqual(self._status('PUT', url, 'ana', json={'status': 'done'}), 200)
        self.assertEqual(self._status('DELETE', url, 'ana'), 200)

    def test_senha_nunca_sai_na_api(self):
        resposta = self.client.post('/login', json={'email': 'ana@x.com', 'password': SENHA}).get_json()
        self.assertNotIn('password', resposta['user'])

    def test_entrada_invalida_responde_400(self):
        self.assertEqual(self._status('POST', '/tasks', 'ana', json={'title': 'abcd', 'priority': 'x'}), 400)
        self.assertEqual(self._status('GET', '/tasks/search?priority=abc', 'ana'), 400)


class AutenticacaoTest(ApiTestCase):
    def test_rotas_exigem_login(self):
        for url in ('/tasks', '/users', '/categories', '/reports/summary', '/tasks/stats'):
            with self.subTest(url=url):
                self.assertEqual(self._status('GET', url), 401)
        self.assertEqual(self._status('DELETE', f"/users/{self.ids['bia']}"), 401)
        self.assertEqual(self._status('DELETE', f'/tasks/{self.task_id}'), 401)

    def test_token_antigo_previsivel_e_recusado(self):
        cabecalho = {'Authorization': f"Bearer fake-jwt-token-{self.ids['admin']}"}
        self.assertEqual(self.client.get('/users', headers=cabecalho).status_code, 401)

    def test_token_forjado_com_segredo_de_exemplo_e_recusado(self):
        for segredo in ('change-me', 'super-secret-key-123', 'troque-por-uma-chave-secreta'):
            forjado = URLSafeTimedSerializer(segredo, salt='task-manager-auth').dumps({'user_id': self.ids['admin']})
            with self.subTest(segredo=segredo):
                self.assertEqual(self.client.get('/users', headers={'Authorization': f'Bearer {forjado}'}).status_code, 401)

    def test_usuario_removido_perde_o_acesso(self):
        self.assertEqual(self._status('DELETE', f"/users/{self.ids['ana']}", 'admin'), 200)
        self.assertEqual(self._status('GET', '/tasks', 'ana'), 401)


class AutorizacaoTest(ApiTestCase):
    def test_usuario_comum_nao_age_sobre_recurso_de_outro(self):
        bia, categoria = self.ids['bia'], self.category_id
        negadas = [
            ('GET', '/users', {}),
            ('GET', f'/users/{bia}', {}),
            ('GET', f'/users/{bia}/tasks', {}),
            ('PUT', f'/users/{bia}', {'json': {'name': 'Hack'}}),
            ('DELETE', f'/users/{bia}', {}),
            ('PUT', f'/tasks/{self.task_id}', {'json': {'title': 'Hack'}}),
            ('DELETE', f'/tasks/{self.task_id}', {}),
            ('POST', '/tasks', {'json': {'title': 'Para Bia', 'user_id': bia}}),
            ('POST', '/categories', {'json': {'name': 'Hack'}}),
            ('PUT', f'/categories/{categoria}', {'json': {'name': 'Hack'}}),
            ('DELETE', f'/categories/{categoria}', {}),
            ('GET', '/reports/summary', {}),
            ('GET', f'/reports/user/{bia}', {}),
        ]
        for method, url, kwargs in negadas:
            with self.subTest(method=method, url=url):
                self.assertEqual(self._status(method, url, 'ana', **kwargs), 403)

    def test_dono_nao_transfere_task_para_outro(self):
        resposta = self._status('PUT', f'/tasks/{self.task_id}', 'bia', json={'user_id': self.ids['ana']})
        self.assertEqual(resposta, 403)

    def test_dono_acessa_o_proprio_recurso(self):
        bia = self.ids['bia']
        self.assertEqual(self._status('GET', f'/users/{bia}', 'bia'), 200)
        self.assertEqual(self._status('GET', f'/reports/user/{bia}', 'bia'), 200)
        self.assertEqual(self._status('PUT', f'/tasks/{self.task_id}', 'bia', json={'status': 'done'}), 200)

    def test_gerente_administra_tasks_e_categorias_mas_nao_usuarios(self):
        self.assertEqual(self._status('PUT', f'/tasks/{self.task_id}', 'gerente', json={'user_id': self.ids['ana']}), 200)
        self.assertEqual(self._status('POST', '/categories', 'gerente', json={'name': 'Nova'}), 201)
        self.assertEqual(self._status('DELETE', f"/users/{self.ids['ana']}", 'gerente'), 403)

    def test_cadastro_publico_nao_cria_conta_privilegiada(self):
        dados = {'name': 'X', 'email': 'x@x.com', 'password': SENHA}
        self.assertEqual(self.client.post('/users', json={**dados, 'role': 'admin'}).status_code, 403)
        self.assertEqual(self.client.post('/users', json={**dados, 'role': 'manager'}).status_code, 403)
        criado = self.client.post('/users', json=dados)
        self.assertEqual(criado.status_code, 201)
        self.assertEqual(criado.get_json()['role'], 'user')

    def test_usuario_comum_nao_se_promove(self):
        self.assertEqual(self._status('PUT', f"/users/{self.ids['ana']}", 'ana', json={'role': 'admin'}), 403)


class SeedESegredosTest(ApiTestCase):
    def _rodar(self, codigo, **ambiente):
        return subprocess.run(
            [sys.executable, '-c', codigo], cwd=RAIZ, env={**os.environ, **ambiente}, capture_output=True, text=True
        )

    def test_aplicacao_nao_inicia_sem_segredo_real(self):
        for valor in ('', 'troque-por-uma-chave-secreta'):
            with self.subTest(valor=valor):
                resultado = self._rodar('import app', SECRET_KEY=valor)
                self.assertNotEqual(resultado.returncode, 0)
                self.assertIn('SECRET_KEY', resultado.stderr)

    def test_env_example_nao_abre_a_aplicacao(self):
        exemplo = (RAIZ / '.env.example').read_text(encoding='utf-8')
        linha = next(item for item in exemplo.splitlines() if item.startswith('SECRET_KEY='))
        self.assertTrue(linha.split('=', 1)[1].startswith('troque-por-'))

    def test_seed_nao_tem_senha_conhecida_nem_admin(self):
        seed.seed_data()
        with app.app_context():
            self.assertEqual(User.query.filter_by(role='admin').count(), 0)
        credenciais = (('joao@email.com', '1234'), ('maria@email.com', 'abcd'), ('pedro@email.com', 'pass'))
        for email, senha in credenciais:
            with self.subTest(email=email):
                self.assertEqual(self.client.post('/login', json={'email': email, 'password': senha}).status_code, 401)

    def test_create_admin_falha_sem_variaveis_e_cria_com_elas(self):
        runner = app.test_cli_runner()
        self.assertNotEqual(runner.invoke(args=['create-admin']).exit_code, 0)

        app.config.update(ADMIN_EMAIL='root@x.com', ADMIN_PASSWORD=SENHA)
        self.addCleanup(app.config.update, ADMIN_EMAIL='', ADMIN_PASSWORD='')
        self.assertEqual(runner.invoke(args=['create-admin']).exit_code, 0)
        self.assertNotEqual(runner.invoke(args=['create-admin']).exit_code, 0)

        login = self.client.post('/login', json={'email': 'root@x.com', 'password': SENHA})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.get_json()['user']['role'], 'admin')


if __name__ == '__main__':
    unittest.main()
