# Referência: Playbook de Refatoração

Este arquivo contém os padrões concretos de transformação para cada anti-pattern detectado na Fase 2. Para cada finding, encontre o padrão correspondente e aplique a transformação indicada.

---

## PB-01 · SQL Injection → Queries Parametrizadas

**Anti-pattern:** AP-01  
**Aplica-se a:** Python (sqlite3, psycopg2, pymysql), Node.js (sqlite3, pg)

### Python — sqlite3 raw

**Antes (vulnerável):**
```python
def get_produto_por_id(id):
    cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))

def login_usuario(email, senha):
    cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")

def buscar_produtos(termo, categoria):
    query = "SELECT * FROM produtos WHERE 1=1"
    if termo:
        query += " AND nome LIKE '%" + termo + "%'"
    cursor.execute(query)
```

**Depois (seguro):**
```python
def get_produto_por_id(produto_id: int):
    cursor.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))

def login_usuario(email: str, senha_hash: str):
    cursor.execute(
        "SELECT * FROM usuarios WHERE email = ? AND senha = ?",
        (email, senha_hash)
    )

def buscar_produtos(termo: str, categoria: str | None):
    query = "SELECT * FROM produtos WHERE 1=1"
    params = []
    if termo:
        query += " AND nome LIKE ?"
        params.append(f"%{termo}%")
    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)
    cursor.execute(query, params)
```

### Node.js — sqlite3

**Antes (vulnerável):**
```js
db.get("SELECT * FROM courses WHERE id = " + cid, (err, course) => { ... });
```

**Depois (seguro):**
```js
db.get("SELECT * FROM courses WHERE id = ? AND active = 1", [cid], (err, course) => { ... });
```

---

## PB-02 · Hardcoded Secrets → Variáveis de Ambiente

**Anti-pattern:** AP-02  
**Aplica-se a:** Python/Flask, Node.js/Express

### Python

**Antes:**
```python
# app.py
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
```

**Depois:**

1. Criar `config/settings.py`:
```python
import os

class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///app.db")
```

2. Atualizar `app.py`:
```python
from config.settings import Settings

app = Flask(__name__)
app.config["SECRET_KEY"] = Settings.SECRET_KEY
app.config["DEBUG"] = Settings.DEBUG
```

3. Criar `.env.example` (nunca commitar `.env` real):
```
SECRET_KEY=troque-por-uma-chave-segura-em-producao
DEBUG=false
DATABASE_URL=sqlite:///app.db
```

### Node.js

**Antes:**
```js
// utils.js
const config = {
    paymentGatewayKey: "pk_live_1234567890abcdef",
    dbPass: "senha_super_secreta_prod_123"
};
```

**Depois:**

1. Criar `config/settings.js`:
```js
module.exports = {
    port: process.env.PORT || 3000,
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY,
    dbPath: process.env.DB_PATH || ':memory:',
};
```

2. Criar `.env.example`:
```
PORT=3000
PAYMENT_GATEWAY_KEY=pk_test_sua_chave_aqui
DB_PATH=./database.db
```

---

## PB-03 · God File → Separação em Camadas MVC

**Anti-pattern:** AP-05  
**Aplica-se a:** Qualquer arquivo com múltiplas responsabilidades

### Estratégia de decomposição

Para cada domínio identificado no God File (ex: Produto, Usuário, Pedido):

1. **Extrair dados para `models/[entidade]_model.py`** — apenas funções de acesso a banco
2. **Extrair lógica de negócio para `controllers/[entidade]_controller.py`** — apenas regras
3. **Criar `routes/[entidade]_routes.py`** — apenas handlers HTTP e Blueprint

**Antes (God File `models.py` com 4 domínios misturados):**
```python
# models.py — 314 linhas: produto, usuário, pedido, relatório tudo junto
def get_todos_produtos(): ...
def criar_produto(): ...
def login_usuario(): ...       # autenticação aqui?
def criar_pedido(): ...        # lógica de negócio aqui?
def relatorio_vendas(): ...    # cálculo de desconto aqui?
```

