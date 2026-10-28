# Solução de Criação de Skills — Refatoração Arquitetural Automatizada

---

## Análise Manual

### Projeto 1 — `code-smells-project` (Python/Flask — E-commerce API)

| Severidade | Anti-Pattern | Arquivo | Linha(s) |
|---|---|---|---|
| CRITICAL | SQL Injection generalizado — todas as queries construídas por concatenação | `models.py` | 28, 48–50, 58–61, 68, 92, 109–111, 127–129, 140, 155, 164–165, 174, 188, 192, 280–281, 291–293 |
| CRITICAL | Endpoint de execução arbitrária de SQL sem autenticação | `app.py` | 59–78 |
| CRITICAL | `SECRET_KEY` hardcoded em código-fonte | `app.py` | 7 |
| CRITICAL | `SECRET_KEY` exposta no response do health check | `controllers.py` | 289 |
| HIGH | God File — `models.py` concentra 4 domínios + lógica de negócio + acesso a banco | `models.py` | 1–314 |
| HIGH | Debug mode hardcoded | `app.py` | 8 |
| HIGH | Senhas armazenadas e retornadas em texto puro | `models.py` | 75–87, 122–131 |
| MEDIUM | N+1 Queries em pedidos (3 cursores aninhados em loop) | `models.py` | 171–200, 203–233 |
| MEDIUM | Lógica de negócio (cálculo de desconto) dentro de função de modelo | `models.py` | 256–263 |
| LOW | `print()` para logging em toda a camada de controllers | `controllers.py` | 8, 11, 57, 61, 106, 161, 179, 182, 208–210, 219 |
| LOW | Magic numbers no cálculo de desconto (10000, 5000, 1000, 0.1, 0.05, 0.02) | `models.py` | 257–263 |
| LOW | Endpoint `/admin/reset-db` sem proteção alguma deleta todos os dados | `app.py` | 47–57 |

**Por que esses problemas são relevantes:** O SQL Injection em todas as queries torna a aplicação completamente vulnerável — qualquer usuário pode extrair ou destruir todos os dados. A `SECRET_KEY` exposta permite forjar sessões. O God File torna impossível testar qualquer domínio isoladamente.


#### Resultado da execução da Skill

```markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask
Files:   4 analyzed | ~780 lines of code
Date:    2026-10-27

## Summary

CRITICAL: 6 | HIGH: 5 | MEDIUM: 5 | LOW: 4
Total findings: 20

Deprecated APIs: nenhuma ocorrência de DEP-01 a DEP-04 (Flask 3.1.1 e `sqlite3` da stdlib).

## Findings

### [CRITICAL] SQL Injection no login (bypass de autenticação)
File: models.py:105-111
Anti-pattern: AP-01 — SQL Injection
Description: `login_usuario` concatena `email` e `senha` direto na query:
  "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
Enviando `email = ' OR 1=1 --`, a query vira `WHERE email = '' OR 1=1 --...` e o trecho da senha é comentado. O `fetchone()` dev
olve o primeiro usuário, que é o Admin (id 1, tipo admin). Achado por análise estática; payload não executado.
Impact: Login como administrador via `POST /login` sem conhecer a senha.
Recommendation: `cursor.execute("SELECT id, nome, email, tipo, senha FROM usuarios WHERE email = ?", (email,))` e comparar o has
h com `check_password_hash` (ver C5).

---

### [CRITICAL] SQL Injection na busca pública de produtos (vazamento de tabelas)
File: models.py:289-297; controllers.py:113-123
Anti-pattern: AP-01 — SQL Injection
Description: `termo` (query string `q`) e `categoria` são concatenados em `nome LIKE '%" + termo + "%'` e `categoria = '...'`. `
GET /produtos/busca` não exige autenticação.
Impact: Leitura de qualquer tabela via `UNION SELECT`, incluindo `usuarios.senha`. Exemplo de `q` (sintaxe conferida por análise
): `x%') UNION SELECT id,nome,email,senha,tipo,criado_em,NULL,NULL FROM usuarios --`. Os dados saem no campo `dados` da resposta
.
Recommendation: `query += " AND (nome LIKE ? OR descricao LIKE ?)"` com parâmetros `(f"%{termo}%", f"%{termo}%")`; mesma correçã
o para `categoria`, `preco_min` e `preco_max`.

---

### [CRITICAL] SQL Injection nas operações de escrita
File: models.py:47-50, 58-60, 126-129, 148-151, 157-160, 164-166, 280
Anti-pattern: AP-01 — SQL Injection
Description: Campos de texto livre são concatenados em INSERT/UPDATE:
  - `criar_produto` (nome, descricao, categoria)
  - `atualizar_produto` (nome, descricao, categoria; a categoria nem é validada no controller)
  - `criar_usuario` (nome, email, senha)
  - `criar_pedido` (usuario_id, produto_id, quantidade, sem cast para inteiro)
  - `atualizar_status_pedido` (novo_status, protegido pela whitelist do controller)
Impact: Escrita arbitrária no banco e exfiltração por subconsulta. Exemplo: `nome = "x'||(SELECT group_concat(senha) FROM usuari
os)||'"` grava as senhas no nome do produto, que sai em `GET /produtos`. O `sqlite3` recusa múltiplos statements, o que limita D
ROP/DELETE encadeado, mas não subconsultas.
Recommendation: Usar placeholders `?` em todas as chamadas `execute`; converter IDs com `int()` ou validar tipo no controller an
tes de chegar ao model.

---

### [CRITICAL] Endpoints administrativos sem autenticação: SQL arbitrário e reset total
File: app.py:47-57, 59-78
Anti-pattern: AP-03 — Endpoint de Execução Arbitrária de SQL
Description: `POST /admin/query` executa o campo `sql` do body diretamente com `cursor.execute`. `POST /admin/reset-db` executa
`DELETE` em todas as tabelas. Nenhum dos dois verifica autenticação.
Impact: Qualquer cliente pode apagar o banco inteiro, executar UPDATE/DELETE arbitrários e ler senhas com `SELECT ... FROM usuar
ios`.
Recommendation: Remover `/admin/query` do código de produção. Se necessário, substituir por comando CLI (`flask ...`) executado
localmente. Proteger ou remover `/admin/reset-db`.

---

### [CRITICAL] Senhas em texto puro, armazenadas e devolvidas pela API
File: models.py:79-86, 95-102, 110, 126-129; database.py:76-78
Anti-pattern: AP-04 — Senha em Texto Puro / Retorno de senha no payload
Description: `criar_usuario` grava `senha` sem hash (models.py:126-129). `get_todos_usuarios` (79-86) e `get_usuario_por_id` (95
-102) incluem `"senha": row["senha"]` no retorno, então `GET /usuarios` e `GET /usuarios/<id>` expõem todas as senhas. O login c
ompara a senha em claro na SQL (110). O seed cria senhas fracas: `admin123`, `123456`, `senha123` (database.py:76-78).
Impact: Qualquer cliente anônimo lista todas as senhas. O vazamento do arquivo `loja.db` expõe todas as credenciais em claro.
Recommendation: Gerar hash com `werkzeug.security.generate_password_hash` (Werkzeug já vem com Flask) em `criar_usuario`; valida
r com `check_password_hash` no login; remover `senha` de todos os dicts de retorno; redefinir as senhas do seed.

---

