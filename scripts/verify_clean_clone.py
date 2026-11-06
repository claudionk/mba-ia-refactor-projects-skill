#!/usr/bin/env python3
"""Valida o repositório como um avaliador: clone limpo, instalação do zero e os comandos do README.

Uso:
    python scripts/verify_clean_clone.py                 # clona o HEAD deste repositório
    python scripts/verify_clean_clone.py --source <url>  # clona um remoto

Requer Python 3 com pip, Node.js e npm. Só escreve em uma pasta temporária, removida no final.
"""
import argparse
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import venv
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WINDOWS = os.name == "nt"
falhas = []


def verifica(rotulo, condicao, detalhe=""):
    print(f"  [{'PASS' if condicao else 'FAIL'}] {rotulo}{f' ({detalhe})' if detalhe else ''}", flush=True)
    if not condicao:
        falhas.append(rotulo)


def executa(comando, cwd, env=None):
    return subprocess.run(
        comando, cwd=cwd, env={**os.environ, **(env or {})},
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def porta_livre():
    with socket.socket() as sonda:
        sonda.bind(("127.0.0.1", 0))
        return sonda.getsockname()[1]


def http(metodo, url, corpo=None, cabecalhos=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    pedido = urllib.request.Request(url, data=dados, method=metodo, headers={"Content-Type": "application/json", **(cabecalhos or {})})
    try:
        with urllib.request.urlopen(pedido, timeout=10) as resposta:
            return resposta.status, resposta.read().decode()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.read().decode()


class Servidor:
    """Sobe o processo e o encerra com os filhos: no Windows, o Python do venv é um lançador."""

    def __init__(self, comando, cwd, base, sonda):
        self.processo = subprocess.Popen(comando, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.base, self.sonda = base, sonda

    def __enter__(self):
        for _ in range(60):
            try:
                http("GET", self.base + self.sonda)
                return self
            except OSError:
                time.sleep(0.25)
        raise RuntimeError(f"Servidor não respondeu em {self.base}")

    def __exit__(self, *_):
        if WINDOWS:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.processo.pid)], capture_output=True)
        else:
            self.processo.terminate()
        self.processo.wait()


def cria_venv(destino, projeto):
    venv.create(destino, with_pip=False)
    python = destino / ("Scripts/python.exe" if WINDOWS else "bin/python")
    instalado = executa([sys.executable, "-m", "pip", "--python", str(python), "install", "-q", "-r", "requirements.txt"], projeto)
    verifica("pip install -r requirements.txt", instalado.returncode == 0, instalado.stderr.strip()[-200:] if instalado.returncode else "")
    return python


def escreve_env(projeto, **valores):
    """Faz `cp .env.example .env` e troca só o que o README manda definir."""
    linhas = []
    for linha in (projeto / ".env.example").read_text(encoding="utf-8").splitlines():
        chave = linha.split("=", 1)[0]
        linhas.append(f"{chave}={valores[chave]}" if chave in valores and not linha.startswith("#") else linha)
    (projeto / ".env").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def testes(comando, projeto):
    resultado = executa(comando, projeto)
    resumo = [linha for linha in (resultado.stdout + resultado.stderr).splitlines() if linha.startswith(("Ran ", "ℹ tests", "ℹ fail"))]
    resumo = [linha.replace("ℹ ", "") for linha in resumo]
    verifica(Path(comando[0]).stem + " " + " ".join(comando[1:]), resultado.returncode == 0, "; ".join(resumo))