**Depois (separado por domínio):**
```
models/
├── produto_model.py     ← get_all(), get_by_id(), create(), update(), delete()
├── usuario_model.py     ← get_by_id(), get_by_email(), create()
└── pedido_model.py      ← get_by_id(), get_by_usuario(), create(), update_status()

controllers/
├── produto_controller.py    ← validação + chama produto_model
├── usuario_controller.py    ← hash de senha + chama usuario_model
└── pedido_controller.py     ← regras de negócio (estoque, total) + chama pedido_model
```

---

## PB-04 · Lógica de Negócio na Route → Extração para Controller

**Anti-pattern:** AP-06  
**Aplica-se a:** Route handlers com mais de ~20 linhas ou com acesso direto ao banco

**Antes (lógica de negócio na route):**
```python
@app.route('/pedidos', methods=['POST'])
def criar_pedido():
    dados = request.get_json()
    usuario_id = dados.get('usuario_id')
    itens = dados.get('itens', [])
    
    total = 0
    for item in itens:
        cursor.execute("SELECT * FROM produtos WHERE id = " + str(item['produto_id']))
        produto = cursor.fetchone()
        if produto['estoque'] < item['quantidade']:
            return jsonify({'erro': 'Estoque insuficiente'}), 400
        total += produto['preco'] * item['quantidade']
    
    cursor.execute("INSERT INTO pedidos ...")
    # ... mais 30 linhas
```

**Depois (route delgada + controller):**
```python
# routes/pedido_routes.py — apenas HTTP
@pedido_bp.route('/pedidos', methods=['POST'])
def criar_pedido():
    dados = request.get_json()
    if not dados or 'usuario_id' not in dados:
        return jsonify({'erro': 'usuario_id é obrigatório'}), 400
    try:
        resultado = PedidoController.criar_pedido(
            usuario_id=dados['usuario_id'],
            itens=dados.get('itens', [])
        )
        return jsonify({'dados': resultado, 'sucesso': True}), 201
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

# controllers/pedido_controller.py — apenas negócio
class PedidoController:
    @staticmethod
    def criar_pedido(usuario_id: int, itens: list) -> dict:
        if not itens:
            raise ValueError("Pedido deve ter pelo menos 1 item")
        db = get_db()
        total = 0
        for item in itens:
            produto = ProdutoModel.get_by_id(db, item['produto_id'])
            if not produto:
                raise ValueError(f"Produto {item['produto_id']} não encontrado")
            if produto['estoque'] < item['quantidade']:
                raise ValueError(f"Estoque insuficiente para {produto['nome']}")
            total += produto['preco'] * item['quantidade']
        pedido_id = PedidoModel.create(db, usuario_id, itens, total)
        return {'pedido_id': pedido_id, 'total': total}
```

---

## PB-05 · God Class (Node.js) → Decomposição em MVC

**Anti-pattern:** AP-05 (variante Node.js)  
**Aplica-se a:** Classe única com DB + rotas + lógica de negócio

**Antes (`AppManager.js` com tudo):**
```js
class AppManager {
    constructor() { this.db = new sqlite3.Database(':memory:'); }
    initDb() { /* cria tabelas */ }
    setupRoutes(app) {
        app.post('/api/checkout', (req, res) => {
            // 50 linhas de lógica de negócio aqui
        });
    }
}
```

**Depois (decomposição):**

