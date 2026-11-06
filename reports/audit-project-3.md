================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python (versão não especificada; runtime local CPython 3.14)
Framework:     Flask 3.0.0
Dependencies:  flask-sqlalchemy 3.1.1, flask-cors 4.0.0, marshmallow, requests, python-dotenv
Domain:        Task Manager API para criação, atribuição e acompanhamento de tarefas, com usuários, categorias e relatórios
Architecture:  Parcialmente organizada: models/, routes/, services/ e utils/ existem, mas a lógica de negócio está nas routes e falta a camada Controller
Source files:  15 files analyzed
DB:            SQLite (sqlite:///tasks.db) via ORM Flask-SQLAlchemy, sem migrations
================================

================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask
Files:   15 analyzed | ~1158 lines of code
Date:    2026-11-06

> Reexecução a partir do código original (commit 6d1ce62). Os comportamentos citados como "executado"
> foram observados rodando o código original sem alterações.

## Summary

CRITICAL: 4 | HIGH: 5 | MEDIUM: 3 | LOW: 5
Total findings: 17

## Findings

### [CRITICAL] Hardcoded Credentials / Secrets
File: app.py:11, 13; services/notification_service.py:7-10
Anti-pattern: AP-02 — Hardcoded Credentials / Secrets
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` (app.py:13) e `self.email_password = 'senha123'` com `self.email_user = 'taskmanager@gmail.com'` (notification_service.py:9-10) estão literais no código versionado. A URI do banco (app.py:11) e o host SMTP também são fixos.
Impact: Quem lê o repositório pode assinar dados com a chave da aplicação e usar a conta SMTP; trocar de ambiente exige editar código.
Recommendation:
  (1) Criar `config/settings.py` lendo `SECRET_KEY`, `DATABASE_URL` e `SMTP_*` do ambiente.
  (2) Sem `SECRET_KEY`, ou com o placeholder do exemplo, a aplicação não inicia (PB-12).
  (3) Criar `.env.example` com placeholder não vazio, sem valores reais.

---

### [CRITICAL] Credenciais de seed, incluindo uma conta admin
File: seed.py:19-20, 26, 33
Anti-pattern: AP-02 — Hardcoded Credentials / Secrets (sinal "credencial de seed")
Description: `u1.set_password('1234')` com `u1.role = 'admin'`, além de `'abcd'` e `'pass'`. Executado: `POST /login` com `joao@email.com` / `1234` responde 200 com papel admin.
Impact: A senha do administrador está publicada no repositório.
Recommendation (PB-13):
  (1) Remover as senhas literais do seed.
  (2) Tasks do seed referenciam os 3 usuários: eles recebem senha aleatória e papéis não administrativos.
  (3) Criar o admin por comando de setup com `ADMIN_EMAIL` e `ADMIN_PASSWORD` do ambiente, que falha sem elas.
  (4) Deixar essas variáveis vazias no `.env.example` e retirar as senhas do `api.http`.

---

### [CRITICAL] Senha com hash inseguro e exposta na API
File: models/user.py:21, 27-32
Anti-pattern: AP-04 — Senha em Texto Puro / Hash Inseguro
Description: `set_password` usa `hashlib.md5(pwd.encode()).hexdigest()`, sem salt, e `to_dict()` inclui `'password': self.password`. Executado: `POST /login` e `GET /users/1` devolvem o hash MD5.
Impact: Hashes vazam na API e são quebráveis por rainbow table em segundos.
Recommendation:
  (1) Usar `werkzeug.security.generate_password_hash` e `check_password_hash`.
  (2) Remover `password` do `to_dict()`.
  (3) Migrar hashes MD5 legados no primeiro login válido.

---

### [CRITICAL] Token falso, nenhuma rota autenticada e admin criado por anônimo
File: routes/user_routes.py:52, 71, 119-122, 134, 210; routes/task_routes.py:225; routes/report_routes.py:12, 103, 167, 190, 211
Anti-pattern: AP-17 — Endpoint Sensível sem Autenticação / Autenticação Fail-Open
Description: `/login` devolve `'fake-jwt-token-' + str(user.id)`, previsível e que nenhuma rota valida. Executado sem credencial alguma: `POST /users` com `role: 'admin'` → 201; `DELETE /users/3` → 200; `DELETE /tasks/1` → 200. Severidade CRITICAL porque qualquer cliente apaga todos os dados, um registro por vez.
Impact: Qualquer visitante vira administrador, lê relatórios e dados pessoais, e apaga usuários e tarefas.
Recommendation (PB-12 e PB-14):
  (1) Token assinado com validade; rotas exigem login, exceto `/`, `/health`, `/login` e o cadastro.
  (2) Cadastro público cria apenas `role: user`; outro papel exige admin.
  (3) Usuários: lista só para admin ou manager; leitura e tarefas de um usuário para o próprio ou admin/manager; edição para o próprio ou admin; exclusão e troca de papel só para admin.
  (4) Tasks: escrita para o dono ou admin/manager; atribuir a outro usuário só para admin/manager.
  (5) Categorias: escrita só para admin/manager.
  (6) Relatórios: resumo só para admin/manager; relatório de usuário para o próprio ou admin/manager.

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
File: app.py:34
Anti-pattern: AP-08 — Debug Mode em Produção
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` fixo no código.
Impact: Debugger interativo Werkzeug exposto na rede permite execução remota de código.
Recommendation: Ler `DEBUG`, `HOST`, `PORT` da config/ambiente com default `False`
e host `127.0.0.1`.

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
File: routes/task_routes.py:62,137,204,236 | routes/user_routes.py:130,149 | routes/report_routes.py:186,207,221 | routes/task_routes.py:221 | utils/helpers.py:46,49,88
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
File: app.py:7 | routes/task_routes.py:7 | routes/user_routes.py:6 | routes/report_routes.py:7-8 | models/task.py:3 | utils/helpers.py:2-7,9-55 | services/notification_service.py:4-48
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
Total: 17 findings
CRITICAL: 4 | HIGH: 5 | MEDIUM: 3 | LOW: 5
================================

Deprecated APIs: DEP-01 presente (16 ocorrências, finding acima). `datetime.utcnow()` registrado como LOW.

Observações fora do catálogo (não entram na contagem):
- `MIN_PASSWORD_LENGTH` é 4 no contrato original; aumentar esse mínimo muda o contrato de cadastro.
- `NotificationService` não é chamado por nenhuma rota.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y (respondido pelo usuário em 2026-11-06, após ver o relatório)

================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure

app.py                  entry point e comando create-admin
config/                 settings.py (segredo obrigatório, recusa placeholder) e constants.py
models/                 task_model, user_model, category_model e base (CRUD)
controllers/            task, user, category, report (regras e permissões)
routes/                 task, user, category, report (HTTP)
middlewares/            auth.py (token) e error_handler.py
services/               auth_service.py (token assinado) e notification_service.py
utils/                  errors, permissions, validators, time_utils
tests/test_api.py       contrato, autenticação, autorização, seed e segredos
Removidos: models/user.py, models/task.py, models/category.py e utils/helpers.py.

A estrutura MVC reaproveita a entrega anterior (0ce9e35), que já atendia às recomendações de arquitetura. Esta reexecução acrescentou segredo obrigatório, autorização por dono e papel, seed sem senha conhecida e testes.

## Issues Resolved
  ✓ CRITICAL: AP-02 segredos, AP-02 credenciais de seed, AP-04 hash, AP-17 autenticação e autorização
  ✓ HIGH: DEP-01, AP-06, AP-07, AP-08, AP-05
  ✓ MEDIUM: AP-09, AP-11, AP-12
  ✓ LOW: AP-13, AP-14, AP-15, AP-16, utcnow

## Recommendation Coverage (CRITICAL/HIGH)
  AP-02 segredos
    (1) settings lê do ambiente → config/settings.py:25-42
    (2) sem segredo real não inicia → config/settings.py:10-17; teste: test_aplicacao_nao_inicia_sem_segredo_real
    (3) .env.example com placeholder → .env.example:3
  AP-02 credenciais de seed (PB-13)
    (1) senhas literais removidas → seed.py:26, 33, 40; teste: credenciais antigas → 401
    (2) senha aleatória e sem admin → seed.py:26-27; teste: test_seed_nao_tem_senha_conhecida_nem_admin
    (3) comando de setup → app.py:35-43; controllers/user_controller.py:75-85; teste: test_create_admin_falha_sem_variaveis_e_cria_com_elas
    (4) variáveis vazias no exemplo e api.http sem senhas → .env.example:15-16; api.http:22-23
  AP-04 hash
    (1) PBKDF2 → models/user_model.py:36; (2) sem password no to_dict → models/user_model.py:25-33; (3) migração de MD5 → models/user_model.py:47-52
  AP-17 autenticação e autorização (PB-12, PB-14)
    (1) token assinado e rotas fechadas → services/auth_service.py:13-25; middlewares/auth.py:37-46
    (2) cadastro só com role user → controllers/user_controller.py:64-66
    (3) usuários → controllers/user_controller.py:30, 41, 92, 113, 125, 134
    (4) tasks → controllers/task_controller.py:54, 64, 69, 80
    (5) categorias → controllers/category_controller.py:39, 57, 76
    (6) relatórios → controllers/report_controller.py:18, 72
    Testes: AutenticacaoTest e AutorizacaoTest
  DEP-01 → `db.session.get` em models/base.py:14; busca por query.get( sem ocorrências
  AP-06 → routes/ só faz HTTP; regras em controllers/
  AP-07 → Task.is_overdue e to_dict em models/task_model.py:28, 33; validação única em utils/validators.py:57
  AP-08 → DEBUG e HOST do ambiente, com padrão seguro, em config/settings.py:29-30
  AP-05 → categorias em routes/category_routes.py e controllers/category_controller.py

## Validation (aplicação real; `python -m unittest` e `scripts/verify_clean_clone.py` repetem estes cenários)
  ✓ Application boots without errors
  ✓ All endpoints respond correctly (19 testes, incluindo todas as rotas de leitura e o CRUD de task)
  ✓ Sensitive endpoints deny by default
      | Cenário                                              | Original | Agora |
      |------------------------------------------------------|----------|-------|
      | Cliente anônimo em GET /tasks                        | 200      | 401   |
      | Cadastro anônimo com role admin                      | 201      | 403   |
      | Cliente anônimo em DELETE /users/3 e DELETE /tasks/1 | 200      | 401   |
      | Usuário comum apagando task de outro                 | 200      | 403   |
      | Usuário comum apagando categoria                     | 200      | 403   |
      | Usuário comum lendo /users e /reports/summary        | 200      | 403   |
      | Token 'fake-jwt-token-<id>'                          | aceito   | 401   |
      | Token assinado com o segredo de exemplo (change-me)  | aceito*  | 401   |
      * na entrega anterior; o original nem validava token.
  ✓ No seed credentials (PB-13)
      Login com joao/1234, maria/abcd e pedro/pass → 401. Contas admin criadas pelo seed: 0.
  ✓ Placeholders and forged tokens rejected; owner/role authorization enforced (PB-12, PB-14)
  ✓ Clean clone: README commands work and automated tests pass
      Os testes rodaram também contra o commit anterior e registraram 18 falhas, como esperado.
  ✓ Every CRITICAL/HIGH recommendation applied in full (cobertura acima)
  ✓ Zero CRITICAL/HIGH anti-patterns remaining

Mudanças de contrato (intencionais):
- Rotas passam a exigir `Authorization: Bearer <token>`, exceto `/`, `/health`, `/login` e o cadastro.
- Permissões por dono e papel (matriz no README do projeto).
- `password` não é mais retornado pela API, e o token do login agora é assinado.
- O seed não cria admin nem senhas conhecidas; a conta admin nasce de `flask --app app create-admin`.
- Sem `SECRET_KEY` real, a aplicação não inicia, inclusive em modo DEBUG.
- POST /tasks sem `user_id` atribui a task a quem a criou.
================================
