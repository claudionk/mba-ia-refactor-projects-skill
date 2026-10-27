# Referência: Guidelines de Arquitetura MVC

Este arquivo define o padrão MVC alvo para a **Fase 3**. Use estas regras para determinar a estrutura de diretórios e as responsabilidades de cada camada após a refatoração.

---

## Princípio Fundamental

O padrão MVC divide a aplicação em três camadas com responsabilidades exclusivas:

| Camada     | Responsabilidade única                                                         |
|------------|--------------------------------------------------------------------------------|
| Model      | Representar dados e abstrair o acesso ao banco (queries, ORM, validação básica)|
| Controller | Orquestrar a lógica de negócio — recebe dados do Model, aplica regras, retorna resultado |
| View/Route | Lidar com HTTP — receber request, chamar Controller, retornar response          |

Uma camada **nunca** deve assumir responsabilidade de outra.

---

## Estrutura de Diretórios Alvo

### Python / Flask

```
projeto/
├── app.py                   ← Entry point: cria app, registra blueprints, inicia servidor
├── config/
│   └── settings.py          ← Lê variáveis de ambiente; NUNCA valores hardcoded
├── models/
│   ├── __init__.py
│   └── [entidade]_model.py  ← Um arquivo por entidade de domínio
├── controllers/
│   ├── __init__.py
│   └── [entidade]_controller.py  ← Um arquivo por domínio
├── routes/                  ← (também chamado de "views/" em Flask)
│   ├── __init__.py
│   └── [entidade]_routes.py ← Blueprints Flask; um por domínio
├── middlewares/
│   └── error_handler.py     ← Handlers de erro HTTP globais
├── services/                ← (opcional) Lógica de negócio complexa ou integrações externas
│   └── [nome]_service.py
└── requirements.txt
```

### Node.js / Express

```
projeto/
├── src/
│   ├── app.js               ← Entry point: cria Express app, registra routers, inicia servidor
│   ├── config/
│   │   └── settings.js      ← Lê process.env; NUNCA valores hardcoded
│   ├── models/
│   │   └── [entidade]Model.js  ← Acesso a dados por entidade
│   ├── controllers/
│   │   └── [entidade]Controller.js  ← Lógica de negócio por domínio
│   ├── routes/
│   │   └── [entidade]Routes.js  ← Express Router por domínio
│   ├── middlewares/
│   │   └── errorHandler.js  ← Middleware de erro global
│   └── services/            ← (opcional) Integrações externas
│       └── [nome]Service.js
└── package.json
```

---

## Responsabilidades por Camada

### Config (`config/settings.py` ou `config/settings.js`)

**DEVE:**
- Ler toda configuração de variáveis de ambiente (`os.environ`, `process.env`)
- Definir valores padrão seguros para desenvolvimento
- Exportar um objeto/dict com todas as configurações centralizadas

**NUNCA DEVE:**
- Conter valores de produção hardcoded (senhas, chaves de API, tokens)
- Fazer conexão com banco de dados
- Importar outros módulos da aplicação

```python
# Python — settings.py correto
import os

class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-key-change-in-prod")
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
```

```js
// Node.js — settings.js correto
module.exports = {
    port: process.env.PORT || 3000,
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY,
    dbPath: process.env.DB_PATH || ':memory:',
};
```

---

### Model (`models/`)

**DEVE:**
- Representar uma entidade de domínio (Produto, Usuário, Task, Course)
- Conter as queries ou métodos ORM para CRUD dessa entidade
- Usar queries parametrizadas (NUNCA concatenação de strings)
- Retornar dados estruturados (dict, objeto) — não objetos HTTP

**NUNCA DEVE:**
- Conter lógica de negócio complexa (cálculos, regras de desconto, decisões de fluxo)
- Importar `request`, `jsonify` ou qualquer objeto HTTP
- Fazer chamadas para outros models diretamente em cadeias longas
- Retornar respostas HTTP

```python
# Python — model correto
class ProdutoModel:
    @staticmethod
    def get_by_id(db, produto_id: int) -> dict | None:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def create(db, nome: str, preco: float, estoque: int, categoria: str) -> int:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO produtos (nome, preco, estoque, categoria) VALUES (?, ?, ?, ?)",
            (nome, preco, estoque, categoria)
        )
        db.commit()
        return cursor.lastrowid
```

