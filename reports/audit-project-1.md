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
Enviando `email = ' OR 1=1 --`, a query vira `WHERE email = '' OR 1=1 --...` e o trecho da senha é comentado. O `fetchone()` devolve o primeiro usuário, que é o Admin (id 1, tipo admin). Achado por análise estática; payload não executado.
Impact: Login como administrador via `POST /login` sem conhecer a senha.
Recommendation: `cursor.execute("SELECT id, nome, email, tipo, senha FROM usuarios WHERE email = ?", (email,))` e comparar o hash com `check_password_hash` (ver C5).

---

### [CRITICAL] SQL Injection na busca pública de produtos (vazamento de tabelas)
File: models.py:289-297; controllers.py:113-123
Anti-pattern: AP-01 — SQL Injection
Description: `termo` (query string `q`) e `categoria` são concatenados em `nome LIKE '%" + termo + "%'` e `categoria = '...'`. `GET /produtos/busca` não exige autenticação.
Impact: Leitura de qualquer tabela via `UNION SELECT`, incluindo `usuarios.senha`. Exemplo de `q` (sintaxe conferida por análise): `x%') UNION SELECT id,nome,email,senha,tipo,criado_em,NULL,NULL FROM usuarios --`. Os dados saem no campo `dados` da resposta.
Recommendation: `query += " AND (nome LIKE ? OR descricao LIKE ?)"` com parâmetros `(f"%{termo}%", f"%{termo}%")`; mesma correção para `categoria`, `preco_min` e `preco_max`.

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
Impact: Escrita arbitrária no banco e exfiltração por subconsulta. Exemplo: `nome = "x'||(SELECT group_concat(senha) FROM usuarios)||'"` grava as senhas no nome do produto, que sai em `GET /produtos`. O `sqlite3` recusa múltiplos statements, o que limita DROP/DELETE encadeado, mas não subconsultas.
Recommendation: Usar placeholders `?` em todas as chamadas `execute`; converter IDs com `int()` ou validar tipo no controller antes de chegar ao model.

---

### [CRITICAL] Endpoints administrativos sem autenticação: SQL arbitrário e reset total
File: app.py:47-57, 59-78
Anti-pattern: AP-03 — Endpoint de Execução Arbitrária de SQL
Description: `POST /admin/query` executa o campo `sql` do body diretamente com `cursor.execute`. `POST /admin/reset-db` executa `DELETE` em todas as tabelas. Nenhum dos dois verifica autenticação.
Impact: Qualquer cliente pode apagar o banco inteiro, executar UPDATE/DELETE arbitrários e ler senhas com `SELECT ... FROM usuarios`.
Recommendation: Remover `/admin/query` do código de produção. Se necessário, substituir por comando CLI (`flask ...`) executado localmente. Proteger ou remover `/admin/reset-db`.

---

### [CRITICAL] Senhas em texto puro, armazenadas e devolvidas pela API
File: models.py:79-86, 95-102, 110, 126-129; database.py:76-78
Anti-pattern: AP-04 — Senha em Texto Puro / Retorno de senha no payload
Description: `criar_usuario` grava `senha` sem hash (models.py:126-129). `get_todos_usuarios` (79-86) e `get_usuario_por_id` (95-102) incluem `"senha": row["senha"]` no retorno, então `GET /usuarios` e `GET /usuarios/<id>` expõem todas as senhas. O login compara a senha em claro na SQL (110). O seed cria senhas fracas: `admin123`, `123456`, `senha123` (database.py:76-78).
Impact: Qualquer cliente anônimo lista todas as senhas. O vazamento do arquivo `loja.db` expõe todas as credenciais em claro.
Recommendation: Gerar hash com `werkzeug.security.generate_password_hash` (Werkzeug já vem com Flask) em `criar_usuario`; validar com `check_password_hash` no login; remover `senha` de todos os dicts de retorno; redefinir as senhas do seed.

---