### [CRITICAL] Secrets e credenciais hardcoded, incluindo exposição no /health
File: app.py:7; database.py:76; controllers.py:289
Anti-pattern: AP-02 — Hardcoded Credentials / Secrets
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` é literal (app.py:7) e é devolvida em claro por `GET /
health` (controllers.py:289). A conta `admin@loja.com` / `admin123` é criada automaticamente no seed (database.py:76).
Impact: Qualquer visitante obtém a SECRET_KEY e pode forjar cookies de sessão assinados. A credencial de admin está pública no r
epositório.
Recommendation: `app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]` (falhar na inicialização se ausente); remover `secret_key`
 do `/health`; criar o admin por comando de setup com senha vinda de variável de ambiente, não do seed.

---

### [HIGH] God File: models.py concentra SQL, regra de negócio e serialização
File: models.py:1-314 (destaques: 133-169, 256-262)
Anti-pattern: AP-05 — God Class / God File
Description: `models.py` tem 314 linhas e 18 funções. Além de acesso a dados, contém: cálculo de total e checagem de estoque em
`criar_pedido` (133-169); regra de desconto por faixas de faturamento em `relatorio_vendas` (256-262, com limites 10000/5000/100
0 e percentuais 0.1/0.05/0.02); composição do relatório e ticket médio.
Impact: Alterar uma regra de desconto exige mexer no módulo de persistência. Não é possível testar a regra sem SQLite. As camada
s ficam acopladas.
Recommendation: Mover cálculo de total, validação de estoque e desconto para a camada de regra de negócio; `models` fica só com
queries. Detalhes na Fase 3, conforme `04-mvc-guidelines.md`.

---

### [HIGH] Controllers misturam validação, acesso direto ao banco e resposta HTTP
File: controllers.py:24-62, 64-96, 188-220, 264-292
Anti-pattern: AP-06 — Lógica de Negócio em Route Handler
Description: `health_check` (264-292) executa 4 queries SQL direto via `get_db()`, sem passar pelo model. `criar_pedido` (188-22
0) orquestra validação, persistência e notificações. As linhas 208-210 imprimem "ENVIANDO EMAIL / SMS / PUSH", mas nada é enviad
o. Regras de domínio (categorias válidas em 52, preço e estoque em 43-46) ficam dentro do handler.
Impact: A regra não pode ser testada sem subir o Flask. O health check fica acoplado ao schema. O log sugere notificações que nã
o existem.
Recommendation: `health_check` chama `models.contar_registros()`; validação em módulo próprio; notificações atrás de uma interfa
ce explícita, ou removidas até existirem de verdade.

---

### [HIGH] Duplicação (DRY): serialização, validação e montagem de pedidos
File: models.py:10-21, 31-40, 304-313; models.py:79-86, 95-102; models.py:178-199, 211-231; controllers.py:26-46, 66-90
Anti-pattern: AP-07 — Lógica de Negócio Duplicada
Description: O dict de produto (8 campos) aparece 3 vezes. O dict de usuário aparece 2 vezes. O bloco "monta pedido + itens + no
me do produto" é quase idêntico em `get_pedidos_usuario` (178-199) e `get_todos_pedidos` (211-231), cerca de 20 linhas. A valida
ção de nome, preço e estoque está duplicada entre `criar_produto` (26-46) e `atualizar_produto` (66-90), e as duas divergem: a c
ategoria só é validada na criação.
Impact: Uma correção em um lugar não chega aos outros. A divergência já causa um bug: `PUT /produtos/<id>` aceita categoria invá
lida.
Recommendation: Extrair `_produto_to_dict(row)`, `_usuario_to_dict(row)` e `_montar_pedido(...)` no model; `validar_produto(dado
s)` compartilhado entre criar e atualizar.

---

### [HIGH] Debug ativo e vazamento de informações internas
File: app.py:8, 78, 88; controllers.py:12, 22, 62, 96, 109, 126, 134, 144, 165, 186, 220, 227, 235, 255, 262, 284-292
Anti-pattern: AP-08 — Debug Mode em Produção / Informações Sensíveis no Response
Description: `app.config["DEBUG"] = True` (app.py:8) e `app.run(host="0.0.0.0", debug=True)` (app.py:88), que expõe o console in
terativo do Werkzeug na rede. O `/health` devolve `"ambiente": "producao"` junto com `"debug": True`, `"db_path"` e `secret_key`
 (controllers.py:284-289). Há 17 respostas 500 que devolvem `str(e)` (16 em controllers.py e 1 em app.py:78), o que expõe mensag
ens internas do SQLite e do Python.
Impact: Estrutura do banco e do código vazada a qualquer cliente. Quem obtiver o PIN do debugger do Werkzeug ganha execução de c
ódigo no servidor.
Recommendation: `DEBUG` lido de variável de ambiente, com padrão `False`; `host="127.0.0.1"` em desenvolvimento; respostas 500 g
enéricas com `logger.exception` no servidor; remover campos internos do `/health`.

---

### [HIGH] Ausência de autenticação e autorização (fora do catálogo)
File: app.py:11-26
Anti-pattern: Não catalogado. Extensão de AP-03 e AP-08, anotado aqui.
Description: Nenhuma rota exige token ou sessão. `PUT /produtos/<id>`, `DELETE /produtos/<id>`, `PUT /pedidos/<id>/status` e `PO
ST /usuarios` são públicos. Qualquer cliente altera preço, apaga produto ou cancela pedido de terceiros. O campo `tipo` do usuár
io não é usado em nenhuma checagem de permissão.
Impact: Qualquer visitante anônimo executa operações administrativas.
Recommendation: Autenticação por token ou sessão e decorator de autorização (`@requer_admin`) nas rotas de escrita; `tipo` verif
icado no servidor.

---

### [MEDIUM] N+1 Query Problem
File: models.py:177-200, 209-232, 154-156
Anti-pattern: AP-09 — N+1 Query Problem
Description: `get_pedidos_usuario` e `get_todos_pedidos` executam 1 query por pedido (188, 220) e 1 query por item (191-193, 223
-225). Com P pedidos e I itens no total, são 1 + P + I queries. Em `criar_pedido`, o preço de cada produto é consultado duas vez
es (140-141 e 155-156).
Impact: `GET /pedidos` degrada linearmente. Com 100 pedidos de 3 itens cada, são 401 queries em uma requisição.
Recommendation: Um `JOIN` entre `itens_pedido` e `produtos` em uma query, agrupando em Python. Reutilizar o produto carregado no
 loop de validação de `criar_pedido`.

---

### [MEDIUM] Estado global mutável: conexão única compartilhada entre requests
File: database.py:4-11, 86; models.py:134-169
Anti-pattern: AP-10 — Estado Global Mutável
Description: `db_connection` é global. Uma única conexão SQLite com `check_same_thread=False` é usada por todas as threads do Fl
ask. A inicialização é lazy e sem lock. `criar_pedido` faz vários INSERT/UPDATE e só commita no fim, sem rollback no erro. Como
a conexão é compartilhada, escritas pendentes de uma request são persistidas pelo próximo `commit()` de outra. A checagem de est
oque (144) e o UPDATE (164) são separados, sem transação nem lock.
Impact: Pedido parcial gravado por outra request. Overselling sob concorrência, já que dois pedidos podem passar na checagem ant
es de qualquer um atualizar o estoque.
Recommendation: Conexão por request (com `g` do Flask ou abrir e fechar por operação); `BEGIN IMMEDIATE` em `criar_pedido`; `rol
lback()` no `except`.

---

### [MEDIUM] Quantidade zero ou negativa aceita em pedidos
File: controllers.py:195-201; models.py:143-166
Anti-pattern: AP-11 — Ausência de Validação de Entrada
Description: `criar_pedido` valida só a presença de `itens` e `usuario_id`. `quantidade` não é validada. Com `quantidade = -100`
, a checagem `produto["estoque"] < item["quantidade"]` (144) passa, `total` fica negativo (146) e `estoque - (-100)` aumenta o e
stoque (164-166).
Impact: Um cliente cria pedido com quantidade negativa, aumenta o estoque sem limite e gera total negativo, distorcendo `relator
io_vendas` (faturamento, desconto e líquido).
Recommendation: Validar `quantidade` como inteiro maior que zero, e `produto_id` como inteiro, antes da persistência.

---

### [MEDIUM] Validação de tipos e de corpo da requisição ausente
File: controllers.py:169-171, 239-240, 113-121, 26-46, 66-90, 153-158
Anti-pattern: AP-11 — Ausência de Validação de Entrada
Description:
  - `login` (169-171) e `atualizar_status_pedido` (239-240) chamam `dados.get(...)` sem checar `None`. Body ausente ou `null` ge
ra `AttributeError` e resposta 500.
  - Corpo JSON malformado também vira 500: o `except Exception` captura o `BadRequest` do Flask.
  - `preco` e `estoque` não são checados como numéricos. Com `"preco": "abc"`, `preco < 0` (43, 87) levanta `TypeError` e respos
ta 500.
  - `preco_min` e `preco_max` (118-121) são convertidos com `float()` sem tratamento. Valor inválido gera `ValueError` e respost
a 500.
  - `email` não tem formato validado (154). `atualizar_produto` não valida categoria (85) nem tamanho de nome.
Impact: Erros 500 onde deveria haver 400. Combinado com H4, as mensagens internas vazam.
Recommendation: Validação centralizada de tipo, formato e obrigatoriedade (função de validação ou biblioteca de schema). Usar `r
equest.get_json(silent=True)` e responder 400 quando o body não for objeto JSON.

---

### [MEDIUM] Exceções capturadas sem log
File: controllers.py:21-22, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 226-227, 234-235, 254-255, 261-262; app
.py:77-78
Anti-pattern: AP-12 — Bare Except / Swallowed Exceptions
Description: 13 blocos `except Exception as e` retornam `str(e)` sem `print` nem logging. Outros blocos (`listar_produtos`, `cri
ar_produto`, `criar_pedido`) imprimem a mensagem, mas sem traceback. Falhas em `login` e `criar_usuario` não são registradas.
Impact: Falhas em produção sem rastro. Diagnosticar exige reproduzir o erro.
Recommendation: `logger.exception(...)` no `except` e resposta 500 genérica para o cliente.

---

### [LOW] print() usado como logging
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250; app.py:56, 83-86
Anti-pattern: AP-13 — Print / Console.log para Logging
Description: 19 chamadas `print`. Em 208-210, as mensagens "ENVIANDO EMAIL / SMS / PUSH" dizem que notificações foram enviadas,
mas são só prints. Os logs de login (179, 182) gravam o e-mail do usuário em claro.
Impact: Sem níveis e sem rotação. Logs enganosos. Dados pessoais nos logs.
Recommendation: Módulo `logging` com níveis. Substituir as simulações de notificação por uma interface real ou removê-las.

---

### [LOW] Magic numbers e strings
File: models.py:247-262; controllers.py:47-52, 242; database.py:5; app.py:88
Anti-pattern: AP-14 — Magic Numbers / Magic Strings
Description: Faixas de desconto (10000, 5000, 1000) e percentuais (0.1, 0.05, 0.02) inline em `relatorio_vendas`. Status de pedi
do literais em models.py:247-253 e em lista em controllers.py:242. Limites de nome (2 e 200) em 47 e 49. Lista de categorias em
52, sem constante compartilhada com o seed (database.py:59-69). Caminho `"loja.db"` e porta `5000` literais.
Recommendation: Constantes nomeadas (`FAIXAS_DESCONTO`, `STATUS_PEDIDO`, `CATEGORIAS_VALIDAS`, `DB_PATH`).

---

### [LOW] Nomes sem semântica e sombreamento de built-in
File: controllers.py:14, 56, 64, 98, 136, 160; models.py:24, 54, 65, 89, 187-193, 219-225
Anti-pattern: AP-15 — Nomes de Variáveis Sem Semântica
Description: `id` sombreia o built-in `id()` em 10 funções. `cursor2`, `cursor3`, `prod`, `rows`, `result` e `dados` são genéric
os demais.
Recommendation: `produto_id`, `usuario_id`, `cursor_itens`, `cursor_produto`, `itens_rows`.

---

### [LOW] Imports não utilizados
File: models.py:2; database.py:2
Anti-pattern: AP-16 — Imports Não Utilizados
Description: `import sqlite3` em `models.py` não é referenciado. `import os` em `database.py` também não.
Recommendation: Remover os dois imports.

---

## Observações fora do catálogo (não entram na contagem)

- **Cancelamento não devolve estoque:** `controllers.py:249-250` imprime "Devolver estoque", mas nenhum código faz isso.
- **Transição de status livre:** qualquer status pode ir para qualquer outro (`controllers.py:242-245`).
- **Usuário não verificado no pedido:** `criar_pedido` não confere se `usuario_id` existe (`controllers.py:198-199`).
- **Relatório inclui cancelados:** `relatorio_vendas` soma pedidos cancelados no faturamento (`models.py:242-243`) e no ticket m
## Observações fora do catálogo (não entram na contagem)

- **Cancelamento não devolve estoque:** `controllers.py:249-250` imprime "Devolver estoque", mas nenhum código faz isso.
- **Transição de status livre:** qualquer status pode ir para qualquer outro (`controllers.py:242-245`).
- **Usuário não verificado no pedido:** `criar_pedido` não confere se `usuario_id` existe (`controllers.py:198-199`).
- **Relatório inclui cancelados:** `relatorio_vendas` soma pedidos cancelados no faturamento (`models.py:242-243`) e no ticket m
édio (`models.py:272`).
- **CORS aberto:** `CORS(app)` (`app.py:9`) libera qualquer origem.
- **Versão de Python não declarada:** `requirements.txt` lista só `flask` e `flask-cors`. O `__pycache__` indica CPython 3.14.

================================
Total: 20 findings
CRITICAL: 6 | HIGH: 5 | MEDIUM: 5 | LOW: 4
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]

---

================================
PHASE 1: PROJECT ANALYSIS

Language:      Python (versão não declarada; __pycache__ indica CPython 3.14)
Framework:     Flask 3.1.1
Dependencies:  flask==3.1.1, flask-cors==5.0.1, sqlite3 (stdlib)
Domain:        API de e-commerce para gestão de produtos, usuários, pedidos e relatório de vendas
Architecture:  Semi-estruturada / Pseudo-MVC. app.py mistura rotas, endpoints admin e config. controllers.py mistura HTTP, validação e regra de negócio. models.py mistura SQL e regra de negócio. database.py faz conexão, schema e seed. Não há diretórios por camada.
Source files:  4 files analyzed (~780 linhas)
DB:            SQLite (loja.db), SQL raw com concatenação de strings, sem ORM e sem migrations. Schema criado por CREATE TABLE IF NOT EXISTS em get_db().

================================
ARCHITECTURE AUDIT REPORT

Project: code-smells-project
Stack:   Python + Flask
Files:   4 analyzed | ~780 lines of code
Date:    2026-10-27

Summary

CRITICAL: 6 | HIGH: 5 | MEDIUM: 5 | LOW: 4
Total findings: 20

Deprecated APIs: nenhuma ocorrência de DEP-01 a DEP-04 (Flask 3.1.1 e sqlite3 da stdlib).

Findings

[CRITICAL] SQL Injection no login (bypass de autenticação)

File: models.py:105-111
Anti-pattern: AP-01 — SQL Injection
Description: login_usuario concatena email e senha direto na query. Enviando email = ' OR 1=1 --, a query vira WHERE email = '' OR 1=1 --... e o trecho da senha é comentado. O fetchone() devolve o primeiro usuário, que é o Admin (id 1, tipo admin). Achado por análise estática; payload não executado.
Impact: Login como administrador via POST /login sem conhecer a senha.
Recommendation: SELECT ... FROM usuarios WHERE email = ? com parâmetros, e comparar hash com check_password_hash (ver C5).

[CRITICAL] SQL Injection na busca pública de produtos (vazamento de tabelas)

File: models.py:289-297; controllers.py:113-123
Anti-pattern: AP-01 — SQL Injection
Description: termo (query string q) e categoria são concatenados em nome LIKE '%" + termo + "%' e categoria = '...'. GET /produtos/busca não exige autenticação.
Impact: Leitura de qualquer tabela via UNION SELECT, incluindo usuarios.senha. Exemplo de q (sintaxe conferida por análise): x%') UNION SELECT id,nome,email,senha,tipo,criado_em,NULL,NULL FROM usuarios --. Os dados saem no campo dados.
Recommendation: " AND (nome LIKE ? OR descricao LIKE ?)" com parâmetros (f"%{termo}%", f"%{termo}%"); mesma correção para categoria, preco_min e preco_max.

[CRITICAL] SQL Injection nas operações de escrita

File: models.py:47-50, 58-60, 126-129, 148-151, 157-160, 164-166, 280
Anti-pattern: AP-01 — SQL Injection
Description: Campos de texto livre são concatenados em INSERT/UPDATE: criar_produto (nome, descricao, categoria), atualizar_produto (nome, descricao, categoria, sem validação de categoria), criar_usuario (nome, email, senha), criar_pedido (usuario_id, produto_id, quantidade, sem cast) e atualizar_status_pedido (protegido pela whitelist do controller).
Impact: Escrita arbitrária e exfiltração por subconsulta. Exemplo: nome = "x'||(SELECT group_concat(senha) FROM usuarios)||'" grava as senhas no nome do produto, que sai em GET /produtos. O sqlite3 recusa múltiplos statements, o que limita DROP encadeado, mas não subconsultas.
Recommendation: Placeholders ? em todos os execute; converter IDs com int() ou validar tipo no controller.

[CRITICAL] Endpoints administrativos sem autenticação: SQL arbitrário e reset total

File: app.py:47-57, 59-78
Anti-pattern: AP-03 — Endpoint de Execução Arbitrária de SQL
Description: POST /admin/query executa o campo sql do body diretamente. POST /admin/reset-db executa DELETE em todas as tabelas. Nenhum dos dois verifica autenticação.
Impact: Qualquer cliente apaga o banco inteiro, executa UPDATE/DELETE arbitrários e lê senhas com SELECT ... FROM usuarios.
Recommendation: Remover /admin/query do código de produção, substituindo por comando CLI local se necessário. Proteger ou remover /admin/reset-db.

[CRITICAL] Senhas em texto puro, armazenadas e devolvidas pela API

File: models.py:79-86, 95-102, 110, 126-129; database.py:76-78
Anti-pattern: AP-04 — Senha em Texto Puro / Retorno de senha no payload
Description: criar_usuario grava senha sem hash. get_todos_usuarios e get_usuario_por_id incluem "senha" no retorno, então GET /usuarios e GET /usuarios/<id> expõem todas as senhas. O login compara em claro. O seed cria senhas fracas: admin123, 123456, senha123.
Impact: Qualquer cliente anônimo lista todas as senhas. Vazamento do loja.db expõe todas as credenciais.
Recommendation: werkzeug.security.generate_password_hash em criar_usuario e check_password_hash no login. Remover senha de todos os retornos. Redefinir as senhas do seed.

[CRITICAL] Secrets e credenciais hardcoded, incluindo exposição no /health

File: app.py:7; database.py:76; controllers.py:289
Anti-pattern: AP-02 — Hardcoded Credentials / Secrets
Description: SECRET_KEY = "minha-chave-super-secreta-123" é literal (app.py:7) e é devolvida em claro por GET /health (controllers.py:289). A conta admin@loja.com / admin123 é criada no seed (database.py:76).
Impact: Qualquer visitante obtém a SECRET_KEY e pode forjar cookies de sessão. A credencial de admin está pública no repositório.
Recommendation: Ler SECRET_KEY de variável de ambiente, sem fallback literal. Remover secret_key do /health. Criar o admin por comando de setup, não pelo seed.

[HIGH] God File: models.py concentra SQL, regra de negócio e serialização

File: models.py:1-314 (destaques: 133-169, 256-262)
Anti-pattern: AP-05 — God Class / God File
Description: Além de acesso a dados, models.py contém o cálculo de total e a checagem de estoque em criar_pedido (133-169), a regra de desconto por faixas em relatorio_vendas (256-262, limites 10000/5000/1000 e percentuais 0.1/0.05/0.02) e a composição do relatório.
Impact: Alterar uma regra de desconto exige mexer no módulo de persistência. A regra não é testável sem SQLite.
Recommendation: Mover total, estoque e desconto para a camada de regra de negócio. models fica só com queries. Detalhes na Fase 3.

[HIGH] Controllers misturam validação, acesso direto ao banco e resposta HTTP

File: controllers.py:24-62, 64-96, 188-220, 264-292
Anti-pattern: AP-06 — Lógica de Negócio em Route Handler
Description: health_check (264-292) executa 4 queries SQL direto via get_db(). criar_pedido orquestra validação, persistência e notificações. As linhas 208-210 imprimem "ENVIANDO EMAIL / SMS / PUSH", mas nada é enviado. Regras de domínio (categorias em 52, preço e estoque em 43-46) ficam no handler.
Impact: Regra não testável sem subir o Flask. O health check fica acoplado ao schema. O log sugere notificações que não existem.
Recommendation: health_check chama models.contar_registros(). Validação em módulo próprio. Notificações atrás de interface explícita, ou removidas.

[HIGH] Duplicação (DRY): serialização, validação e montagem de pedidos

File: models.py:10-21, 31-40, 304-313; models.py:79-86, 95-102; models.py:178-199, 211-231; controllers.py:26-46, 66-90
Anti-pattern: AP-07 — Lógica de Negócio Duplicada
Description: O dict de produto (8 campos) aparece 3 vezes e o de usuário 2 vezes. O bloco "monta pedido + itens" é quase idêntico em get_pedidos_usuario e get_todos_pedidos, cerca de 20 linhas. A validação de produto está duplicada entre criar e atualizar, e as duas divergem: a categoria só é validada na criação.
Impact: Correção em um lugar não chega aos outros. A divergência já é um bug: PUT /produtos/<id> aceita categoria inválida.
Recommendation: _produto_to_dict(row), _usuario_to_dict(row), _montar_pedido(...) e validar_produto(dados) compartilhado.

[HIGH] Debug ativo e vazamento de informações internas

File: app.py:8, 78, 88; controllers.py:12, 22, 62, 96, 109, 126, 134, 144, 165, 186, 220, 227, 235, 255, 262, 284-292
Anti-pattern: AP-08 — Debug Mode em Produção / Informações Sensíveis no Response
Description: DEBUG = True (app.py:8) e app.run(host="0.0.0.0", debug=True) (app.py:88), que expõe o console do Werkzeug na rede. O /health devolve "ambiente": "producao" junto com "debug": True, "db_path" e secret_key. São 17 respostas 500 com str(e) (16 em controllers.py e 1 em app.py:78).
Impact: Estrutura do banco e do código vazada. Quem obtiver o PIN do debugger ganha execução de código no servidor.
Recommendation: DEBUG por variável de ambiente, padrão False. host="127.0.0.1" em desenvolvimento. Respostas 500 genéricas com logger.exception. Remover campos internos do /health.

[HIGH] Ausência de autenticação e autorização (fora do catálogo)

File: app.py:11-26
Anti-pattern: Não catalogado. Extensão de AP-03 e AP-08.
Description: Nenhuma rota exige token ou sessão. PUT /produtos/<id>, DELETE /produtos/<id>, PUT /pedidos/<id>/status e POST /usuarios são públicos. O campo tipo não é usado em nenhuma checagem de permissão.
Impact: Qualquer visitante anônimo executa operações administrativas.
Recommendation: Autenticação por token ou sessão e decorator @requer_admin nas rotas de escrita.

[MEDIUM] N+1 Query Problem

File: models.py:177-200, 209-232, 154-156
Anti-pattern: AP-09 — N+1 Query Problem
Description: get_pedidos_usuario e get_todos_pedidos executam 1 query por pedido e 1 por item. Com P pedidos e I itens, são 1 + P + I queries. Em criar_pedido, o preço de cada produto é consultado duas vezes (140-141 e 155-156).
Impact: GET /pedidos degrada linearmente. Com 100 pedidos de 3 itens, são 401 queries em uma requisição.
Recommendation: JOIN entre itens_pedido e produtos. Reutilizar o produto carregado em criar_pedido.

[MEDIUM] Estado global mutável: conexão única compartilhada entre requests

File: database.py:4-11, 86; models.py:134-169
Anti-pattern: AP-10 — Estado Global Mutável
Description: db_connection é global e uma única conexão com check_same_thread=False é usada por todas as threads. A inicialização é lazy e sem lock. criar_pedido faz vários writes e só commita no fim, sem rollback no erro. Escritas pendentes de uma request são persistidas pelo commit() de outra. A checagem de estoque (144) e o UPDATE (164) não são atômicos.
Impact: Pedido parcial gravado por outra request. Overselling sob concorrência.
Recommendation: Conexão por request. BEGIN IMMEDIATE em criar_pedido. rollback() no except.

[MEDIUM] Quantidade zero ou negativa aceita em pedidos

File: controllers.py:195-201; models.py:143-166
Anti-pattern: AP-11 — Ausência de Validação de Entrada
Description: quantidade não é validada. Com quantidade = -100, a checagem de estoque (144) passa, total fica negativo (146) e estoque - (-100) aumenta o estoque (164-166).
Impact: Estoque inflado sem limite e total negativo, distorcendo relatorio_vendas.
Recommendation: Validar quantidade como inteiro maior que zero e produto_id como inteiro antes da persistência.

[MEDIUM] Validação de tipos e de corpo da requisição ausente

File: controllers.py:169-171, 239-240, 113-121, 26-46, 66-90, 153-158
Anti-pattern: AP-11 — Ausência de Validação de Entrada
Description: login (169-171) e atualizar_status_pedido (239-240) chamam dados.get sem checar None. JSON malformado também vira 500, pois o except Exception captura o BadRequest do Flask. preco e estoque não são checados como numéricos ("abc" gera TypeError em 43). preco_min/preco_max com float() sem tratamento. Email sem formato validado.
Impact: Erros 500 onde deveria haver 400. Combinado com H4, as mensagens internas vazam.
Recommendation: Validação centralizada de tipo, formato e obrigatoriedade. request.get_json(silent=True) e 400 quando o body não for objeto JSON.

[MEDIUM] Exceções capturadas sem log

File: controllers.py:21-22, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 226-227, 234-235, 254-255, 261-262; app.py:77-78
Anti-pattern: AP-12 — Bare Except / Swallowed Exceptions
Description: 13 blocos except Exception as e retornam str(e) sem log. Falhas em login e criar_usuario não são registradas.
Impact: Falhas em produção sem rastro.
Recommendation: logger.exception(...) no except e resposta 500 genérica para o cliente.

[LOW] print() usado como logging

File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250; app.py:56, 83-86
Anti-pattern: AP-13 — Print / Console.log para Logging
Description: 19 chamadas print. Em 208-210, as mensagens "ENVIANDO EMAIL / SMS / PUSH" dizem que notificações foram enviadas, mas são só prints. Os logs de login (179, 182) gravam o e-mail em claro.
Impact: Logs enganosos e dados pessoais nos logs.
Recommendation: Módulo logging com níveis. Substituir ou remover as simulações de notificação.

[LOW] Magic numbers e strings

File: models.py:247-262; controllers.py:47-52, 242; database.py:5; app.py:88
Anti-pattern: AP-14 — Magic Numbers / Magic Strings
Description: Faixas e percentuais de desconto inline. Status literais em models.py:247-253 e em lista em controllers.py:242. Limites de nome (2, 200). Lista de categorias sem constante compartilhada com o seed. Caminho "loja.db" e porta 5000 literais.
Recommendation: FAIXAS_DESCONTO, STATUS_PEDIDO, CATEGORIAS_VALIDAS, DB_PATH.

[LOW] Nomes sem semântica e sombreamento de built-in

File: controllers.py:14, 56, 64, 98, 136, 160; models.py:24, 54, 65, 89, 187-193, 219-225
Anti-pattern: AP-15 — Nomes de Variáveis Sem Semântica
Description: id sombreia o built-in id() em 10 funções. cursor2, cursor3, prod, rows, result e dados são genéricos.
Recommendation: produto_id, usuario_id, cursor_itens, cursor_produto.

[LOW] Imports não utilizados

File: models.py:2; database.py:2
Anti-pattern: AP-16 — Imports Não Utilizados
Description: import sqlite3 em models.py e import os em database.py não são referenciados.
Recommendation: Remover os dois imports.

Observações fora do catálogo (não entram na contagem)

- Cancelamento não devolve estoque: controllers.py:249-250 imprime "Devolver estoque", mas nenhum código faz isso.
- Transição de status livre: qualquer status pode ir para qualquer outro (controllers.py:242-245).
- Usuário não verificado no pedido: criar_pedido não confere se usuario_id existe (controllers.py:198-199).
- Relatório inclui cancelados: relatorio_vendas soma pedidos cancelados no faturamento (models.py:242-243) e no ticket médio (models.py:272).
- CORS aberto: CORS(app) (app.py:9) libera qualquer origem.
- Versão de Python não declarada: requirements.txt lista só flask e flask-cors.

================================
Total: 20 findings
CRITICAL: 6 | HIGH: 5 | MEDIUM: 5 | LOW: 4

================================
PHASE 2 COMPLETE

Relatório salvo em: reports/audit-project-1.md
Total de findings: 20

Phase 3 vai reestruturar o projeto para o padrão MVC.
Todos os arquivos originais serão modificados ou movidos.

Proceed with refactoring (Phase 3)? [y/n]


Fase 1 e 2 concluídas. A Fase 3 não foi iniciada, porque o skill exige a sua confirmação. Antes de responder:

- Número do projeto: usei 1. Inferi pelo PLAN_PROJECT_1.md, que descreve code-smells-project como Projeto 1. Se não for esse o número, me diga e eu renomeio o relatório.
- Payloads: os exemplos de injection foram verificados por análise estática do código. Não executei contra o loja.db.
- Escopo da Fase 3: a reestruturação altera ou move todos os arquivos (app.py, controllers.py, models.py, database.py) e vai corrigir os 6 CRITICAL e os 5 HIGH. Preciso ler 04-mvc-guidelines.md e 05-refactoring-playbook.md antes de começar.

Responda y para seguir com a Fase 3, ou n para parar aqui.

---
A Fase 3 está concluída, e a aplicação sobe e responde corretamente. Nada foi commitado.

Nova estrutura

code-smells-project/
├── app.py                        entry point (create_app)
├── database.py                   conexão por request, schema, seed, transacao()
├── config/settings.py            configuração via variáveis de ambiente
├── models/                       SQL parametrizado, sem regra de negócio
│   ├── produto_model.py
│   ├── usuario_model.py
│   ├── pedido_model.py           JOIN único em vez de N+1
│   └── sistema_model.py
├── controllers/                  regras de negócio e validação
│   ├── produto_controller.py
│   ├── usuario_controller.py     hash de senha, login, migração
│   ├── pedido_controller.py      estoque, total, transação
│   ├── relatorio_controller.py   faixas de desconto
│   ├── sistema_controller.py
│   ├── validacao.py
│   └── erros.py
├── routes/                       blueprints HTTP, uma por domínio
├── middlewares/
│   ├── auth.py                   requer_admin (header X
│   └── error_handler.py          erros padronizados, 500 genérico
├── .env.example                  novo
└── README.md                     configuração e autenticação documentadas

models.py e controllers.py antigos foram removidos.

Findings resolvidos

- CRITICAL
  - C1 login bypass: resolvido com consulta parametrizada.
  - C2 UNION na busca: resolvido. Testado com o payload do relatório, sem vazamento.
  - C3 concatenação nas escritas: resolvido em todos os models.
  - C4 /admin/query removido. /admin/reset-db continua, mas protegido por token.
  - C5 senhas: hash com werkzeug.security, senha removid
  - C6 parcial: a SECRET_KEY literal foi removida e o /health não expõe mais a chave. O admin seed admin123 continua no código, agora com hash.
    Precisa de uma decisão sua (ver abaixo).
- HIGH
  - H1 e H2: regras de negócio saíram de models e routes SQL direto.
  - H3: duplicação removida. A validação de produto agora é a mesma na criação e na atualização.
  - H4: DEBUG e host de rede agora têm padrão seguro. Erros 500 não expõem mais str(e).
  - H5 (fora do catálogo): rotas de escrita e leitura adoken.
- MEDIUM
  - M1: N+1 eliminado com JOIN.
  - M2: conexão por request, BEGIN IMMEDIATE nos pedidos e rollback em erro. Isso também fecha o overselling.
  - M3: quantidade zero ou negativa é rejeitada.
  - M4: tipos e corpo JSON validados, respondendo 400 em vez de 500.
  - M5: erros são registrados com logger.exception.
- LOW: print trocado por logging, constantes nomeadas, id renomeado para produto_id, imports não usados removidos.

Validação

- Testes de contrato: 57 verificações via test client, todas passando. Cobrem todos os endpoints, os códigos de erro e os casos de injeção. O banco usado foi temporário, o loja.db não foi tocado.
- Boot real: python app.py subiu e respondeu. /health re sem token e 200 com token, e /admin/query deu 404.
- Migração: senhas em texto puro de bancos antigos são aceitas uma vez no login e regravadas com hash.

Mudanças de contrato (intencionais)

- senha não aparece mais em GET /usuarios nem em GET /usuarios/<id>.
- /health não retorna mais secret_key, db_path, debug ne
- POST /admin/query foi removido.
- Rotas admin exigem X-Admin-Token. Sem ADMIN_TOKEN configurado, respondem 403.
- usuario_id, produto_id e quantidade precisam ser inteipela concatenação.
- Erros de validação agora trazem "sucesso": false. Rotas desconhecidas respondem JSON.
- O servidor escuta em 127.0.0.1 por padrão. Para acesso.0.

Decisões que tomei

- werkzeug.security em vez de bcrypt: o Flask já traz o  dependência.
- Token único em vez de login por usuário: é o mínimo para cumprir H5. Autenticação por usuário é um passo maior.

Pendências que precisam da sua decisão

1. Admin seed (admin123): removo a criação automática do admin e passo a exigir um comando de setup, ou mantenho para demo?
2. Pendências fora do escopo desta fase:
   - GET /pedidos/usuario/<id> continua público, então qualquer um lê pedidos de outro usuário.
   - O cancelamento não devolve o estoque, e o relatório soma pedidos cancelados no faturamento.
   - CORS continua aberto para qualquer origem.

```