```js
// models/userModel.js
const getByEmail = (db, email) => new Promise((resolve, reject) => {
    db.get("SELECT id FROM users WHERE email = ?", [email], (err, row) => {
        if (err) reject(err); else resolve(row);
    });
});

// controllers/checkoutController.js
const checkout = async (db, { username, email, password, courseId, card }) => {
    const course = await CourseModel.getById(db, courseId);
    if (!course) throw new Error('Curso não encontrado');
    
    let user = await UserModel.getByEmail(db, email);
    if (!user) {
        const hash = await CryptoService.hashPassword(password);
        user = await UserModel.create(db, { name: username, email, hash });
    }
    
    const status = PaymentService.processCard(card);
    if (status === 'DENIED') throw new Error('Pagamento recusado');
    
    const enrollment = await EnrollmentModel.create(db, user.id, courseId);
    await PaymentModel.create(db, enrollment.id, course.price, status);
    return { enrollment_id: enrollment.id };
};

// routes/checkoutRoutes.js
router.post('/api/checkout', async (req, res, next) => {
    try {
        const { usr: username, eml: email, pwd: password, c_id: courseId, card } = req.body;
        if (!username || !email || !courseId || !card) {
            return res.status(400).json({ error: 'Campos obrigatórios ausentes' });
        }
        const result = await CheckoutController.checkout(db, { username, email, password, courseId, card });
        res.status(200).json({ msg: 'Sucesso', ...result });
    } catch (err) {
        next(err);
    }
});
```

---

## PB-06 · Senha em Texto Puro → Hash com bcrypt

**Anti-pattern:** AP-04  
**Aplica-se a:** Python e Node.js

### Python

**Antes:**
```python
def criar_usuario(nome, email, senha):
    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
        (nome, email, senha)  # senha em texto puro!
    )
```

**Depois:**
```python
import bcrypt

def criar_usuario(nome: str, email: str, senha: str) -> int:
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
        (nome, email, senha_hash.decode('utf-8'))
    )
    db.commit()
    return cursor.lastrowid

def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))
```

Adicionar ao `requirements.txt`: `bcrypt>=4.0.0`

### Node.js

**Antes (`badCrypto`):**
```js
function badCrypto(pwd) {
    let hash = "";
    for(let i = 0; i < 10000; i++) {
        hash += Buffer.from(pwd).toString('base64').substring(0, 2);
    }
    return hash.substring(0, 10);
}
```

**Depois:**
```js
// services/cryptoService.js
const bcrypt = require('bcrypt');
const SALT_ROUNDS = 12;

const hashPassword = async (password) => bcrypt.hash(password, SALT_ROUNDS);
const verifyPassword = async (password, hash) => bcrypt.compare(password, hash);

module.exports = { hashPassword, verifyPassword };
```

Adicionar ao `package.json`: `"bcrypt": "^5.1.0"`

---

## PB-07 · N+1 Query → JOIN ou Eager Loading

**Anti-pattern:** AP-09  
**Aplica-se a:** Python (sqlite3 raw), Node.js (sqlite3)

### Python — substituir loop de queries por JOIN

**Antes (N+1):**
```python
def get_pedidos_usuario(usuario_id):
    cursor.execute("SELECT * FROM pedidos WHERE usuario_id = ?", (usuario_id,))
    pedidos = cursor.fetchall()
    for pedido in pedidos:
        cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = ?", (pedido['id'],))
        itens = cursor2.fetchall()
        for item in itens:
            cursor3.execute("SELECT nome FROM produtos WHERE id = ?", (item['produto_id'],))
            # 1 + N + N*M queries!
```

**Depois (JOIN único):**
```python
def get_pedidos_usuario(usuario_id: int) -> list:
    cursor.execute("""
        SELECT
            p.id, p.status, p.total, p.criado_em,
            ip.produto_id, ip.quantidade, ip.preco_unitario,
            pr.nome AS produto_nome
        FROM pedidos p
        LEFT JOIN itens_pedido ip ON ip.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = ip.produto_id
        WHERE p.usuario_id = ?
        ORDER BY p.id
    """, (usuario_id,))
    rows = cursor.fetchall()
    # agrupa resultados por pedido_id
    pedidos = {}
    for row in rows:
        pid = row['id']
        if pid not in pedidos:
            pedidos[pid] = {'id': pid, 'status': row['status'], 'total': row['total'], 'itens': []}
        if row['produto_id']:
            pedidos[pid]['itens'].append({
                'produto_id': row['produto_id'],
                'produto_nome': row['produto_nome'],
                'quantidade': row['quantidade'],
                'preco_unitario': row['preco_unitario']
            })
    return list(pedidos.values())
```

