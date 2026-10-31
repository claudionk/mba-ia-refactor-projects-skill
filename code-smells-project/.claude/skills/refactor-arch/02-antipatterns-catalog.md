# Referência: Catálogo de Anti-Patterns

Este arquivo contém os anti-patterns que a skill detecta na **Fase 2**. Para cada finding, registre o nome exato do anti-pattern, a severidade, o arquivo e as linhas.

---

## Escala de Severidade

| Nível    | Critério                                                                                               |
|----------|--------------------------------------------------------------------------------------------------------|
| CRITICAL | Falha grave de segurança ou arquitetura que impede funcionamento correto ou expõe dados sensíveis      |
| HIGH     | Forte violação de MVC ou SOLID que dificulta muito manutenção e testes                                 |
| MEDIUM   | Problema de padronização, duplicação ou performance moderada                                           |
| LOW      | Melhoria de legibilidade, nomenclatura ou estilo                                                       |

---

## Anti-Patterns — Segurança (CRITICAL)

### AP-01 · SQL Injection
**Severidade:** CRITICAL  
**Sinais de detecção:**
- String SQL construída por concatenação: `"SELECT * WHERE id = " + str(id)`
- f-string com variável em query: `f"SELECT * WHERE email = '{email}'"`
- Template string em query JS: `` `SELECT * WHERE id = ${id}` ``
- `cursor.execute("... WHERE campo = '" + variavel + "'")`

**Verificar em:** Todos os arquivos com acesso a banco de dados.