---

### Projeto 2 — `ecommerce-api-legacy` (Node.js/Express — LMS API)

| Severidade | Anti-Pattern | Arquivo | Linha(s) |
|---|---|---|---|
| CRITICAL | God Class `AppManager` — DB + rotas + lógica de negócio + hash em uma classe | `src/AppManager.js` | 1–141 |
| CRITICAL | Credenciais reais de produção hardcoded (chave live do gateway de pagamento) | `src/utils.js` | 1–7 |
| CRITICAL | Algoritmo de hash falso (`badCrypto`) — base64 truncado não é hash | `src/utils.js` | 17–23 |
| HIGH | Toda a lógica do checkout (50+ linhas) dentro de um route handler | `src/AppManager.js` | 28–78 |
| HIGH | Callback Hell — 5 níveis de aninhamento assíncrono | `src/AppManager.js` | 37–77 |
| HIGH | Deleção de usuário sem integridade referencial — matrículas ficam órfãs | `src/AppManager.js` | 131–136 |
| MEDIUM | N+1 Queries no relatório financeiro (curso → matrículas → usuário → pagamento) | `src/AppManager.js` | 80–129 |
| MEDIUM | Estado global mutável (`globalCache`, `totalRevenue`) sem controle | `src/utils.js` | 9–10 |
| MEDIUM | Número de cartão logado no console durante processamento | `src/AppManager.js` | 45 |
| LOW | Nomes de variáveis sem semântica (`u`, `e`, `p`, `cid`, `cc`) | `src/AppManager.js` | 29–33 |
| LOW | Ausência de error handling no DELETE de usuário (err ignorado) | `src/AppManager.js` | 131–136 |