---

## PB-08 · Deprecated SQLAlchemy API → Session.get()

**Anti-pattern:** DEP-01  
**Aplica-se a:** Python com Flask-SQLAlchemy

**Antes (depreciado no SQLAlchemy 2.0):**
```python
user = User.query.get(user_id)
task = Task.query.get(task_id)
category = Category.query.get(cat_id)
```

**Depois (SQLAlchemy 2.0+):**
```python
from database import db

user = db.session.get(User, user_id)
task = db.session.get(Task, task_id)
category = db.session.get(Category, cat_id)
```

> **Nota:** `db.session.get()` retorna `None` se não encontrado, exatamente igual ao comportamento anterior de `query.get()`. Nenhuma mudança de lógica necessária.

---

## PB-09 · Lógica Duplicada → Extração para Método ou Service

**Anti-pattern:** AP-07  
**Aplica-se a:** Qualquer linguagem

**Antes (lógica de `overdue` em 3 lugares):**
```python
# Em get_tasks():
if t.due_date and t.due_date < datetime.utcnow():
    if t.status != 'done' and t.status != 'cancelled':
        task_data['overdue'] = True

# Em get_task():
if task.due_date and task.due_date < datetime.utcnow():
    if task.status != 'done' and task.status != 'cancelled':
        data['overdue'] = True

# Em task_stats():
if t.due_date and t.due_date < datetime.utcnow():
    if t.status != 'done' and t.status != 'cancelled':
        overdue_count += 1
```

**Depois (encapsulado no Model):**
```python
# models/task.py — adicionar método ao Model
class Task(db.Model):
    # ... campos existentes ...

    def is_overdue(self) -> bool:
        """Retorna True se a task está atrasada e não está concluída/cancelada."""
        if not self.due_date:
            return False
        active_statuses = {'pending', 'in_progress'}
        return self.due_date < datetime.utcnow() and self.status in active_statuses

# Uso em routes/controllers — um único ponto:
task_data['overdue'] = task.is_overdue()
```

---

## PB-10 · Bare Except → Tratamento de Exceção Tipado com Logging

**Anti-pattern:** AP-12  
**Aplica-se a:** Python

**Antes:**
```python
try:
    db.session.commit()
except:
    return jsonify({'error': 'Erro interno'}), 500
```

**Depois:**
```python
import logging

logger = logging.getLogger(__name__)

try:
    db.session.commit()
    return jsonify(task.to_dict()), 201
except Exception as e:
    db.session.rollback()
    logger.error(f"Erro ao salvar task: {e}", exc_info=True)
    return jsonify({'error': 'Erro ao salvar. Tente novamente.'}), 500
```

---

## PB-11 · Print → Logger Estruturado

**Anti-pattern:** AP-13  
**Aplica-se a:** Python e Node.js

### Python

**Antes:**
```python
print("Task criada: " + str(task.id))
print("ERRO: " + str(e))
```

**Depois:**
```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"Task criada: id={task.id}, title={task.title!r}")
logger.error(f"Erro ao criar task: {e}", exc_info=True)
```

Configurar no entry point (`app.py`):
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
```

### Node.js

**Antes:**
```js
console.log(`Processando cartão ${cc}`)  // NUNCA logar dados de cartão!
console.log('Frankenstein LMS rodando...')
```

**Depois:**
```js
// Usar winston ou pino, ou no mínimo:
const logger = {
    info: (msg) => console.log(`[${new Date().toISOString()}] INFO: ${msg}`),
    error: (msg, err) => console.error(`[${new Date().toISOString()}] ERROR: ${msg}`, err || ''),
};

logger.info(`Servidor iniciado na porta ${config.port}`);
// NUNCA logar número de cartão, senha ou dados sensíveis
```
