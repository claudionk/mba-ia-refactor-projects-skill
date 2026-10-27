# Referência: Análise de Projeto

Este arquivo contém as heurísticas usadas na **Fase 1** para detectar stack, framework, banco de dados e mapear a arquitetura atual de qualquer projeto.

---

## 1. Detecção de Linguagem e Framework

### Identificar pelo manifesto de dependências

| Arquivo encontrado       | Linguagem    | Próximo passo                                  |
|--------------------------|-------------|------------------------------------------------|
| `requirements.txt`       | Python       | Leia o arquivo para identificar o framework    |
| `pyproject.toml`         | Python       | Leia `[tool.poetry.dependencies]`              |
| `package.json`           | Node.js      | Leia `"dependencies"` para o framework         |
| `Gemfile`                | Ruby         | Procure `gem 'rails'` ou `gem 'sinatra'`       |
| `go.mod`                 | Go           | Procure `github.com/gin-gonic` ou `echo`       |
| `pom.xml`                | Java/Kotlin  | Procure `spring-boot` nos `<dependencies>`     |
| `build.gradle`           | Java/Kotlin  | Procure `org.springframework.boot`             |
| `Cargo.toml`             | Rust         | Procure `actix-web` ou `axum`                  |

### Mapeamento de dependência → framework

**Python:**
- `flask` → Flask
- `django` → Django
- `fastapi` → FastAPI
- `tornado` → Tornado

**Node.js:**
- `express` → Express
- `fastify` → Fastify
- `@nestjs/core` → NestJS
- `koa` → Koa

**Ruby:**
- `rails` → Ruby on Rails
- `sinatra` → Sinatra

### Detectar versão

- Python: `python_requires` no `pyproject.toml` ou `runtime.txt` ou `.python-version`
- Node.js: campo `"engines"` no `package.json` ou `.nvmrc`
- Se não encontrar versão explícita, registre como "versão não especificada"

---

## 2. Detecção de Banco de Dados

### Por dependência declarada

| Dependência                   | Banco                      | Modo de acesso    |
|-------------------------------|---------------------------|-------------------|
| `sqlite3` (Python)            | SQLite                     | SQL raw           |
| `flask-sqlalchemy`            | Configurável via URI       | ORM (SQLAlchemy)  |
| `sqlalchemy`                  | Configurável via URI       | ORM (SQLAlchemy)  |
| `psycopg2`, `psycopg2-binary` | PostgreSQL                 | SQL raw           |
| `pymysql`, `mysql-connector`  | MySQL                      | SQL raw           |
| `pymongo`                     | MongoDB                    | ODM               |
| `sqlite3` (Node.js)           | SQLite                     | SQL raw (callback)|
| `sequelize`                   | Configurável via dialect   | ORM               |
| `mongoose`                    | MongoDB                    | ODM               |
| `pg`                          | PostgreSQL                 | SQL raw           |
| `typeorm`                     | Configurável               | ORM               |
| `prisma`                      | Configurável               | ORM               |

### Por string de conexão no código

Procure padrões como:
```python
# Python
sqlite:///nome.db          → SQLite
postgresql://user:pass@... → PostgreSQL
mysql://user:pass@...      → MySQL
```
```js
// Node.js
':memory:'                 → SQLite in-memory
'./database.db'            → SQLite file
```

### Por tabelas no código

Se encontrar `cursor.execute("CREATE TABLE ...")` ou `class Model(db.Model)` ou `db.define(...)`, liste os nomes das tabelas para mapear o domínio.

---

## 3. Mapeamento de Arquitetura Atual

### Perguntas para fazer ao ler o código

1. **Existe separação em diretórios?** (`models/`, `controllers/`, `routes/`, `views/`, `services/`)
2. **O arquivo principal (`app.py`, `app.js`, `index.js`) contém lógica de negócio?**
3. **As queries SQL estão dentro de route handlers ou em arquivos separados?**
4. **Existe um arquivo que faz tudo** (rotas + banco + lógica)?

### Classificação de arquitetura

| Padrão detectado                                                             | Classificação                                              |
|------------------------------------------------------------------------------|------------------------------------------------------------|
| Tudo em 1-2 arquivos, sem separação                                          | Monolítica sem camadas                                     |
| Existe separação superficial (ex: `models.py` + `controllers.py`) mas tudo misturado | Semi-estruturada / Pseudo-MVC                    |
| Diretórios `models/`, `routes/` existem mas lógica de negócio está nas routes | Parcialmente organizada — falta camada Controller      |
| Models, Controllers e Routes em diretórios separados com responsabilidades claras | MVC estruturado                                      |

### Heurísticas de contagem de arquivos

- **Inclua:** `.py`, `.js`, `.ts`, `.rb`, `.go`, `.java`, `.kt`
- **Exclua:** `node_modules/`, `venv/`, `.venv/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `*.pyc`, `*.min.js`
- **Conte separadamente:** arquivos de teste (pasta `test/`, `tests/`, `spec/`), arquivos de config (`*.json`, `*.yaml`, `*.toml`, `*.env`)

---

## 4. Identificação do Domínio

### Sinais para inferir o domínio da aplicação

1. **Nomes de tabelas:** `usuarios`, `pedidos`, `produtos` → E-commerce; `tasks`, `categories` → Task Manager; `courses`, `enrollments` → LMS
2. **Nomes de rotas:** `/api/checkout` → fluxo de compra; `/tasks` → gerenciamento de tarefas; `/cursos` → plataforma de cursos
3. **Nomes de models/entidades:** seguem a mesma lógica dos nomes de tabelas

### Template de descrição de domínio

> "[Tipo de aplicação] para [operações principais] de [entidades principais]"

Exemplos:
- "E-commerce API para gestão de produtos, usuários e pedidos"
- "LMS API com fluxo de checkout, matrículas e pagamentos"
- "Task Manager API para criação, atribuição e acompanhamento de tarefas"