---

### Controller (`controllers/`)

**DEVE:**
- Receber dados já validados da camada de Routes
- Aplicar as regras de negócio (cálculos, decisões, orquestração de models)
- Chamar um ou mais models para ler/escrever dados
- Retornar um resultado (dict, objeto) — não uma resposta HTTP diretamente

**NUNCA DEVE:**
- Conter queries SQL diretamente
- Importar `request` do framework (recebe dados como parâmetros)
- Fazer parsing de `request.json` ou `req.body`

```python
# Python — controller correto
from models.produto_model import ProdutoModel
from database import get_db

class ProdutoController:
    @staticmethod
    def criar_produto(nome: str, descricao: str, preco: float, estoque: int, categoria: str) -> dict:
        if preco < 0:
            raise ValueError("Preço não pode ser negativo")
        if estoque < 0:
            raise ValueError("Estoque não pode ser negativo")
        db = get_db()
        produto_id = ProdutoModel.create(db, nome, descricao, preco, estoque, categoria)
        return {"id": produto_id, "mensagem": "Produto criado com sucesso"}
```

---

### Routes / Views (`routes/`)

**DEVE:**
- Definir as URLs e métodos HTTP aceitos
- Fazer parsing e validação básica do `request` (campos obrigatórios, tipos)
- Chamar o Controller com os dados extraídos
- Serializar a resposta do Controller para JSON e retornar com o status HTTP correto

**NUNCA DEVE:**
- Conter lógica de negócio
- Fazer queries SQL
- Conter mais de ~15 linhas por handler (sinal de que lógica de negócio vazou)

```python
# Python/Flask — route correto
from flask import Blueprint, request, jsonify
from controllers.produto_controller import ProdutoController

produto_bp = Blueprint('produtos', __name__)

@produto_bp.route('/produtos', methods=['POST'])
def criar_produto():
    dados = request.get_json()
    if not dados or 'nome' not in dados:
        return jsonify({"erro": "Nome é obrigatório"}), 400
    try:
        resultado = ProdutoController.criar_produto(
            nome=dados['nome'],
            descricao=dados.get('descricao', ''),
            preco=dados['preco'],
            estoque=dados['estoque'],
            categoria=dados.get('categoria', 'geral')
        )
        return jsonify({"dados": resultado, "sucesso": True}), 201
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
```

---

### Middleware / Error Handler (`middlewares/`)

**DEVE:**
- Capturar exceções não tratadas e retornar respostas HTTP padronizadas
- Ser registrado no entry point (`app.py` / `app.js`) para toda a aplicação
- Logar erros com nível e contexto adequados

```python
# Python/Flask — error_handler.py correto
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return {"erro": "Recurso não encontrado"}, 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Erro interno: {e}", exc_info=True)
        return {"erro": "Erro interno do servidor"}, 500

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        logger.error(f"Exceção não tratada: {e}", exc_info=True)
        return {"erro": "Erro inesperado"}, 500
```

---

### Entry Point (`app.py` / `app.js`)

**DEVE:**
- Criar a instância da aplicação
- Carregar configurações do módulo `config/`
- Registrar blueprints/routers
- Registrar middlewares de erro
- Inicializar o banco de dados (em app context, se aplicável)
- Iniciar o servidor

**NUNCA DEVE:**
- Conter lógica de negócio ou queries SQL
- Definir handlers de rota (exceto `/health` e `/` básicos, se conveniente)
- Ter mais de ~40 linhas

---

## Regras Transversais

1. **Sem hardcoded secrets** em qualquer camada — sempre via `config/`
2. **Sem SQL por concatenação** em nenhum arquivo — sempre queries parametrizadas
3. **Um arquivo por entidade de domínio** em models e controllers
4. **Error handling centralizado** — use o middleware, não `try/except` espalhado em todos os handlers
5. **Logging estruturado** — use `logging` (Python) ou logger (Node.js), nunca `print()`/`console.log()` em produção