def projeto_1(raiz, trabalho):
    print("\n== code-smells-project (Python/Flask)", flush=True)
    projeto = raiz / "code-smells-project"
    python = cria_venv(trabalho / "v1", projeto)
    testes([str(python), "-m", "unittest", "discover", "-s", "tests", "-t", "."], projeto)

    porta = porta_livre()
    escreve_env(projeto, PORT=porta)
    placeholder = executa([str(python), "-c", "import app"], projeto)
    verifica("com o .env.example sem editar, a aplicação recusa iniciar e explica", placeholder.returncode != 0 and "SECRET_KEY" in placeholder.stderr)

    token_admin, senha_admin = secrets.token_hex(16), secrets.token_urlsafe(16)
    escreve_env(projeto, PORT=porta, SECRET_KEY=secrets.token_hex(32), ADMIN_TOKEN=token_admin, ADMIN_EMAIL="admin@exemplo.com", ADMIN_PASSWORD=senha_admin)
    admin = executa([str(python), "-m", "flask", "--app", "app", "criar-admin"], projeto)
    verifica("flask --app app criar-admin", admin.returncode == 0, admin.stdout.strip())

    base = f"http://127.0.0.1:{porta}"
    with Servidor([str(python), "app.py"], projeto, base, "/health"):
        verifica("GET /health", http("GET", base + "/health")[0] == 200)
        verifica("GET /produtos", http("GET", base + "/produtos")[0] == 200)
        verifica("GET /usuarios sem token -> 401", http("GET", base + "/usuarios")[0] == 401)
        verifica("GET /usuarios com X-Admin-Token -> 200", http("GET", base + "/usuarios", cabecalhos={"X-Admin-Token": token_admin})[0] == 200)
        verifica("login com a senha antiga do seed -> 401", http("POST", base + "/login", {"email": "admin@loja.com", "senha": "admin123"})[0] == 401)
        _, corpo = http("POST", base + "/login", {"email": "admin@exemplo.com", "senha": senha_admin})
        verifica("login do admin criado devolve token", "token" in json.loads(corpo))

        criado = json.loads(http("POST", base + "/usuarios", {"nome": "Ana", "email": "ana@x.com", "senha": "senha-da-ana"})[1])["dados"]["id"]
        token = json.loads(http("POST", base + "/login", {"email": "ana@x.com", "senha": "senha-da-ana"})[1])["token"]
        bearer = {"Authorization": f"Bearer {token}"}
        pedido = {"usuario_id": criado, "itens": [{"produto_id": 1, "quantidade": 1}]}
        verifica("POST /pedidos sem login -> 401", http("POST", base + "/pedidos", pedido)[0] == 401)
        verifica("POST /pedidos do próprio cliente -> 201", http("POST", base + "/pedidos", pedido, bearer)[0] == 201)
        verifica("GET /pedidos/usuario/<outro> -> 403", http("GET", f"{base}/pedidos/usuario/{criado + 999}", cabecalhos=bearer)[0] == 403)


def projeto_2(raiz):
    print("\n== ecommerce-api-legacy (Node.js/Express)", flush=True)
    projeto = raiz / "ecommerce-api-legacy"
    npm = shutil.which("npm")
    instalado = executa([npm, "ci", "--silent"], projeto)
    verifica("npm ci", instalado.returncode == 0, instalado.stderr.strip()[-200:] if instalado.returncode else "")
    testes([npm, "test"], projeto)

    porta = porta_livre()
    base = f"http://127.0.0.1:{porta}"
    placeholder = "troque-por-um-token-admin-forte"
    escreve_env(projeto, PORT=porta)
    with Servidor(["node", "src/app.js"], projeto, base, "/"):
        verifica("com o .env.example sem editar, o placeholder não abre o relatório -> 403",
                 http("GET", base + "/api/admin/financial-report", cabecalhos={"x-admin-token": placeholder})[0] == 403)

    token_admin = secrets.token_hex(16)
    escreve_env(projeto, PORT=porta, ADMIN_TOKEN=token_admin)
    with Servidor(["node", "src/app.js"], projeto, base, "/"):
        checkout = {"usr": "Gui", "eml": "gui@x.com", "pwd": "senhaforte", "c_id": 2, "card": "4111222233334444"}
        verifica("POST /api/checkout -> 200", http("POST", base + "/api/checkout", checkout)[0] == 200)
        verifica("checkout com card numérico -> 400", http("POST", base + "/api/checkout", {**checkout, "card": 123})[0] == 400)
        verifica("relatório sem token -> 401", http("GET", base + "/api/admin/financial-report")[0] == 401)
        verifica("relatório com token -> 200", http("GET", base + "/api/admin/financial-report", cabecalhos={"x-admin-token": token_admin})[0] == 200)