### [CRITICAL] Secrets e credenciais hardcoded, incluindo exposição no /health
File: app.py:7; database.py:76; controllers.py:289
Anti-pattern: AP-02 — Hardcoded Credentials / Secrets
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` é literal (app.py:7) e é devolvida em claro por `GET /health` (controllers.py:289). A conta `admin@loja.com` / `admin123` é criada automaticamente no seed (database.py:76).
Impact: Qualquer visitante obtém a SECRET_KEY e pode forjar cookies de sessão assinados. A credencial de admin está pública no repositório.
Recommendation: `app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]` (falhar na inicialização se ausente); remover `secret_key` do `/health`; criar o admin por comando de setup com senha vinda de variável de ambiente, não do seed.

---

### [HIGH] God File: models.py concentra SQL, regra de negócio e serialização
File: models.py:1-314 (destaques: 133-169, 256-262)
Anti-pattern: AP-05 — God Class / God File
Description: `models.py` tem 314 linhas e 18 funções. Além de acesso a dados, contém: cálculo de total e checagem de estoque em `criar_pedido` (133-169); regra de desconto por faixas de faturamento em `relatorio_vendas` (256-262, com limites 10000/5000/1000 e percentuais 0.1/0.05/0.02); composição do relatório e ticket médio.
Impact: Alterar uma regra de desconto exige mexer no módulo de persistência. Não é possível testar a regra sem SQLite. As camadas ficam acopladas.
Recommendation: Mover cálculo de total, validação de estoque e desconto para a camada de regra de negócio; `models` fica só com queries. Detalhes na Fase 3, conforme `04-mvc-guidelines.md`.

---

### [HIGH] Controllers misturam validação, acesso direto ao banco e resposta HTTP
File: controllers.py:24-62, 64-96, 188-220, 264-292
Anti-pattern: AP-06 — Lógica de Negócio em Route Handler
Description: `health_check` (264-292) executa 4 queries SQL direto via `get_db()`, sem passar pelo model. `criar_pedido` (188-220) orquestra validação, persistência e notificações. As linhas 208-210 imprimem "ENVIANDO EMAIL / SMS / PUSH", mas nada é enviado. Regras de domínio (categorias válidas em 52, preço e estoque em 43-46) ficam dentro do handler.
Impact: A regra não pode ser testada sem subir o Flask. O health check fica acoplado ao schema. O log sugere notificações que não existem.
Recommendation: `health_check` chama `models.contar_registros()`; validação em módulo próprio; notificações atrás de uma interface explícita, ou removidas até existirem de verdade.

---

### [HIGH] Duplicação (DRY): serialização, validação e montagem de pedidos
File: models.py:10-21, 31-40, 304-313; models.py:79-86, 95-102; models.py:178-199, 211-231; controllers.py:26-46, 66-90
Anti-pattern: AP-07 — Lógica de Negócio Duplicada
Description: O dict de produto (8 campos) aparece 3 vezes. O dict de usuário aparece 2 vezes. O bloco "monta pedido + itens + nome do produto" é quase idêntico em `get_pedidos_usuario` (178-199) e `get_todos_pedidos` (211-231), cerca de 20 linhas. A validação de nome, preço e estoque está duplicada entre `criar_produto` (26-46) e `atualizar_produto` (66-90), e as duas divergem: a categoria só é validada na criação.
Impact: Uma correção em um lugar não chega aos outros. A divergência já causa um bug: `PUT /produtos/<id>` aceita categoria inválida.
Recommendation: Extrair `_produto_to_dict(row)`, `_usuario_to_dict(row)` e `_montar_pedido(...)` no model; `validar_produto(dados)` compartilhado entre criar e atualizar.

---

### [HIGH] Debug ativo e vazamento de informações internas
File: app.py:8, 78, 88; controllers.py:12, 22, 62, 96, 109, 126, 134, 144, 165, 186, 220, 227, 235, 255, 262, 284-292
Anti-pattern: AP-08 — Debug Mode em Produção / Informações Sensíveis no Response
Description: `app.config["DEBUG"] = True` (app.py:8) e `app.run(host="0.0.0.0", debug=True)` (app.py:88), que expõe o console interativo do Werkzeug na rede. O `/health` devolve `"ambiente": "producao"` junto com `"debug": True`, `"db_path"` e `secret_key` (controllers.py:284-289). Há 17 respostas 500 que devolvem `str(e)` (16 em controllers.py e 1 em app.py:78), o que expõe mensagens internas do SQLite e do Python.
Impact: Estrutura do banco e do código vazada a qualquer cliente. Quem obtiver o PIN do debugger do Werkzeug ganha execução de código no servidor.
Recommendation: `DEBUG` lido de variável de ambiente, com padrão `False`; `host="127.0.0.1"` em desenvolvimento; respostas 500 genéricas com `logger.exception` no servidor; remover campos internos do `/health`.

---

### [HIGH] Ausência de autenticação e autorização (fora do catálogo)
File: app.py:11-26
Anti-pattern: Não catalogado. Extensão de AP-03 e AP-08, anotado aqui.
Description: Nenhuma rota exige token ou sessão. `PUT /produtos/<id>`, `DELETE /produtos/<id>`, `PUT /pedidos/<id>/status` e `POST /usuarios` são públicos. Qualquer cliente altera preço, apaga produto ou cancela pedido de terceiros. O campo `tipo` do usuário não é usado em nenhuma checagem de permissão.
Impact: Qualquer visitante anônimo executa operações administrativas.
Recommendation: Autenticação por token ou sessão e decorator de autorização (`@requer_admin`) nas rotas de escrita; `tipo` verificado no servidor.

---

### [MEDIUM] N+1 Query Problem
File: models.py:177-200, 209-232, 154-156
Anti-pattern: AP-09 — N+1 Query Problem
Description: `get_pedidos_usuario` e `get_todos_pedidos` executam 1 query por pedido (188, 220) e 1 query por item (191-193, 223-225). Com P pedidos e I itens no total, são 1 + P + I queries. Em `criar_pedido`, o preço de cada produto é consultado duas vezes (140-141 e 155-156).
Impact: `GET /pedidos` degrada linearmente. Com 100 pedidos de 3 itens cada, são 401 queries em uma requisição.
Recommendation: Um `JOIN` entre `itens_pedido` e `produtos` em uma query, agrupando em Python. Reutilizar o produto carregado no loop de validação de `criar_pedido`.

---

### [MEDIUM] Estado global mutável: conexão única compartilhada entre requests
File: database.py:4-11, 86; models.py:134-169
Anti-pattern: AP-10 — Estado Global Mutável
Description: `db_connection` é global. Uma única conexão SQLite com `check_same_thread=False` é usada por todas as threads do Flask. A inicialização é lazy e sem lock. `criar_pedido` faz vários INSERT/UPDATE e só commita no fim, sem rollback no erro. Como a conexão é compartilhada, escritas pendentes de uma request são persistidas pelo próximo `commit()` de outra. A checagem de estoque (144) e o UPDATE (164) são separados, sem transação nem lock.
Impact: Pedido parcial gravado por outra request. Overselling sob concorrência, já que dois pedidos podem passar na checagem antes de qualquer um atualizar o estoque.
Recommendation: Conexão por request (com `g` do Flask ou abrir e fechar por operação); `BEGIN IMMEDIATE` em `criar_pedido`; `rollback()` no `except`.

---

### [MEDIUM] Quantidade zero ou negativa aceita em pedidos
File: controllers.py:195-201; models.py:143-166
Anti-pattern: AP-11 — Ausência de Validação de Entrada
Description: `criar_pedido` valida só a presença de `itens` e `usuario_id`. `quantidade` não é validada. Com `quantidade = -100`, a checagem `produto["estoque"] < item["quantidade"]` (144) passa, `total` fica negativo (146) e `estoque - (-100)` aumenta o estoque (164-166).
Impact: Um cliente cria pedido com quantidade negativa, aumenta o estoque sem limite e gera total negativo, distorcendo `relatorio_vendas` (faturamento, desconto e líquido).
Recommendation: Validar `quantidade` como inteiro maior que zero, e `produto_id` como inteiro, antes da persistência.

---

### [MEDIUM] Validação de tipos e de corpo da requisição ausente
File: controllers.py:169-171, 239-240, 113-121, 26-46, 66-90, 153-158
Anti-pattern: AP-11 — Ausência de Validação de Entrada
Description:
  - `login` (169-171) e `atualizar_status_pedido` (239-240) chamam `dados.get(...)` sem checar `None`. Body ausente ou `null` gera `AttributeError` e resposta 500.
  - Corpo JSON malformado também vira 500: o `except Exception` captura o `BadRequest` do Flask.
  - `preco` e `estoque` não são checados como numéricos. Com `"preco": "abc"`, `preco < 0` (43, 87) levanta `TypeError` e resposta 500.
  - `preco_min` e `preco_max` (118-121) são convertidos com `float()` sem tratamento. Valor inválido gera `ValueError` e resposta 500.
  - `email` não tem formato validado (154). `atualizar_produto` não valida categoria (85) nem tamanho de nome.
Impact: Erros 500 onde deveria haver 400. Combinado com H4, as mensagens internas vazam.
Recommendation: Validação centralizada de tipo, formato e obrigatoriedade (função de validação ou biblioteca de schema). Usar `request.get_json(silent=True)` e responder 400 quando o body não for objeto JSON.

---

### [MEDIUM] Exceções capturadas sem log
File: controllers.py:21-22, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 226-227, 234-235, 254-255, 261-262; app.py:77-78
Anti-pattern: AP-12 — Bare Except / Swallowed Exceptions
Description: 13 blocos `except Exception as e` retornam `str(e)` sem `print` nem logging. Outros blocos (`listar_produtos`, `criar_produto`, `criar_pedido`) imprimem a mensagem, mas sem traceback. Falhas em `login` e `criar_usuario` não são registradas.
Impact: Falhas em produção sem rastro. Diagnosticar exige reproduzir o erro.
Recommendation: `logger.exception(...)` no `except` e resposta 500 genérica para o cliente.

---

### [LOW] print() usado como logging
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250; app.py:56, 83-86
Anti-pattern: AP-13 — Print / Console.log para Logging
Description: 19 chamadas `print`. Em 208-210, as mensagens "ENVIANDO EMAIL / SMS / PUSH" dizem que notificações foram enviadas, mas são só prints. Os logs de login (179, 182) gravam o e-mail do usuário em claro.
Impact: Sem níveis e sem rotação. Logs enganosos. Dados pessoais nos logs.
Recommendation: Módulo `logging` com níveis. Substituir as simulações de notificação por uma interface real ou removê-las.

---

### [LOW] Magic numbers e strings
File: models.py:247-262; controllers.py:47-52, 242; database.py:5; app.py:88
Anti-pattern: AP-14 — Magic Numbers / Magic Strings
Description: Faixas de desconto (10000, 5000, 1000) e percentuais (0.1, 0.05, 0.02) inline em `relatorio_vendas`. Status de pedido literais em models.py:247-253 e em lista em controllers.py:242. Limites de nome (2 e 200) em 47 e 49. Lista de categorias em 52, sem constante compartilhada com o seed (database.py:59-69). Caminho `"loja.db"` e porta `5000` literais.
Recommendation: Constantes nomeadas (`FAIXAS_DESCONTO`, `STATUS_PEDIDO`, `CATEGORIAS_VALIDAS`, `DB_PATH`).

---

### [LOW] Nomes sem semântica e sombreamento de built-in
File: controllers.py:14, 56, 64, 98, 136, 160; models.py:24, 54, 65, 89, 187-193, 219-225
Anti-pattern: AP-15 — Nomes de Variáveis Sem Semântica
Description: `id` sombreia o built-in `id()` em 10 funções. `cursor2`, `cursor3`, `prod`, `rows`, `result` e `dados` são genéricos demais.
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
- **Relatório inclui cancelados:** `relatorio_vendas` soma pedidos cancelados no faturamento (`models.py:242-243`) e no ticket médio (`models.py:272`).
- **CORS aberto:** `CORS(app)` (`app.py:9`) libera qualquer origem.
- **Versão de Python não declarada:** `requirements.txt` lista só `flask` e `flask-cors`. O `__pycache__` indica CPython 3.14.

================================
Total: 20 findings
CRITICAL: 6 | HIGH: 5 | MEDIUM: 5 | LOW: 4
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
>