**Por que esses problemas são relevantes:** A chave `pk_live_` do gateway de pagamento exposta representa risco financeiro direto. O hash falso torna todas as senhas trivialmente reversíveis. A God Class impossibilita qualquer teste unitário.

---
#### Resultado da execução da Skill

================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Node.js (versão não especificada)
Framework:     Express ^4.18.2
Dependencies:  express, sqlite3 ^5.1.6
Domain:        LMS API (com fluxo de checkout) para matrículas, pagamentos e relatório financeiro de cursos
Architecture:  Monolítica sem camadas — AppManager.js concentra schema/seed, rotas, regras de negócio e SQL; utils.js mistura config, cache global e "crypto"
Source files:  3 files analyzed
DB:            SQLite em memória (`:memory:`), SQL raw via callbacks, sem migrations
================================

================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js + Express
Files:   3 analyzed | ~180 lines of code
Date:    2026-10-27

## Summary

CRITICAL: 2 | HIGH: 4 | MEDIUM: 5 | LOW: 4
Total findings: 15

## Findings

### [CRITICAL] Hardcoded Credentials / Secrets
File: src/utils.js:1-7
Anti-pattern: AP-02 — Hardcoded Credentials / Secrets
Description: O objeto `config` contém credenciais literais versionadas no código:
  dbPass: "senha_super_secreta_prod_123"
  paymentGatewayKey: "pk_live_1234567890abcdef"
  dbUser: "admin_master", smtpUser: "no-reply@fullcycle.com.br"
Impact: Qualquer pessoa com acesso ao repositório obtém a chave live do gateway de pagamento e a senha do banco; rotação exige novo deploy.
Recommendation: Mover para variáveis de ambiente lidas em `config/settings.js` (com `.env.example`), sem valores sensíveis no código; remover chaves não utilizadas (db
User, dbPass, smtpUser).

---

### [CRITICAL] Senha com Hash Inseguro / Senha Padrão
File: src/utils.js:17-23 (usado em src/AppManager.js:68; seed em src/AppManager.js:18)
Anti-pattern: AP-04 — Senha em Texto Puro / Hash Inseguro
Description: `badCrypto` é um pseudo-hash: concatena 10.000 vezes os 2 primeiros caracteres do base64 da senha e devolve `substring(0, 10)`. Isso é determinístico, sem
 salt, e na prática revela os 2 primeiros caracteres repetidos (colisões massivas entre senhas distintas). Além disso, `badCrypto(p || "123456")` atribui uma senha pad
rão previsível quando `pwd` não é enviado, e o seed insere `pass = '123'` em texto puro (linha 18). O loop de 10.000 iterações também bloqueia o event loop a cada novo
 usuário.
Impact: Senhas de usuários são triviais de quebrar/colidir; contas criadas sem senha ficam com "123456".
Recommendation: Usar hash com salt (`crypto.scrypt`/`bcrypt`) em um serviço de senha; exigir `pwd` ou gerar token aleatório; fazer hash também do seed.

---

### [HIGH] God Class / God File
File: src/AppManager.js:4-139
Anti-pattern: AP-05 — God Class / God File
Description: `AppManager` acumula criação de conexão, DDL e seed (`initDb`), registro de rotas HTTP (`setupRoutes`), regras de negócio de checkout, simulação de gatewa
y de pagamento, geração de relatório e acesso a dados.
Impact: Impossível testar ou evoluir qualquer parte isoladamente; toda mudança toca o mesmo arquivo.
Recommendation: Separar em `config/`, `models/` (User, Course, Enrollment, Payment, AuditLog), `controllers/`, `routes/` e `middlewares/`.

---

### [HIGH] Lógica de Negócio em Route Handler
File: src/AppManager.js:28-78, 80-129, 131-137
Anti-pattern: AP-06 — Lógica de Negócio em Route Handler
Description: O handler de `POST /api/checkout` (~50 linhas) valida entrada, consulta curso e usuário, cria usuário, decide aprovação do cartão (`cc.startsWith("4")`),
grava matrícula, pagamento e auditoria e atualiza cache, com callbacks aninhados em 5 níveis. `GET /api/admin/financial-report` calcula receita e monta o relatório den
tro da rota, e `DELETE /api/users/:id` executa SQL direto.
Impact: Regras de negócio acopladas ao HTTP e ao SQL; "callback hell" dificulta manutenção e o tratamento correto de erros.
Recommendation: Criar `CheckoutController`/`ReportController` (ou services) chamando models com Promises/async-await; rotas apenas mapeiam URL → controller.

---

### [HIGH] Informações Sensíveis em Log
File: src/AppManager.js:45
Anti-pattern: AP-08 — Debug/Informações Sensíveis no Response ou logs
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` escreve o número completo do cartão e a chave live do gateway nos logs.
Impact: Violação de PCI-DSS; vazamento de dados de cartão e da chave em qualquer agregador de logs.
Recommendation: Não logar PAN nem chaves; no máximo logar os últimos 4 dígitos mascarados via logger estruturado.

---

### [HIGH] Endpoints Administrativos/Destrutivos sem Autenticação
File: src/AppManager.js:80, 131
Anti-pattern: Fora do catálogo (mais próximo de AP-08 — exposição de informação sensível)
Description: `GET /api/admin/financial-report` (nomes de alunos e receita) e `DELETE /api/users/:id` não têm nenhuma verificação de identidade/autorização.
Impact: Qualquer cliente anônimo lê dados financeiros e apaga usuários.
Recommendation: Adicionar middleware de autenticação/autorização para rotas admin. Obs.: isso altera o contrato das rotas; será tratado na Fase 3 apenas como middlewar
e opt-in (via variável de ambiente) para preservar os contratos existentes.

---

### [MEDIUM] N+1 Query Problem
File: src/AppManager.js:83-126
Anti-pattern: AP-09 — N+1 Query Problem
Description: Para cada curso roda uma query de matrículas; para cada matrícula, uma de usuário e uma de pagamento (3 níveis de queries em loop). A ordem do relatório t
ambém fica não determinística (`report.push` na ordem em que os callbacks terminam).
Impact: Número de queries cresce com cursos × matrículas; latência alta e ordem instável.
Recommendation: Uma única query com JOIN (courses ⟕ enrollments ⟕ users ⟕ payments) e agregação em memória, com `ORDER BY`.

---

### [MEDIUM] Ausência de Validação de Entrada
File: src/AppManager.js:29-35, 131-133
Anti-pattern: AP-11 — Ausência de Validação de Entrada
Description: Checkout só testa presença (`!u || !e || !cid || !cc`); não valida formato de e-mail, tipo de `c_id` ou formato do cartão. `req.body` indefinido gera exce
ção se o JSON for inválido; `:id` do DELETE é usado sem validação.
Impact: Dados inválidos persistidos; erros 500 evitáveis.
Recommendation: Criar validadores (`validators/`) para checkout e id numérico, retornando 400 com mensagem clara.

---

### [MEDIUM] Exceções/Erros Ignorados
File: src/AppManager.js:57-61, 92-94, 104-106, 133-135
Anti-pattern: AP-12 — Bare Except / Swallowed Exceptions
Description: O `err` do INSERT de `audit_logs` (57) é ignorado; em 92 `enrollments` é usado sem checar `err` (TypeError se a query falhar); em 104/106 os erros de user
/payment são descartados; o DELETE (133) responde sucesso mesmo com `err`.
Impact: Falhas silenciosas, respostas de sucesso incorretas e possível crash do processo.
Recommendation: Tratar todos os erros, propagar para um middleware de error handling central e logar.

---

### [MEDIUM] Estado Global Mutável
File: src/utils.js:9-15, 25
Anti-pattern: AP-10 — Estado Global Mutável
Description: `globalCache` é um objeto de módulo escrito por `logAndCache` a cada checkout (nunca lido, nunca expira); `totalRevenue` é variável global exportada e não
 usada.
Impact: Vazamento de memória crescente e estado compartilhado entre requisições.
Recommendation: Remover o cache morto ou encapsular em um módulo de cache com TTL/limite; remover `totalRevenue`.

---

### [MEDIUM] Integridade Referencial: Delete sem Cascata
File: src/AppManager.js:131-137
Anti-pattern: Fora do catálogo (mais próximo de AP-06 — acesso direto a banco em handler)
Description: `DELETE /api/users/:id` apaga só o usuário; a própria mensagem admite: "as matrículas e pagamentos ficaram sujos no banco". Não há FKs no DDL (linhas 12-1
6).
Impact: Matrículas/pagamentos órfãos distorcem o relatório financeiro (aluno aparece como "Unknown").
Recommendation: Apagar pagamentos e matrículas do usuário em transação (ou habilitar FKs com `ON DELETE CASCADE`), mantendo a resposta HTTP.

---

### [LOW] console.log para Logging
File: src/app.js:13; src/AppManager.js:45; src/utils.js:13
Anti-pattern: AP-13 — Print / Console.log para Logging
Description: Logs ad-hoc via `console.log` em entry point, handler e utilitário.
Impact: Sem níveis, sem estrutura; mistura log com dados sensíveis.
Recommendation: Usar um módulo logger único (`config/logger.js`) com níveis.

---

### [LOW] Magic Numbers / Magic Strings
File: src/AppManager.js:46, 48, 108; src/utils.js:19-22
Anti-pattern: AP-14 — Magic Numbers / Magic Strings
Description: Status `'PAID'`/`'DENIED'` literais em vários pontos, regra `cc.startsWith("4")`, `10000` iterações, `substring(0, 2)`/`(0, 10)`.
Impact: Typos silenciosos e regras difíceis de localizar.
Recommendation: Constantes nomeadas (`PAYMENT_STATUS`, `APPROVED_CARD_PREFIX`).

---

### [LOW] Nomes de Variáveis Sem Semântica
File: src/AppManager.js:29-33, 90, 102
Anti-pattern: AP-15 — Nomes de Variáveis Sem Semântica
Description: `u`, `e`, `p`, `cid`, `cc`, `c`, `enr` e campos do payload `usr`, `eml`, `pwd`, `c_id`.
Impact: Leitura difícil. Os nomes do payload fazem parte do contrato e serão mantidos na API, mapeados para nomes claros internamente.
Recommendation: Renomear variáveis internas (`name`, `email`, `password`, `courseId`, `cardNumber`).

---

### [LOW] Imports/Exports Não Utilizados
File: src/AppManager.js:2; src/utils.js:2-5, 25
Anti-pattern: AP-16 — Imports Não Utilizados
Description: `totalRevenue` é importado em AppManager mas nunca usado; `globalCache`, `totalRevenue` e as chaves `dbUser`, `dbPass`, `smtpUser` do config nunca são con
sumidos.
Impact: Ruído e superfície de configuração morta.
Recommendation: Remover.

================================
Total: 15 findings
sumidos.
Impact: Ruído e superfície de configuração morta.
Recommendation: Remover.

================================
Total: 15 findings
CRITICAL: 2 | HIGH: 4 | MEDIUM: 5 | LOW: 4
================================

Deprecated APIs: nenhuma encontrada (sem `crypto.createCipher`, sem `res.send(status, body)`).

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]

---

================================
PHASE 1: PROJECT ANALYSIS

Language:      Node.js (versão não especificada)
Framework:     Express ^4.18.2
Dependencies:  express, sqlite3 ^5.1.6
Domain:        LMS API (com fluxo de checkout) para matrículas, pagamentos e relatório financeiro de cursos
Architecture:  Monolítica sem camadas. AppManager.js concentra schema/seed, rotas, regras de negócio e SQL. utils.js mistura config, cache global e "crypto".
Source files:  3 files analyzed
DB:            SQLite em memória, SQL raw via callbacks, sem migrations

PHASE 2: ARCHITECTURE AUDIT (resumo)

Project: ecommerce-api-legacy, Node.js + Express, 3 arquivos, ~180 LOC.

CRITICAL: 2 | HIGH: 4 | MEDIUM: 5 | LOW: 4 | Total: 15

┌─────┬──────────┬───────────────────────────────────────────────────────────────────────────┬──────────────────────────────────────────┐
│  #  │   Sev    │                               Anti-pattern                                │                  Local                   │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 1   │ CRITICAL │ AP-02 Hardcoded secrets (pk_live_..., dbPass)                             │ utils.js:1-7                             │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 2   │ CRITICAL │ AP-04 Hash inseguro (badCrypto), senha padrão 123456, seed em texto puro  │ utils.js:17-23, AppManager.js:18,68      │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 3   │ HIGH     │ AP-05 God Class (AppManager)                                              │ AppManager.js:4-139                      │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 4   │ HIGH     │ AP-06 Lógica de negócio e SQL em route handlers (callbacks em 5 níveis)   │ AppManager.js:28-137                     │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 5   │ HIGH     │ AP-08 Log do cartão completo e da chave live                              │ AppManager.js:45                         │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 6   │ HIGH     │ Admin report e DELETE sem autenticação (fora do catálogo)                 │ AppManager.js:80,131                     │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 7   │ MEDIUM   │ AP-09 N+1 no relatório financeiro (ordem não determinística)              │ AppManager.js:83-126                     │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 8   │ MEDIUM   │ AP-11 Sem validação de entrada                                            │ AppManager.js:29-35,131-133              │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 9   │ MEDIUM   │ AP-12 Erros ignorados (err descartado, possível TypeError)                │ AppManager.js:57,92,104,106,133          │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 10  │ MEDIUM   │ AP-10 Estado global mutável (globalCache, totalRevenue)                   │ utils.js:9-15,25                         │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 11  │ MEDIUM   │ DELETE de usuário deixa matrículas e pagamentos órfãos (fora do catálogo) │ AppManager.js:131-137                    │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 12  │ LOW      │ AP-13 console.log como logging                                            │ app.js:13, AppManager.js:45, utils.js:13 │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 13  │ LOW      │ AP-14 Magic strings e números ('PAID', startsWith("4"), 10000)            │ AppManager.js:46,48,108, utils.js:19-22  │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 14  │ LOW      │ AP-15 Nomes sem semântica (u, e, p, cid, cc)                              │ AppManager.js:29-33,90,102               │
├─────┼──────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────┤
│ 15  │ LOW      │ AP-16 Imports e exports não usados                                        │ AppManager.js:2, utils.js:2-5,25         │
└─────┴──────────┴───────────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────┘

Deprecated APIs: nenhuma encontrada.

O relatório completo, com descrição, impacto e recomendação de cada finding, está em reports/audit-project-3.md. Inferi o N=3 pelo PLAN_PROJECT_3.md.

Duas observações sobre a Fase 3:
- Vou preservar os contratos dos endpoints, incluindo os nomes do payload (usr, eml, pwd, c_id, card) e as mensagens de resposta.
- Para o finding 6, a autenticação alteraria o contrato das rotas. Pretendo adicioná-la como middleware opt-in, ativado por variável de ambiente.

================================
PHASE 2 COMPLETE

Relatório salvo em: reports/audit-project-3.md
Total de findings: 15

Phase 3 vai reestruturar o projeto para o padrão MVC.
Todos os arquivos originais serão modificados ou movidos.

Proceed with refactoring (Phase 3)? [y/n]

---

================================
PHASE 3: REFACTORING COMPLETE

New Project Structure

src/
├── app.js                      entry point (~25 linhas)
├── constants.js                PAYMENT_STATUS, prefixo de cartão aprovado
├── config/settings.js          lê process.env, sem segredos no código
├── database/
│   ├── connection.js           sqlite com helpers run/get/all em Promise
│   └── init.js                 schema + seed (senha do seed com hash)
├── models/                     user, course, enrollment, payment, auditLog (SQL parametrizado)
├── controllers/                checkout, report, user (regras de negócio)
├── routes/                     checkout, admin, user + index (apenas HTTP)
├── middlewares/                errorHandler, adminAuth (opt-in)
├── services/                   passwordService (scrypt + salt), paymentService
├── validators/checkoutValidator.js
└── utils/                      logger, AppError
.env.example
Removidos: AppManager.js e utils.js.

Issues Resolved

- ✓ AP-02 Segredos hardcoded: agora vêm de process.env, e .env.example foi criado.
- ✓ AP-04 Hash inseguro: badCrypto foi trocado por scrypt com salt. A senha padrão 123456 virou senha aleatória, e o seed também recebe hash.
- ✓ AP-05 God Class: dividida em camadas MVC.
- ✓ AP-06 Lógica nas rotas: rotas finas, regras nos controllers e SQL nos models. Os callbacks viraram async/await.
- ✓ AP-08 Log sensível: o cartão aparece só como ****4444 e a chave não é mais logada.
- ✓ Endpoints admin sem auth: middleware opt-in, ativo quando ADMIN_TOKEN está definido.
- ✓ AP-09 N+1: o relatório usa uma query com JOIN, com ordem determinística.
- ✓ AP-10 Estado global: o cache morto e o totalRevenue foram removidos.
- ✓ AP-11 Validação: validator para checkout (e-mail, c_id inteiro, tipos) e para o :id do DELETE.
- ✓ AP-12 Erros ignorados: todos propagam para o errorHandler central.
- ✓ DELETE de usuário agora remove também matrículas e pagamentos.
- ✓ AP-13/14/15/16: logger único, constantes nomeadas, nomes semânticos e imports mortos removidos.

Validation

- ✓ A aplicação sobe sem erros (testada na porta 3055).
- ✓ Todos os endpoints responderam:
  - Checkout aprovado: 200 {msg, enrollment_id}.
  - Cartão recusado: 400 "Pagamento recusado".
  - Campos ausentes: 400 "Bad Request".
  - Curso inexistente: 404 "Curso não encontrado".
  - Relatório financeiro: 200 com o mesmo formato.
  - DELETE: 200, e o relatório depois dele não tem mais registros órfãos.
- ✓ Nenhum finding CRITICAL ou HIGH permanece. Busca por pk_live e senha_super em src/ não encontrou nada.

Mudanças de comportamento a conhecer:
- Mensagem do DELETE: mudou para "Usuário deletado junto com suas matrículas e pagamentos." O texto antigo dizia que os registros ficavam sujos, o que deixou de ser verdade. O status continua 200.
- ADMIN_TOKEN: sem ele definido, as rotas admin continuam abertas, como antes. Com ele definido, exigem o header x-admin-token.
- PAYMENT_GATEWAY_KEY: o novo settings.js a lê, mas o paymentService simulado ainda não a usa.
- Não testei: o caminho 401 do adminAuth e a rota de checkout com um e-mail já existente.
- Não commitei nada: as mudanças e o reports/audit-project-3.md estão só na árvore de trabalho.

---

### Projeto 3 — `task-manager-api` (Python/Flask — Task Manager)

| Severidade | Anti-Pattern | Arquivo | Linha(s) |
|---|---|---|---|
| CRITICAL | `SECRET_KEY` hardcoded | `app.py` | 13 |
| HIGH | Lógica de negócio nas routes — validações complexas e montagem de resposta | `routes/task_routes.py` | 11–299 |
| HIGH | API deprecated: `Model.query.get()` (removida no SQLAlchemy 2.1) | `routes/task_routes.py` | 42, 67, 117, 158, 188, 227 |
| HIGH | Lógica de `overdue` duplicada em 3 funções diferentes | `routes/task_routes.py` | 30–38, 71–80, 283–287 |
| MEDIUM | Camada `services/` existe mas não é usada pelas routes | `services/notification_service.py` | — |
| MEDIUM | Imports não utilizados (`json`, `os`, `sys`, `time`) | `routes/task_routes.py` | 7 |
| MEDIUM | Bare `except:` silenciando erros sem logging | `routes/task_routes.py` | 62–63, 236–238 |
| LOW | `print()` para logging em vez de logger estruturado | `routes/task_routes.py` | 149, 153, 219, 234 |
| LOW | `type(tags) == list` em vez de `isinstance(tags, list)` | `routes/task_routes.py` | 141, 210 |
| LOW | Ausência de módulo de configuração centralizado | `app.py` | 11–13 |

**Por que esses problemas são relevantes:** Apesar de ter organização parcial, o projeto viola MVC ao colocar lógica de negócio nas routes. A API deprecated quebrará em futuras atualizações do SQLAlchemy. O `SECRET_KEY` hardcoded é um risco crítico de segurança mesmo em projetos "parcialmente organizados".

---
#### Resulstado da execução da Skill

================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask
Files:   15 analyzed | ~1158 lines of code
Date:    2026-10-27

## Summary

CRITICAL: 2 | HIGH: 6 | MEDIUM: 3 | LOW: 5
Total findings: 16

## Findings

### [CRITICAL] Hardcoded Credentials / Secrets
File: app.py:9,12 | services/notification_service.py:7-10
Anti-pattern: AP-02 — Hardcoded Credentials / Secrets
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` (app.py:12) e
`self.email_password = 'senha123'` / `self.email_user = 'taskmanager@gmail.com'`
(notification_service.py:9-10) estão literais no código versionado. A URI do banco
(`sqlite:///tasks.db`, app.py:9) e o host SMTP também são hardcoded.
Impact: Qualquer pessoa com acesso ao repositório pode forjar sessões e usar a conta
SMTP; trocar de ambiente exige editar código.
Recommendation: Criar `config/settings.py` lendo `SECRET_KEY`, `DATABASE_URI`,
`SMTP_*` de variáveis de ambiente (python-dotenv já está no requirements) e falhar/avisar
se ausentes; adicionar `.env.example`.