**Exemplo suspeito:**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "'")
```

---

### AP-02 · Hardcoded Credentials / Secrets
**Severidade:** CRITICAL  
**Sinais de detecção:**
- `SECRET_KEY = "..."` com valor literal
- `PASSWORD = "..."`, `API_KEY = "..."`, `TOKEN = "..."` com valor literal
- Chaves com padrões como `pk_live_`, `sk_live_`, `bearer_`, seguidas de valor
- Senha de banco hardcoded em string de conexão: `"postgresql://admin:senha123@..."`

**Verificar em:** `app.py`, `app.js`, `config.py`, `settings.py`, `utils.js`, qualquer arquivo de inicialização.

---

### AP-03 · Endpoint de Execução Arbitrária de SQL
**Severidade:** CRITICAL  
**Sinais de detecção:**
- Rota que aceita parâmetro `sql` ou `query` via body/query string e o executa diretamente
- `cursor.execute(request.json.get("sql"))`
- Endpoint `/admin/query`, `/run-query`, `/execute` que chama `db.query(userInput)`

---

### AP-04 · Senha em Texto Puro / Hash Inseguro
**Severidade:** CRITICAL  
**Sinais de detecção:**
- Senha armazenada diretamente: `INSERT INTO users (pass) VALUES (?)` passando senha sem hash
- Hash inseguro: MD5, SHA1, base64 usado como "hash" de senha
- Pseudo-algoritmo de hash (loop + base64 + substring)
- Retorno de senha no payload da API: `"senha": row["senha"]` em GET

---

### AP-17 · Endpoint Sensível sem Autenticação / Autenticação Fail-Open
**Severidade:** HIGH (CRITICAL se o endpoint apaga dados em massa ou executa comandos)  
**Sinais de detecção:**
- Rota administrativa, financeira ou destrutiva (`/admin/*`, `DELETE`, relatórios com dados pessoais ou receita) sem middleware/decorator de autenticação
- Middleware de autenticação **fail-open**: libera a requisição quando a credencial esperada não está configurada
  - Node.js: `if (!settings.adminToken) return next();`
  - Python: `if not token_esperado: return view(*args, **kwargs)`
- `.env.example` com a variável de credencial vazia (`ADMIN_TOKEN=`), o que faz o projeto subir com a proteção desligada
- Comparação de token com `===` / `==` em vez de comparação em tempo constante
- Autorização baseada em campo enviado pelo cliente (`role: 'admin'` no body)

**Verificar em:** `middlewares/`, `routes/`, decorators de rota, `.env.example`, `config/settings`.

**Regra:** um middleware que só protege "quando configurado" **não corrige** este anti-pattern; ele continua aberto na configuração padrão e deve ser reportado como finding.

---

## Anti-Patterns — Arquitetura (HIGH)

### AP-05 · God Class / God File
**Severidade:** HIGH  
**Sinais de detecção:**
- Arquivo único com mais de 3 responsabilidades distintas: inicialização de banco + rotas + lógica de negócio + validação
- Classe com mais de ~200 linhas que faz operações de DB, HTTP e negócio
- Módulo `models.py` com funções de lógica de negócio embutidas (ex: cálculo de desconto dentro de uma função de relatório)

---

### AP-06 · Lógica de Negócio em Route Handler
**Severidade:** HIGH  
**Sinais de detecção:**
- Route handler com mais de ~30 linhas de código
- Acesso direto ao banco dentro de um handler de rota (sem passar por controller/service)
- Cálculos de negócio (descontos, totais, validações complexas) dentro de `@app.route` ou `app.get(...)`
- Múltiplas queries SQL dentro de um mesmo handler de rota

---

### AP-07 · Lógica de Negócio Duplicada (DRY Violation)
**Severidade:** HIGH  
**Sinais de detecção:**
- Mesmo bloco de código (mais de 4 linhas idênticas) aparece em 2+ funções/métodos
- Mesma regra de negócio implementada separadamente em vários lugares (ex: cálculo de `overdue` em 3 funções diferentes)
- Validações idênticas repetidas em create e update sem extração para função auxiliar

---

### AP-08 · Debug Mode em Produção / Informações Sensíveis no Response
**Severidade:** HIGH  
**Sinais de detecção:**
- `app.config["DEBUG"] = True` hardcoded
- `debug=True` passado diretamente no `app.run()`
- Endpoint de health check retornando `SECRET_KEY`, `db_path`, credenciais ou informações internas
- Stack traces expostos diretamente na resposta HTTP

---

## Anti-Patterns — Qualidade (MEDIUM)

### AP-09 · N+1 Query Problem
**Severidade:** MEDIUM  
**Sinais de detecção:**
- Query executada dentro de loop `for`: `for item in items: cursor.execute("SELECT...")`
- Cursor aninhado dentro de outro cursor dentro de loop
- Múltiplos `db.get()` ou `Model.query.get()` dentro de um `forEach` ou `for`

---

### AP-10 · Estado Global Mutável
**Severidade:** MEDIUM  
**Sinais de detecção:**
- Variáveis mutáveis no escopo de módulo que são lidas/escritas por funções: `let cache = {}`
- Dicionário/objeto de cache global sem lock ou controle de concorrência
- Contador global incrementado em handlers de requisição

---

### AP-11 · Ausência de Validação de Entrada
**Severidade:** MEDIUM  
**Sinais de detecção:**
- Route handler que usa `request.json.get("campo")` sem verificar se o campo existe e tem tipo/formato correto
- Dados de usuário usados diretamente sem sanitização
- Ausência de validação de formato (email, data, enum de status)

---

### AP-12 · Bare Except / Swallowed Exceptions
**Severidade:** MEDIUM  
**Sinais de detecção:**
- `except:` sem tipo de exceção
- `except Exception:` ou `except Exception as e:` sem logar `e`
- `catch(err) {}` vazio em JavaScript
- Erros capturados mas não propagados nem logados

---

## Anti-Patterns — Qualidade de Código (LOW)

### AP-13 · Print / Console.log para Logging
**Severidade:** LOW  
**Sinais de detecção:**
- `print(...)` em código de produção (não em scripts utilitários)
- `console.log(...)` em handlers de rota ou lógica de negócio
- Ausência de uso de `logging` (Python) ou logger estruturado (Node.js)

---

### AP-14 · Magic Numbers / Magic Strings
**Severidade:** LOW  
**Sinais de detecção:**
- Números literais em condicionais sem constante nomeada: `if faturamento > 10000`
- Strings de status literais espalhadas: `if status == "aprovado"` em múltiplos lugares sem enum/constante
- Percentuais hardcoded: `* 0.1`, `* 0.05`

---

### AP-15 · Nomes de Variáveis Sem Semântica
**Severidade:** LOW  
**Sinais de detecção:**
- Variáveis de uma letra sem contexto claro: `u`, `e`, `p`, `c`, `d`
- Abreviações ambíguas em campos de API: `usr`, `eml`, `pwd`, `cid`
- Nomes genéricos: `data`, `result`, `item` em contexto onde o tipo é específico

---

### AP-16 · Imports Não Utilizados
**Severidade:** LOW  
**Sinais de detecção:**
- `import os, sys, json, time` quando nenhum desses módulos é referenciado no arquivo
- `const { algo } = require('./utils')` onde `algo` nunca é usado
- Imports listados em bloco sem verificar se todos são usados

---

## Deprecated APIs

### DEP-01 · SQLAlchemy — Model.query.get() depreciado
**Severidade:** HIGH  
**Contexto:** SQLAlchemy 2.0 depreciou `Model.query.get(id)`. O método foi removido no SQLAlchemy 2.1.  
**Sinal de detecção:** `Model.query.get(...)` em qualquer arquivo Python com SQLAlchemy.  
**Substituição correta:** `db.session.get(Model, id)`

```python
# Deprecated:
user = User.query.get(user_id)

# Correto (SQLAlchemy 2.0+):
user = db.session.get(User, user_id)
```

---

### DEP-02 · Node.js — crypto.createCipher() depreciado
**Severidade:** HIGH  
**Contexto:** `crypto.createCipher()` foi removido no Node.js 22. Não usa IV, tornando a criptografia insegura.  
**Sinal de detecção:** `require('crypto').createCipher(...)` em qualquer arquivo JS.  
**Substituição correta:** `crypto.createCipheriv(algorithm, key, iv)`

---

### DEP-03 · Flask — before_first_request depreciado
**Severidade:** MEDIUM  
**Contexto:** O decorator `@app.before_first_request` foi removido no Flask 2.3.  
**Sinal de detecção:** `@app.before_first_request` em qualquer arquivo Python Flask.  
**Substituição correta:** Usar `with app.app_context(): ...` no entry point.

---

### DEP-04 · Express — res.json() com status separado (padrão antigo)
**Severidade:** LOW  
**Contexto:** O padrão `res.status(200).json({...})` é correto, mas `res.send(statusCode, body)` (2 argumentos) foi depreciado no Express 4.  
**Sinal de detecção:** `res.send(200, dados)` ou `res.json(200, dados)`.  
**Substituição correta:** `res.status(200).json(dados)`

