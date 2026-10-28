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
File: routes/task_routes.py:30-39,71-80,283-287 | routes/user_routes.py:171-180 | routes/report_routes.py:34-43,132-135 | routes/task_routes.py:16-28 vs routes/user_routes.py:162-169 | routes/task_routes.py:96-144 vs 166-213 vs utils/helpers.py:57-108
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

### [HIGH] Autenticacao Falsa / Sem Autorização
File: routes/user_routes.py:207-211, 71-78
Anti-pattern: AP-08 — Informações sensíveis / segurança no response (mais próximo no catálogo)
Description: `/login` retorna `'token': 'fake-jwt-token-' + str(user.id)`, token
previsível que nenhum endpoint valida. Todos os endpoints são públicos e `POST /users`
aceita `role: 'admin'` de qualquer cliente.
Impact: Qualquer um pode criar admin, listar/editar/deletar usuários e tasks.
Recommendation: No escopo desta refatoração, manter o contrato do token, mas isolar a
geração em um módulo de auth e documentar a limitação; Autenticacao real (JWT) fica
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
Impact: Ruído e dependências desnecessarias.
Recommendation: Remover imports e código morto (ou integrá-lo, como `is_overdue`).

---

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