---

### [CRITICAL] Senha com Hash Inseguro / Exposta na API
File: models/user.py:21,27-32
Anti-pattern: AP-04 — Senha em Texto Puro / Hash Inseguro
Description: `set_password` usa `hashlib.md5(pwd.encode()).hexdigest()` (sem salt) e
`to_dict()` inclui `'password': self.password` (linha 21). `to_dict()` é retornado em
GET /users/<id>, POST /users, PUT /users/<id> e POST /login.
Impact: Hashes MD5 vazam em respostas da API e são quebráveis por rainbow table em
segundos; todas as contas ficam comprometidas.
Recommendation: Usar `werkzeug.security.generate_password_hash` /
`check_password_hash` e remover `password` do `to_dict()`. Manter compatibilidade no
login com hashes MD5 legados (rehash no primeiro login) ou re-executar o seed.

---

### [HIGH] Deprecated API — SQLAlchemy Model.query.get()
File: routes/task_routes.py:42,51,67,117,122,158,188,195,227 | routes/user_routes.py:29,94,136,155 | routes/report_routes.py:105,192,213
Anti-pattern: DEP-01 — SQLAlchemy Model.query.get() depreciado
Description: 16 ocorrências de `Model.query.get(id)` (ex.: `User.query.get(t.user_id)`).
Impact: Quebra ao atualizar para SQLAlchemy 2.1+; emite warnings hoje.
Recommendation: Substituir por `db.session.get(Model, id)` dentro dos models/controllers.

---

### [HIGH] Lógica de Negócio em Route Handler
File: routes/task_routes.py:11-299 | routes/user_routes.py:10-211 | routes/report_routes.py:12-223
Anti-pattern: AP-06 — Lógica de Negócio em Route Handler
Description: Não há camada controller. Handlers fazem validação, queries, cálculo de
overdue/estatísticas e commit (ex.: `summary_report` com ~90 linhas e 10+ queries;
`create_task` e `update_task` com ~70 linhas cada). O diretório `services/` contém
apenas um `NotificationService` não utilizado.
Impact: Impossível testar regras sem HTTP; qualquer mudança de regra toca rotas.
Recommendation: Criar `controllers/` (task, user, category, report) com a lógica e
deixar `routes/` apenas com parse de request → chamada ao controller → jsonify.

---

### [HIGH] Lógica de Negócio Duplicada (DRY)
File: routes/task_routes.py:30-39,71-80,283-287 | routes/user_routes.py:171-180 | routes/report_routes.py:34-43,132-135 | routes/task_routes.py:16-28 vs routes/user_routes.py:162-169 |
routes/task_routes.py:96-144 vs 166-213 vs utils/helpers.py:57-108
Anti-pattern: AP-07 — Lógica de Negócio Duplicada (DRY Violation)
Description: A regra de "overdue" é reimplementada 6 vezes com if aninhado, embora
`Task.is_overdue()` (models/task.py:50-60) exista e nunca seja usada. A serialização
de task é copiada em 2 rotas, a validação de task existe em create, update e em
`process_task_data` (helpers, não usada), e o regex de email aparece em
user_routes.py:61,106 e helpers.py:21.
Impact: Correções de regra precisam ser feitas em N lugares; risco de divergência.
Recommendation: Usar `Task.is_overdue()` e `Task.to_dict()` (incluindo `overdue`) em
todos os pontos; centralizar validação em um módulo único usado por create/update.

---