def projeto_3(raiz, trabalho):
    print("\n== task-manager-api (Python/Flask + SQLAlchemy)", flush=True)
    projeto = raiz / "task-manager-api"
    python = cria_venv(trabalho / "v3", projeto)
    testes([str(python), "-m", "unittest", "discover", "-s", "tests", "-t", "."], projeto)

    porta = porta_livre()
    escreve_env(projeto, PORT=porta)
    placeholder = executa([str(python), "-c", "import app"], projeto)
    verifica("com o .env.example sem editar, a aplicação recusa iniciar e explica", placeholder.returncode != 0 and "SECRET_KEY" in placeholder.stderr)

    senha_admin = secrets.token_urlsafe(16)
    escreve_env(projeto, PORT=porta, SECRET_KEY=secrets.token_hex(32), ADMIN_EMAIL="admin@exemplo.com", ADMIN_PASSWORD=senha_admin)
    verifica("python seed.py", executa([str(python), "seed.py"], projeto, {"PYTHONIOENCODING": "utf-8"}).returncode == 0)
    admin = executa([str(python), "-m", "flask", "--app", "app", "create-admin"], projeto)
    verifica("flask --app app create-admin", admin.returncode == 0, admin.stdout.strip())

    base = f"http://127.0.0.1:{porta}"
    with Servidor([str(python), "app.py"], projeto, base, "/health"):
        verifica("GET /health", http("GET", base + "/health")[0] == 200)
        verifica("GET /tasks sem token -> 401", http("GET", base + "/tasks")[0] == 401)
        verifica("login com a senha antiga do seed -> 401", http("POST", base + "/login", {"email": "joao@email.com", "password": "1234"})[0] == 401)
        token = json.loads(http("POST", base + "/login", {"email": "admin@exemplo.com", "password": senha_admin})[1])["token"]
        bearer = {"Authorization": f"Bearer {token}"}
        status, corpo = http("GET", base + "/tasks", cabecalhos=bearer)
        verifica("GET /tasks do admin traz as 10 tasks do seed", status == 200 and len(json.loads(corpo)) == 10)
        verifica("GET /tasks/stats -> 200", http("GET", base + "/tasks/stats", cabecalhos=bearer)[0] == 200)
        verifica("GET /reports/summary -> 200", http("GET", base + "/reports/summary", cabecalhos=bearer)[0] == 200)

        http("POST", base + "/users", {"name": "Comum", "email": "comum@x.com", "password": "senha-comum"})
        comum = json.loads(http("POST", base + "/login", {"email": "comum@x.com", "password": "senha-comum"})[1])["token"]
        cabecalho = {"Authorization": f"Bearer {comum}"}
        verifica("usuário comum apagando task de outro -> 403", http("DELETE", base + "/tasks/1", cabecalhos=cabecalho)[0] == 403)
        verifica("usuário comum apagando categoria -> 403", http("DELETE", base + "/categories/1", cabecalhos=cabecalho)[0] == 403)
        verifica("usuário comum lendo /users -> 403", http("GET", base + "/users", cabecalhos=cabecalho)[0] == 403)
        verifica("cadastro anônimo com role admin -> 403",
                 http("POST", base + "/users", {"name": "X", "email": "x@x.com", "password": "senha-x", "role": "admin"})[0] == 403)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # console do Windows pode não ser UTF-8
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--source", default=str(REPO), help="repositório a clonar (padrão: este)")
    origem = argumentos.parse_args().source

    trabalho = Path(tempfile.mkdtemp(prefix="verify-"))
    try:
        raiz = trabalho / "repo"
        clone = executa(["git", "clone", "-q", origem, str(raiz)], trabalho)
        if clone.returncode != 0:
            sys.exit(f"git clone falhou: {clone.stderr}")
        commit = executa(["git", "log", "-1", "--format=%h %s"], raiz).stdout.strip()
        print(f"Clone limpo de {origem}\nCommit: {commit}", flush=True)
        projeto_1(raiz, trabalho)
        projeto_2(raiz)
        projeto_3(raiz, trabalho)
    finally:
        shutil.rmtree(trabalho, ignore_errors=True)

    print(f"\n{'TUDO OK' if not falhas else f'{len(falhas)} FALHA(S): ' + '; '.join(falhas)}", flush=True)
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