### [HIGH] Debug Mode em Produção
File: app.py:33
Anti-pattern: AP-08 — Debug Mode em Produção
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` fixo no código.
Impact: Debugger interativo Werkzeug exposto na rede permite execução remota de código.
Recommendation: Ler `DEBUG`, `HOST`, `PORT` da config/ambiente com default `False`
e host `127.0.0.1`.

---

### [HIGH] Autenticação Falsa / Sem Autorização
File: routes/user_routes.py:207-211, 71-78
Anti-pattern: AP-08 — Informações sensíveis / segurança no response (mais próximo no catálogo)
Description: `/login` retorna `'token': 'fake-jwt-token-' + str(user.id)`, token
previsível que nenhum endpoint valida. Todos os endpoints são públicos e `POST /users`
aceita `role: 'admin'` de qualquer cliente.
Impact: Qualquer um pode criar admin, listar/editar/deletar usuários e tasks.
Recommendation: No escopo desta refatoração, manter o contrato do token, mas isolar a
geração em um módulo de auth e documentar a limitação; autenticação real (JWT) fica
como próximo passo, pois altera o comportamento da API.

---

### [HIGH] God File — Responsabilidades Misturadas
File: routes/report_routes.py:157-223
Anti-pattern: AP-05 — God Class / God File
Description: `report_routes.py` contém relatórios (`/reports/*`) e todo o CRUD de
categorias (`/categories`), além de importar helpers não usados.
Impact: Dificulta localizar e evoluir cada domínio.
Recommendation: Mover o CRUD de categorias para `category_routes.py` +
`category_controller.py`, preservando as URLs.

---

### [MEDIUM] N+1 Query Problem
File: routes/task_routes.py:41-57 | routes/user_routes.py:22 | routes/report_routes.py:55-61,163
Anti-pattern: AP-09 — N+1 Query Problem
Description: `GET /tasks` faz `User.query.get` e `Category.query.get` por task;
`GET /users` acessa `len(u.tasks)` (lazy load por usuário); `summary_report` faz
`Task.query.filter_by(user_id=u.id).all()` por usuário; `GET /categories` faz um
`count()` por categoria.
Impact: Número de queries cresce linearmente com os dados.
Recommendation: Usar `joinedload`/`selectinload` e `group_by` com `func.count`.

---

### [MEDIUM] Ausência de Validação de Entrada
File: routes/task_routes.py:113,182,261,264 | routes/user_routes.py:103,125 | routes/report_routes.py:196-202,173-180
Anti-pattern: AP-11 — Ausência de Validação de Entrada
Description: `priority < 1` com valor não numérico gera TypeError; `int(priority)` /
`int(user_id)` em /tasks/search sem tratamento gera 500 (ValueError); `PUT /categories`
usa `'name' in data` sem checar `data is None`; `title` não é checado como string;
`active` e `color` não são validados; `name` de usuário aceita vazio no update.
Impact: Entradas malformadas causam 500 ou dados inválidos persistidos.
Recommendation: Funções de validação nos controllers com tipos/limites e resposta 400.

---

### [MEDIUM] Bare Except / Swallowed Exceptions
File: routes/task_routes.py:62,137,204,236 | routes/user_routes.py:130,149 | routes/report_routes.py:186,207,221 | routes/task_routes.py:221 | utils/helpers.py:47,49,88
Anti-pattern: AP-12 — Bare Except / Swallowed Exceptions
Description: `except:` sem tipo (inclui KeyboardInterrupt) e `except Exception as e`
sem logar `e` (task_routes.py:221). `get_tasks` retorna 'Erro interno' sem registrar a causa.
Impact: Falhas reais ficam invisíveis, dificultando diagnóstico.
Recommendation: Capturar exceções específicas (`ValueError`, `SQLAlchemyError`),
logar com `logging` e centralizar o tratamento em um error handler global.

---

### [LOW] Print para Logging
File: routes/task_routes.py:149,153,219,234 | routes/user_routes.py:83,89,147 | services/notification_service.py:21,24 | utils/helpers.py:39-41
Anti-pattern: AP-13 — Print / Console.log para Logging
Description: Uso de `print()` em vez de `logging`.
Impact: Sem níveis, formato ou destino configurável.
Recommendation: Usar `logging.getLogger(__name__)`.

---

### [LOW] Magic Numbers / Magic Strings
File: routes/task_routes.py:110,177 | models/task.py:39,52-53 | utils/helpers.py:75 | routes/user_routes.py:64,71,115,120 | routes/report_routes.py:129
Anti-pattern: AP-14 — Magic Numbers / Magic Strings
Description: Lista de status repetida 4 vezes, roles, limites de prioridade (1-5),
tamanho de senha/título e `priority <= 2` hardcoded, apesar de `helpers.py:110-116`
definir constantes que ninguém importa.
Impact: Mudanças exigem edição em vários arquivos.
Recommendation: Centralizar em `config/constants.py` (ou no model) e importar.

---

### [LOW] Nomes de Variáveis Sem Semântica
File: routes/report_routes.py:24-28 | routes/task_routes.py:16,42,51 | routes/user_routes.py:14,37 | models/task.py:45 | models/user.py:27 | utils/helpers.py:25
Anti-pattern: AP-15 — Nomes de Variáveis Sem Semântica
Description: `p1..p5`, `t`, `u`, `c`, `cat`, `p`, `pwd`, `s`.
Impact: Leitura mais difícil.
Recommendation: Renomear (`task`, `user`, `category`, `priority`, `password`).

---

### [LOW] Imports Não Utilizados / Código Morto
File: app.py:5 | routes/task_routes.py:7 | routes/user_routes.py:6 | routes/report_routes.py:7-8 | models/task.py:3 | utils/helpers.py:2-7,9-55 | services/notification_service.py:4-48
Anti-pattern: AP-16 — Imports Não Utilizados
Description: `os, sys, json, time`, `hashlib` (user_routes), `format_date`,
`calculate_percentage`, `math` etc. não são usados. `NotificationService` e a maior parte
de `helpers.py` não são referenciados em lugar nenhum.
Impact: Ruído e dependências desnecessárias.
Recommendation: Remover imports e código morto (ou integrá-lo, como `is_overdue`).

---

### [LOW] Deprecated API — datetime.utcnow()
File: models/*.py (default de colunas) | routes/*.py | services/notification_service.py:35 | utils/helpers.py:38
Anti-pattern: Não catalogado (relacionado a DEP)
Description: `datetime.utcnow()` está depreciado desde o Python 3.12 (projeto roda em 3.14).
Impact: DeprecationWarning; será removido no futuro.
Recommendation: Isolar em um helper `utc_now()` único. Cuidado: as colunas guardam
datetimes naive, então o helper deve retornar naive UTC para manter compatibilidade.


### [LOW] Deprecated API — datetime.utcnow()
File: models/*.py (default de colunas) | routes/*.py | services/notification_service.py:35 | utils/helpers.py:38
Anti-pattern: Não catalogado (relacionado a DEP)
Description: `datetime.utcnow()` está depreciado desde o Python 3.12 (projeto roda em 3.14).
Impact: DeprecationWarning; será removido no futuro.
Recommendation: Isolar em um helper `utc_now()` único. Cuidado: as colunas guardam
datetimes naive, então o helper deve retornar naive UTC para manter compatibilidade.

================================
Total: 16 findings
CRITICAL: 2 | HIGH: 6 | MEDIUM: 3 | LOW: 5
================================

---

================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (versão não especificada; __pycache__ indica 3.14)
Framework:     Flask 3.0.0
Dependencies:  flask-sqlalchemy 3.1.1, flask-cors 4.0.0, marshmallow 3.20.1 (não usado), requests 2.31.0 (não usado), python-dotenv 1.0.0 (não usado)
Domain:        Task Manager API para criação, atribuição e acompanhamento de tarefas, usuários e categorias
Architecture:  Parcialmente organizada. Existem models/, routes/, services/ e utils/, mas não há camada Controller. A lógica de negócio está nas routes.
Source files:  15 files analyzed (~1158 LOC)
DB:            SQLite (instance/tasks.db), ORM Flask-SQLAlchemy, sem migrations (db.create_all)
================================

Phase 2: audit

Assumi que este é o projeto nº 3, então o relatório completo está em reports/audit-project-3.md. Me diga se o número for outro.

Resumo: 16 findings. CRITICAL: 2 | HIGH: 6 | MEDIUM: 3 | LOW: 5.

┌──────────┬────────────────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────┐
│   Sev    │                              Finding                               │                              Local                               │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ CRITICAL │ AP-02 Secrets hardcoded (SECRET_KEY, senha SMTP senha123, URI do   │ app.py:9,12, services/notification_service.py:9-10               │
│          │ banco)                                                             │                                                                  │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ CRITICAL │ AP-04 Senha com MD5 sem salt, e password retornado em to_dict()    │ models/user.py:21,27-32                                          │
│          │ (login, GET/POST/PUT de usuários)                                  │                                                                  │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ HIGH     │ DEP-01 Model.query.get() (16 ocorrências)                          │ task_routes, user_routes, report_routes                          │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ HIGH     │ AP-06 Lógica de negócio nas routes, sem controllers                │ todas as routes                                                  │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ HIGH     │ AP-07 "Overdue" duplicado 6 vezes (Task.is_overdue() existe e não  │ task_routes.py:30-39,71-80,283-287, user_routes.py:171-180,      │
│          │ é usado); serialização e validação duplicadas                      │ report_routes.py:34-43,132-135                                   │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ HIGH     │ AP-08 debug=True com host=0.0.0.0                                  │ app.py:33                                                        │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ HIGH     │ Token falso fake-jwt-token-<id>, sem autorização, e POST /users    │ user_routes.py:207-211,71-78                                     │
│          │ aceita role: admin                                                 │                                                                  │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ HIGH     │ AP-05 CRUD de categorias dentro de report_routes.py                │ report_routes.py:157-223                                         │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ MEDIUM   │ AP-09 N+1 em /tasks, /users, /reports/summary, /categories         │ task_routes.py:41-57, report_routes.py:55-61,163                 │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ MEDIUM   │ AP-11 Validação ausente (int() sem try, data None, tipos)          │ task_routes.py:113,182,261,264, report_routes.py:196-202         │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ MEDIUM   │ AP-12 Bare except: e exceções sem log                              │ task_routes.py:62,137,204,236, user_routes.py:130,149,           │
│          │                                                                    │ report_routes.py:186,207,221                                     │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ LOW      │ AP-13 print em vez de logging                                      │ várias                                                           │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ LOW      │ AP-14 Strings e números mágicos (status repetido 4×; constantes em │ várias                                                           │
│          │  helpers.py não usadas)                                            │                                                                  │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ LOW      │ AP-15 Nomes ruins (p1..p5, t, u, c)                                │ várias                                                           │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ LOW      │ AP-16 Imports e código morto (NotificationService, a maior parte   │ várias                                                           │
│          │ de helpers.py)                                                     │                                                                  │
├──────────┼────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ LOW      │ datetime.utcnow() depreciado (não está no catálogo)                │ models, routes                                                   │
└──────────┴────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────┘

Três pontos a decidir antes da Fase 3:
- Hash de senha: trocar MD5 por werkzeug invalida os hashes existentes. Vou manter compatibilidade com MD5 no login, com rehash no primeiro acesso, e remover password das respostas. Isso muda o contrato das respostas.
- Autenticação: o token falso e a falta de autorização vão continuar. Implementar JWT mudaria o comportamento da API, e a skill exige preservar os contratos. Fica documentado como próximo passo.
- seed.py: vou ajustá-lo para usar os novos models.

================================
PHASE 2 COMPLETE
================================
Relatório salvo em: reports/audit-project-3.md
Total de findings: 16

Phase 3 vai reestruturar o projeto para o padrão MVC.
Todos os arquivos originais serão modificados ou movidos.

Proceed with refactoring (Phase 3)? [y/n]
---

Phase 3: refactoring complete

================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
task-manager-api/
├── app.py                      create_app(), blueprints, error handlers (~45 lines)
├── database.py
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
task-manager-api/
├── app.py                      create_app(), blueprints, error handlers (~45 lines)
├── database.py
├── seed.py                     imports updated
├── .env.example, .gitignore
├── config/        settings.py (env vars), constants.py
├── models/        base.py (CrudMixin), task_model.py, user_model.py, category_model.py
├── controllers/   task_, user_, category_, report_controller.py
├── routes/        task_, user_, category_, report_routes.py   (thin handlers)
├── middlewares/   error_handler.py
├── services/      notification_service.py   (now reads SMTP settings from env)
└── utils/         errors.py, validators.py, time_utils.py

## Issues Resolved
  ✓ AP-02 Secrets: SECRET_KEY, SMTP credentials and DB URI now come from environment variables
  ✓ AP-04 Password hashing: PBKDF2 replaces MD5, and `password` is no longer in any response
  ✓ DEP-01 `Model.query.get` replaced by `db.session.get` (0 occurrences left)
  ✓ AP-05/06 Controllers added; category CRUD moved out of report_routes; handlers are 2–8 lines
  ✓ AP-07 One `Task.is_overdue()`, one serializer, one validator (create and update share it)
  ✓ AP-08 `debug` is now off by default (`DEBUG` env var), host defaults to 127.0.0.1
  ✓ AP-09 N+1 queries replaced by joinedload and group-by counts
  ✓ AP-11 Validation added for types, search params, `active`, `color` and a null body
  ✓ AP-12/13 No bare `except:`; `logging` replaces `print` (seed.py keeps its prints, since it's a utility script)
  ✓ AP-14/15/16 Constants centralized, names cleaned up, dead code and unused imports removed
  ✓ `datetime.utcnow()` wrapped in `utc_now()`

## Validation
  ✓ Application boots without errors (real server started on :5055, /health, /tasks/stats, /categories and /reports/summary answered)
  ✓ 48-request smoke script run against the original and the refactored code: status codes and bodies are identical, apart from the intentional changes below
  ✓ A legacy MD5 user can log in and the hash is upgraded on that login (a wrong password still returns 401)
  ✓ No CRITICAL/HIGH finding is left, except the fake auth below
================================

Contract changes (intentional)
- password is gone from /users, /login and the other user responses.
- Bad inputs that used to return 500 now return 400: a non-numeric priority or user_id on /tasks/search, or a non-numeric priority on task create or update.
- New validation can reject payloads that used to pass: invalid active, color or user name, and empty category names.

Still open
- Fake auth: /login still returns fake-jwt-token-<id> and no endpoint checks it. POST /users still accepts role: admin from anyone. Real JWT auth would change the API, so I left it as the next step.
- README: I added a section on the new structure to README.md, including the password change and the fake token.
- Unrelated change: git status also shows ../README.md as modified. I didn't touch it, so it may be your own edit.
- Smoke tests: they ran in a scratch copy, so your instance/tasks.db was never modified. Run python seed.py before python app.py.
- Dependencies: flask-sqlalchemy wasn't installed in your environment. I installed the dependencies into the scratchpad, not globally.
- Commit: nothing is committed. Do you want me to commit this?

---

## Construção da Skill

### Estrutura da Skill

```
.claude/skills/refactor-arch/
├── SKILL.md                    ← Instruções das 3 fases sequenciais
├── 01-project-analysis.md      ← Heurísticas de detecção de stack e arquitetura
├── 02-antipatterns-catalog.md  ← 16 anti-patterns + 4 deprecated APIs com sinais de detecção
├── 03-report-template.md       ← Template padronizado do relatório de auditoria
├── 04-mvc-guidelines.md        ← Regras MVC: responsabilidades por camada + exemplos
└── 05-refactoring-playbook.md  ← 11 padrões de transformação com código antes/depois
```

### Decisões de Design

**SKILL.md como orquestrador, arquivos de referência como conhecimento:**  
O `SKILL.md` age como um prompt de sistema estruturado que instrui o agente a executar 3 fases em sequência, com pontos de parada explícitos. Os arquivos de referência fornecem o conhecimento de domínio necessário para cada fase, sem misturá-los no arquivo principal — isso mantém o SKILL.md legível e os arquivos de referência focados.

**Por que 16 anti-patterns + 4 deprecated APIs:**  
O catálogo foi construído bottom-up: primeiro identifiquei os problemas reais nos 3 projetos, depois generalizei os sinais de detecção. Isso garante que o catálogo detecte problemas reais, não apenas teóricos. A inclusão de deprecated APIs (`Model.query.get()`, `crypto.createCipher()`) resolve um problema específico do Projeto 3 que seria fácil de perder.

**Por que separar guidelines de MVC e o playbook:**  
As guidelines (`04`) descrevem o *destino* (o que cada camada deve e não deve fazer), enquanto o playbook (`05`) descreve as *transformações* (como sair do estado atual para o estado alvo). Separar os dois permite que o agente consulte as guidelines para decisões de estrutura e o playbook para implementação concreta.

**Como garantiu agnóstica de tecnologia:**
- O catálogo de anti-patterns tem seções por linguagem (Python e Node.js) com sinais de detecção específicos para cada uma
- O `01-project-analysis.md` tem tabelas de mapeamento para múltiplas linguagens e frameworks
- As guidelines (`04`) têm exemplos de estrutura MVC para Python/Flask e Node.js/Express
- O playbook (`05`) tem exemplos de transformação em ambas as linguagens para cada padrão
- A Fase 1 detecta a stack antes de qualquer análise, permitindo que as fases seguintes adaptem a abordagem

**Desafios encontrados:**
- **Callback Hell vs. Async/Await (Node.js):** O projeto usa sqlite3 com callbacks, mas a refatoração ideal usa Promises/async-await. O playbook inclui a transformação completa (PB-05) para não deixar ambiguidade.
- **Projeto 3 parcialmente organizado:** A skill precisa ser útil mesmo quando a estrutura já existe parcialmente. A solução foi fazer a Fase 1 mapear explicitamente o que está certo e o que falta, para a Fase 3 complementar sem destruir o que já está bem.
- **Pausa obrigatória na Fase 2:** A instrução de pausa está em destaque visual no SKILL.md (bloco `⚠️`) e no output da Fase 2, para que o agente não a ignore ao executar sequencialmente.

---

## Resultados

> **Nota:** Esta seção será preenchida após a execução da skill nos 3 projetos.

### Resumo dos Relatórios de Auditoria (a preencher)

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|
| `code-smells-project` | — | — | — | — | — |
| `ecommerce-api-legacy` | — | — | — | — | — |
| `task-manager-api` | — | — | — | — | — |

### Estrutura Antes/Depois (a preencher)

Os relatórios gerados pela skill serão salvos em:
- [`code-smells-project/reports/audit-project-1.md`](code-smells-project/reports/audit-project-1.md)
- [`ecommerce-api-legacy/reports/audit-project-2.md`](ecommerce-api-legacy/reports/audit-project-2.md)
- [`task-manager-api/reports/audit-project-3.md`](task-manager-api/reports/audit-project-3.md)

### Checklist de Validação — Projeto 1 (`code-smells-project`)

#### Fase 1 — Análise
- [ ] Linguagem detectada corretamente (Python)
- [ ] Framework detectado corretamente (Flask)
- [ ] Domínio da aplicação descrito corretamente (E-commerce API)
- [ ] Número de arquivos analisados condiz com a realidade (4 arquivos)

#### Fase 2 — Auditoria
- [ ] Relatório segue o template definido nos arquivos de referência
- [ ] Cada finding tem arquivo e linhas exatos
- [ ] Findings ordenados por severidade (CRITICAL → LOW)
- [ ] Mínimo de 5 findings identificados
- [ ] Detecção de APIs deprecated incluída (se aplicável)
- [ ] Skill pausa e pede confirmação antes da Fase 3

#### Fase 3 — Refatoração
- [ ] Estrutura de diretórios segue padrão MVC
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models criados para abstrair dados
- [ ] Views/Routes separadas para visualização ou roteamento
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem corretamente

---

### Checklist de Validação — Projeto 2 (`ecommerce-api-legacy`)

#### Fase 1 — Análise
- [ ] Linguagem detectada corretamente (Node.js / JavaScript)
- [ ] Framework detectado corretamente (Express)
- [ ] Domínio da aplicação descrito corretamente (LMS com checkout)
- [ ] Número de arquivos analisados condiz com a realidade (3 arquivos em src/)

#### Fase 2 — Auditoria
- [ ] Relatório segue o template definido nos arquivos de referência
- [ ] Cada finding tem arquivo e linhas exatos
- [ ] Findings ordenados por severidade (CRITICAL → LOW)
- [ ] Mínimo de 5 findings identificados
- [ ] Detecção de APIs deprecated incluída (se aplicável)
- [ ] Skill pausa e pede confirmação antes da Fase 3

#### Fase 3 — Refatoração
- [ ] Estrutura de diretórios segue padrão MVC
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models criados para abstrair dados
- [ ] Views/Routes separadas para visualização ou roteamento
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem corretamente

---

### Checklist de Validação — Projeto 3 (`task-manager-api`)

#### Fase 1 — Análise
- [ ] Linguagem detectada corretamente (Python)
- [ ] Framework detectado corretamente (Flask + SQLAlchemy)
- [ ] Domínio da aplicação descrito corretamente (Task Manager API)
- [ ] Número de arquivos analisados condiz com a realidade (~15 arquivos em múltiplos diretórios)

#### Fase 2 — Auditoria
- [ ] Relatório segue o template definido nos arquivos de referência
- [ ] Cada finding tem arquivo e linhas exatos
- [ ] Findings ordenados por severidade (CRITICAL → LOW)
- [ ] Mínimo de 5 findings identificados
- [ ] Detecção de APIs deprecated incluída (`Model.query.get()` do SQLAlchemy)
- [ ] Skill pausa e pede confirmação antes da Fase 3

#### Fase 3 — Refatoração
- [ ] Estrutura de diretórios segue padrão MVC
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models criados para abstrair dados
- [ ] Views/Routes separadas para visualização ou roteamento
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem corretamente

---

## Como Executar

### Pré-requisitos

- **Claude Code** instalado e configurado (`claude` disponível no PATH)
- Python 3.x instalado (para projetos 1 e 3)
- Node.js 18+ instalado (para o projeto 2)
- Dependências de cada projeto instaladas (ver abaixo)

### Instalação das dependências

```bash
# Projeto 1 — Python/Flask
cd code-smells-project
pip install -r requirements.txt

# Projeto 2 — Node.js/Express
cd ecommerce-api-legacy
npm install

# Projeto 3 — Python/Flask + SQLAlchemy
cd task-manager-api
pip install -r requirements.txt
```

### Execução da Skill

```bash
# Projeto 1 — code-smells-project
cd code-smells-project
claude "/refactor-arch"

# Projeto 2 — ecommerce-api-legacy
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3 — task-manager-api
cd ../task-manager-api
claude "/refactor-arch"
```

> **Nota:** A skill pausará ao final da Fase 2 e aguardará confirmação (`y`) antes de iniciar a refatoração. Revise o relatório de auditoria antes de confirmar.

### Como validar que a refatoração funcionou

**Projeto 1 (Python/Flask):**
```bash
cd code-smells-project
python app.py
# Em outro terminal:
curl http://localhost:5000/health
curl http://localhost:5000/produtos
curl http://localhost:5000/usuarios
curl -X POST http://localhost:5000/login -H "Content-Type: application/json" -d '{"email":"test@test.com","senha":"123"}'
```

**Projeto 2 (Node.js/Express):**
```bash
cd ecommerce-api-legacy
node src/app.js
# Em outro terminal:
curl http://localhost:3000/api/admin/financial-report
```

**Projeto 3 (Python/Flask):**
```bash
cd task-manager-api
python app.py
# Em outro terminal:
curl http://localhost:5000/health
curl http://localhost:5000/tasks
curl http://localhost:5000/tasks/stats
```

### Estrutura dos relatórios gerados

Após executar a skill em cada projeto, os relatórios de auditoria (output da Fase 2) são salvos automaticamente em:

```
code-smells-project/reports/audit-project-1.md
ecommerce-api-legacy/reports/audit-project-2.md
task-manager-api/reports/audit-project-3.md
```

---

## Estrutura do Repositório

```
mba-ia-refactor-projects-skill/
├── README.md
├── code-smells-project/                       # Projeto 1 — Python/Flask (E-commerce API)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/                 # ← SKILL AQUI
│   │           ├── SKILL.md
│   │           ├── 01-project-analysis.md
│   │           ├── 02-antipatterns-catalog.md
│   │           ├── 03-report-template.md
│   │           ├── 04-mvc-guidelines.md
│   │           └── 05-refactoring-playbook.md
│   ├── reports/
│   │   └── audit-project-1.md                 # (gerado pela skill)
│   ├── app.py
│   ├── controllers.py
│   ├── models.py
│   ├── database.py
│   └── requirements.txt
│
├── ecommerce-api-legacy/                      # Projeto 2 — Node.js/Express (LMS API)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/                 # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── reports/
│   │   └── audit-project-2.md                 # (gerado pela skill)
│   ├── src/
│   │   ├── app.js
│   │   ├── AppManager.js
│   │   └── utils.js
│   └── package.json
│
└── task-manager-api/                          # Projeto 3 — Python/Flask (Task Manager)
    ├── .claude/
    │   └── skills/
    │       └── refactor-arch/                 # ← CÓPIA DA SKILL
    │           └── ...
    ├── reports/
    │   └── audit-project-3.md                 # (gerado pela skill)
    ├── app.py
    ├── database.py
    ├── models/
    ├── routes/
    ├── services/
    └── utils/
```

---

# Criação de Skills — Refatoração Arquitetural Automatizada

Ao longo do curso você aprendeu o que são Skills e como elas permitem que um agente de IA atue como um especialista em tarefas específicas. Agora imagine o seguinte cenário: você herdou 3 projetos legados com problemas de arquitetura, segurança e qualidade de código. Revisar e corrigir tudo manualmente levaria dias.

Neste desafio, você vai criar uma Skill que automatiza esse processo — analisando, auditando e refatorando qualquer projeto para o padrão MVC, independente da tecnologia.

## Objetivo

Você deve entregar uma Skill capaz de:

- Analisar uma codebase detectando linguagem, framework e arquitetura atual
- Identificar anti-patterns e code smells, classificando por severidade com arquivo e linha exatos
- Gerar um relatório de auditoria estruturado com todos os achados
- Refatorar o projeto para o padrão MVC (Model-View-Controller), eliminando os problemas encontrados
- Validar o resultado garantindo que a aplicação continua funcionando após as mudanças

A skill deve ser agnóstica de tecnologia, funcionando com diferentes linguagens e frameworks.

## Contexto

### Definição de Severidades

Para padronizar a sua auditoria e os relatórios gerados pela IA, utilize a seguinte escala de classificação baseada em problemas de MVC e SOLID:

- **CRITICAL:** Falhas graves de arquitetura ou segurança que impedem o funcionamento correto, expõem dados sensíveis (ex: credenciais hardcoded, SQL Injection) ou violam completamente a separação de responsabilidades (ex: "God Class" contendo banco de dados, lógicas complexas e roteamento no mesmo arquivo).
- **HIGH:** Fortes violações do padrão MVC ou princípios SOLID que dificultam muito a manutenção e testes (ex: lógicas de negócio pesadas presas dentro de Controllers, forte acoplamento sem Injeção de Dependência, ou uso de estado global mutável em toda a aplicação).
- **MEDIUM:** Problemas de padronização, duplicação de código ou gargalos de performance moderada (ex: Queries N+1 no banco de dados, uso inadequado de middlewares, validações ausentes nas rotas).
- **LOW:** Melhorias de legibilidade, nomenclatura de variáveis ruins, ou "magic numbers" soltos pelo código.

### Exemplo de Uso no CLI

```bash
# Executar a skill no projeto com problemas
cd code-smells-project
claude "/refactor-arch"
```

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python
Framework:      Flask 3.1.1
Dependencies:  flask-cors
Domain:        E-commerce API (produtos, pedidos, usuários)
Architecture:  Monolítica — tudo em 4 arquivos, sem separação de camadas
Source files:  4 files analyzed
DB tables:     produtos, usuarios, pedidos, itens_pedido
================================
```

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask
Files:   4 analyzed | ~800 lines of code

## Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 2 | LOW: 3

## Findings

### [CRITICAL] God Class / God Method
File: models.py:1-350
Description: Arquivo único contém toda lógica de negócio, queries SQL, validação e formatação para 4 domínios diferentes.
Impact: Impossível testar em isolamento, qualquer mudança afeta tudo.
Recommendation: Separar em models e controllers por domínio.

### [CRITICAL] Hardcoded Credentials
File: app.py:8
Description: SECRET_KEY hardcoded como 'minha-chave-super-secreta-123'
...

================================
Total: 14 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y
```

```
[... refatoração executada ...]

================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
src/
├── config/settings.py
├── models/
│   ├── produto_model.py
│   └── usuario_model.py
├── views/
│   └── routes.py
├── controllers/
│   ├── produto_controller.py
│   └── pedido_controller.py
├── middlewares/error_handler.py
└── app.py (composition root)

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
  ✓ Zero anti-patterns remaining
================================
```

## Tecnologias obrigatórias

- **Ferramenta:** uma das três opções abaixo (não são aceitas outras ferramentas):
  - Claude Code
  - Gemini CLI
  - OpenAI Codex
- **Recurso:** Custom Skills (ou o equivalente na ferramenta escolhida)
- **Formato dos arquivos de referência:** Markdown
- **Projetos-alvo:** Python/Flask (2 projetos) e Node.js/Express (1 projeto) (fornecidos no repositório base)

> **Nota sobre a ferramenta:** Os exemplos deste documento usam o Claude Code (`.claude/skills/`) como referência, pois é a ferramenta utilizada no curso. Se você optar por Gemini CLI ou Codex, adapte o nome da pasta e o comando de invocação conforme a convenção dela — o conceito de skill e a estrutura interna (SKILL.md + arquivos de referência) permanecem os mesmos.

## Requisitos

### 1. Análise Manual dos Projetos

Antes de criar a skill, você deve entender os problemas que ela vai resolver.

**Tarefas:**

- Analisar o projeto `code-smells-project/` (Python/Flask — API de E-commerce)
- Analisar o projeto `ecommerce-api-legacy/` (Node.js/Express — LMS API com fluxo de checkout)
- Analisar o projeto `task-manager-api/` (Python/Flask — API de Task Manager)

Para cada projeto, identificar e documentar no mínimo 5 problemas, incluindo pelo menos:

- 1 de severidade CRITICAL ou HIGH
- 2 de severidade MEDIUM
- 2 de severidade LOW

Documentar os achados na seção "Análise Manual" do seu `README.md`

> **Dica:** Não precisa encontrar todos os problemas — foque nos que têm maior impacto arquitetural. Use os projetos como insumo para entender quais padrões sua skill precisa detectar.

> **Por que 3 projetos?** Dois são Python/Flask (com níveis de organização diferentes) e um é Node.js/Express. Sua skill precisa funcionar nos 3 para provar que é verdadeiramente agnóstica de tecnologia — lidando tanto com código completamente desestruturado quanto com projetos que já possuem alguma separação de camadas.

### 2. Criação da Skill

Agora que você conhece os problemas, crie uma skill que os detecte, gere um relatório de auditoria e corrija automaticamente.

**Tarefas:**

Criar a skill dentro do projeto `code-smells-project/` e implementar o SKILL.md com 3 fases sequenciais:

- **Fase 1 — Análise:** Detectar stack, mapear arquitetura atual, imprimir resumo
- **Fase 2 — Auditoria:** Cruzar código contra catálogo de anti-patterns, gerar relatório, pedir confirmação
- **Fase 3 — Refatoração:** Reestruturar para o padrão MVC, validar que funciona

Criar arquivos de referência em Markdown que forneçam à skill o conhecimento necessário para executar as 3 fases. Os arquivos devem cobrir **obrigatoriamente** as seguintes áreas de conhecimento:

| Área de conhecimento | O que deve conter |
|---|---|
| Análise de projeto | Heurísticas para detecção de linguagem, framework, banco de dados e mapeamento de arquitetura |
| Catálogo de anti-patterns | Anti-patterns com sinais de detecção e classificação de severidade |
| Template de relatório | Formato padronizado do relatório de auditoria (Fase 2) |
| Guidelines de arquitetura | Regras do padrão MVC alvo (camadas Models, Views/Routes e Controllers, responsabilidades de cada uma) |
| Playbook de refatoração | Padrões concretos de transformação para cada anti-pattern (com exemplos de código) |

> **Nota:** Você tem liberdade para organizar os arquivos de referência como preferir — pode usar os nomes e a quantidade de arquivos que fizer sentido para sua skill. O importante é que todas as 5 áreas de conhecimento estejam cobertas. O nome da skill (`refactor-arch`) e o arquivo `SKILL.md` são obrigatórios e não devem ser alterados. O path da skill segue a convenção da ferramenta escolhida (no Claude Code, por exemplo, é `.claude/skills/refactor-arch/`).

**Requisitos da skill:**

- Deve ser agnóstica de tecnologia — deve funcionar corretamente nos 3 projetos fornecidos, independente da stack ou nível de organização
- O catálogo de anti-patterns deve conter no mínimo 8 anti-patterns com severidade distribuída (CRITICAL, HIGH, MEDIUM, LOW)
- O catálogo deve incluir detecção de APIs deprecated — identificar uso de APIs obsoletas e recomendar o equivalente moderno
- O playbook deve ter no mínimo 8 padrões de transformação com exemplos de código antes/depois
- A Fase 2 deve pausar e pedir confirmação antes de modificar qualquer arquivo
- A Fase 3 deve validar o resultado (boot da aplicação + endpoints funcionando)

### 3. Execução da Skill

Execute sua skill nos 3 projetos e valide que ela funciona em todas as stacks.

#### Projeto 1 — code-smells-project (Python/Flask)

Invocar a skill no Claude Code:

```bash
claude "/refactor-arch"
```

> **Nota:** O comando acima é o exemplo com Claude Code. Se você estiver usando Gemini CLI ou Codex, utilize o comando equivalente para invocar uma skill na sua ferramenta.

- Verificar que a Fase 1 detecta corretamente a stack e imprime o resumo
- Verificar que a Fase 2 encontra no mínimo 5 dos problemas documentados na sua análise manual
- Confirmar a execução da Fase 3
- Verificar que a Fase 3:
  - Cria a estrutura de diretórios baseada em MVC
  - A aplicação inicia sem erros
  - Os endpoints originais continuam respondendo
- Salvar o relatório de auditoria (output da Fase 2) em `reports/audit-project-1.md`
- Commitar o código refatorado do projeto no repositório

#### Projeto 2 — ecommerce-api-legacy (Node.js/Express)

Prove que sua skill é reutilizável em outro projeto de backend, mas com stack diferente.

- Copiar a pasta `.claude/skills/refactor-arch/` para dentro de `ecommerce-api-legacy/`
- Invocar a skill:

```bash
cd ../ecommerce-api-legacy
claude "/refactor-arch"
```

- Verificar que as 3 fases executam corretamente neste projeto
- Salvar o relatório em `reports/audit-project-2.md`
- Commitar o código refatorado do projeto no repositório

#### Projeto 3 — task-manager-api (Python/Flask)

Agora o teste com um projeto Python/Flask que já possui alguma organização de camadas (models, routes, services, utils).

- Copiar a pasta `.claude/skills/refactor-arch/` para dentro de `task-manager-api/`
- Invocar a skill:

```bash
cd ../task-manager-api
claude "/refactor-arch"
```

- Verificar que:
  - A Fase 1 detecta corretamente Python/Flask como stack e identifica o domínio de Task Manager
  - A Fase 2 identifica problemas mesmo em um projeto parcialmente organizado
  - A Fase 3 melhora a estrutura sem quebrar a aplicação (todos os endpoints devem continuar respondendo)
- Salvar o relatório em `reports/audit-project-3.md`
- Commitar o código refatorado do projeto no repositório

> **Nota:** Este projeto já possui alguma separação de camadas, mas isso não significa que a arquitetura está adequada. A skill deve identificar tanto problemas de código (segurança, performance, qualidade) quanto oportunidades de melhoria arquitetural. Se houver mudanças estruturais necessárias, a skill deve propô-las e executá-las.

#### Validação

Para cada projeto refatorado, valide o seguinte checklist:

```markdown
## Checklist de Validação

### Fase 1 — Análise
- [ ] Linguagem detectada corretamente
- [ ] Framework detectado corretamente
- [ ] Domínio da aplicação descrito corretamente
- [ ] Número de arquivos analisados condiz com a realidade

### Fase 2 — Auditoria
- [ ] Relatório segue o template definido nos arquivos de referência
- [ ] Cada finding tem arquivo e linhas exatos
- [ ] Findings ordenados por severidade (CRITICAL → LOW)
- [ ] Mínimo de 5 findings identificados
- [ ] Detecção de APIs deprecated incluída (se aplicável)
- [ ] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [ ] Estrutura de diretórios segue padrão MVC
- [ ] Configuração extraída para módulo de config (sem hardcoded)
- [ ] Models criados para abstrair dados
- [ ] Views/Routes separadas para visualização ou roteamento
- [ ] Controllers concentram o fluxo da aplicação
- [ ] Error handling centralizado
- [ ] Entry point claro
- [ ] Aplicação inicia sem erros
- [ ] Endpoints originais respondem corretamente
```

> **Dica:** Se a skill não detectou problemas suficientes ou a refatoração falhou, ajuste os arquivos de referência e execute novamente. É normal precisar de 2-4 iterações.

## Entregável

Repositório público no GitHub (fork do repositório base) contendo:

- Skill completa em `.claude/skills/refactor-arch/` (dentro dos 3 projetos)
- Código refatorado dos 3 projetos (resultado da execução da Fase 3, commitado no repositório)
- Relatórios de auditoria em `reports/` (3 arquivos)
- `README.md` atualizado

### Estrutura do repositório

Faça um fork do repositório base contendo os três projetos com code smells.

> **Nota:** A estrutura abaixo usa Claude Code como exemplo (`.claude/skills/`). Se estiver usando outra ferramenta, adapte os caminhos conforme a convenção dela.

```
desafio-skills/
├── README.md                              # Sua documentação
│
├── code-smells-project/                   # Projeto 1 — Python/Flask (API de E-commerce)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← SUA SKILL AQUI
│   │           ├── SKILL.md
│   │           └── (arquivos de referência)
│   ├── app.py
│   ├── controllers.py
│   ├── models.py
│   ├── database.py
│   └── requirements.txt
│
├── ecommerce-api-legacy/                  # Projeto 2 — Node.js/Express (LMS API com checkout)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── src/
│   │   ├── app.js
│   │   ├── AppManager.js
│   │   └── utils.js
│   ├── api.http
│   └── package.json
│
├── task-manager-api/                      # Projeto 3 — Python/Flask (API de Task Manager)
│   ├── .claude/
│   │   └── skills/
│   │       └── refactor-arch/             # ← CÓPIA DA SKILL
│   │           └── ...
│   ├── app.py
│   ├── database.py
│   ├── seed.py
│   ├── requirements.txt
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
│
└── reports/                               # Relatórios gerados
    ├── audit-project-1.md                 # Saída da Fase 2 no projeto 1
    ├── audit-project-2.md                 # Saída da Fase 2 no projeto 2
    └── audit-project-3.md                 # Saída da Fase 2 no projeto 3
```

**O que você vai criar:**

- `.claude/skills/refactor-arch/` — A skill completa (SKILL.md + arquivos de referência)
- Código refatorado dos 3 projetos — resultado da execução da Fase 3, commitado no repositório
- `reports/audit-project-{1,2,3}.md` — Relatório de auditoria de cada projeto
- `README.md` — Documentação do seu processo

**O que já vem pronto:**

- `code-smells-project/` — API de E-commerce Python/Flask com code smells intencionais
- `ecommerce-api-legacy/` — LMS API Node.js/Express (com fluxo de checkout) e problemas de implementação
- `task-manager-api/` — API de Task Manager Python/Flask com organização parcial e problemas de segurança/qualidade

> **Dica:** Cada projeto contém problemas intencionais de diferentes severidades (CRITICAL, HIGH, MEDIUM, LOW), incluindo falhas de segurança, violações arquiteturais e problemas de qualidade de código. Parte do desafio é identificá-los por conta própria através da análise manual do código.

### README.md deve conter

**A) Seção "Análise Manual":**

- Lista dos problemas identificados manualmente em cada projeto
- Classificação por severidade
- Justificativa de por que cada problema é relevante

**B) Seção "Construção da Skill":**

- Decisões de design: como estruturou o SKILL.md e os arquivos de referência
- Quais anti-patterns incluiu no catálogo e por quê
- Como garantiu que a skill é agnóstica de tecnologia
- Desafios encontrados e como resolveu

**C) Seção "Resultados":**

- Resumo dos relatórios de auditoria dos 3 projetos (quantos findings por severidade em cada)
- Comparação antes/depois da estrutura de cada projeto
- Checklist de validação preenchido para cada projeto
- Screenshots ou logs mostrando as aplicações rodando após refatoração
- Observações sobre como a skill se comportou em stacks diferentes

**D) Seção "Como Executar":**

- Pré-requisitos (a ferramenta escolhida — Claude Code, Gemini CLI ou Codex — instalada e configurada)
- Comandos para executar a skill em cada projeto
- Como validar que a refatoração funcionou

### Ordem de execução sugerida

**1. Analisar os projetos manualmente**

Leia o código dos três projetos e documente os problemas encontrados.

**2. Criar a skill**

Escreva o SKILL.md e os arquivos de referência.

**3. Executar nos 3 projetos**

```bash
# Projeto 1
cd code-smells-project
claude "/refactor-arch"

# Projeto 2
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3
cd ../task-manager-api
claude "/refactor-arch"
```

Salve a saída da Fase 2 de cada projeto em `reports/audit-project-{1,2,3}.md`.

**4. Iterar**

Se a skill não detectou problemas suficientes ou a refatoração falhou, ajuste os arquivos de referência e execute novamente. É normal precisar de 2-4 iterações.

## Critérios de Aceite

A skill deve atingir os seguintes mínimos em **todos os 3 projetos**:

| Critério | Requisito |
|---|---|
| Fase 1 detecta stack corretamente | OBRIGATÓRIO (3/3 projetos) |
| Fase 2 encontra >= 5 findings | OBRIGATÓRIO (3/3 projetos) |
| Fase 2 inclui pelo menos 1 CRITICAL ou HIGH | OBRIGATÓRIO (3/3 projetos) |
| Fase 3 aplicação funciona após refatoração | OBRIGATÓRIO (3/3 projetos) |

**IMPORTANTE:** Todos os critérios devem ser atingidos nos 3 projetos, não apenas em um!

> **Sobre o projeto 3 (task-manager-api):** Este projeto já possui alguma organização. "aplicação funciona" significa que a API inicia sem erros e todos os endpoints continuam respondendo corretamente.

## Referências

- [Claude Code: Skills](https://docs.anthropic.com/en/docs/claude-code/skills) — Documentação oficial sobre como criar e estruturar Skills
- [Claude Code: Overview](https://docs.anthropic.com/en/docs/claude-code/overview) — Visão geral do Claude Code e suas capacidades
- [The Complete Guide to Building Skills for Claude (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) — Guia completo da Anthropic sobre construção de Skills
- [Equipping Agents for the Real World with Agent Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills) — Blog oficial da Anthropic sobre Agent Skills

---

## Dicas Finais

- **Comece pela análise manual** — entender os problemas profundamente é essencial para criar uma skill que os detecte.
- **O SKILL.md é um prompt** — ele instrui o agente sobre o que fazer, enquanto os arquivos de referência fornecem o conhecimento de domínio.
- **Seja específico nos sinais de detecção** — "código ruim" não ajuda; "query SQL dentro de loop for" é acionável.
- **Teste incrementalmente** — não tente criar a skill perfeita de primeira.
- **A skill deve ser copiável** — se ela só funciona em um projeto específico, está acoplada demais. Teste nos 3 projetos para validar.
- **Projetos diferentes exigem adaptação** — a Fase 3 de um projeto já parcialmente organizado não vai ter as mesmas transformações de um monolito. Sua skill deve se adaptar ao contexto.
- **Pedir confirmação na Fase 2 é obrigatório** — o humano deve revisar o relatório antes de qualquer modificação.
- **Consulte as referências do curso** — revise a documentação oficial da ferramenta escolhida e os materiais das aulas para relembrar a estrutura e anatomia de uma skill.