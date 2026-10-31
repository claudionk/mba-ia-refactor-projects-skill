================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Node.js (runtime local v26.8.1; package.json não fixa versão)
Framework:     Express ^4.18.2
Dependencies:  express, sqlite3 ^5.1.6, dotenv ^18.0.9
Domain:        LMS API (com fluxo de checkout) para matrículas, pagamentos e relatório financeiro de cursos
Architecture:  MVC já aplicado em execução anterior da skill — config/, database/, models/, controllers/, routes/, middlewares/, services/, validators/, utils/; entry point src/app.js
Source files:  24 files analyzed
DB:            SQLite (`:memory:` por padrão), SQL raw parametrizado via helpers Promise (run/get/all), sem migrations
================================

================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js + Express
Files:   24 analyzed | ~370 lines of code
Date:    2026-10-30

> Reexecução da skill após o feedback da revisão: a auditoria anterior (2026-10-27) aceitou um
> middleware admin opt-in como correção. Com o AP-17 e o PB-12 adicionados à skill, esse
> middleware passa a ser reportado como finding.

## Summary

CRITICAL: 0 | HIGH: 1 | MEDIUM: 0 | LOW: 2
Total findings: 3

## Findings

### [HIGH] Autenticação admin fail-open: rotas sensíveis abertas na configuração padrão
File: src/middlewares/adminAuth.js:4-9; .env.example:4-5; src/routes/adminRoutes.js:7; src/routes/userRoutes.js:8
Anti-pattern: AP-17 — Endpoint Sensível sem Autenticação / Autenticação Fail-Open
Description: O middleware libera a requisição quando o token não está configurado:
  if (!settings.adminToken) return next();   // adminAuth.js:6
O comentário (linha 4) assume o opt-in "preservando o contrato atual". O `.env.example` sobe com
`ADMIN_TOKEN=` vazio (linha 5), então quem copia o exemplo roda com a proteção desligada. A
comparação usa `!==` (linha 7), sem tempo constante.
Impact: Em uma instalação padrão, qualquer cliente anônimo lê `GET /api/admin/financial-report`
(nomes de alunos e receita) e apaga usuários com `DELETE /api/users/:id`, junto com as matrículas
e os pagamentos deles.
Recommendation: PB-12 — negar por padrão: sem `ADMIN_TOKEN` → 403; header ausente/errado → 401;
comparar com `crypto.timingSafeEqual`; `.env.example` com placeholder não vazio. Documentar a
mudança de contrato em vez de mantê-la aberta.

---

### [LOW] Senha padrão literal para o usuário do seed
File: src/config/settings.js:8; src/database/init.js:12-13
Anti-pattern: AP-02 — Hardcoded Credentials / Secrets (rebaixado para LOW)
Description: `seedUserPassword: process.env.SEED_USER_PASSWORD || 'change-me-seed'`. Sem a
variável, o usuário `leonan@fullcycle.com.br` recebe uma senha conhecida, publicada no repositório.
Severidade rebaixada porque a API não tem rota de login que aceite essa senha hoje.
Impact: A credencial passa a valer assim que surgir um login; o padrão incentiva fallback literal.
Recommendation: Sem `SEED_USER_PASSWORD`, gerar senha aleatória com
`passwordService.generateRandomPassword()` (mesmo critério já usado no checkout).

---

### [LOW] Export não utilizado
File: src/services/passwordService.js:16-21, 25
Anti-pattern: AP-16 — Imports Não Utilizados
Description: `verifyPassword` é exportado, mas nenhum arquivo o usa (não existe login).
Impact: Código morto sem teste; sugere um fluxo de autenticação que não existe.
Recommendation: Remover até existir um consumidor.

================================
Total: 3 findings
CRITICAL: 0 | HIGH: 1 | MEDIUM: 0 | LOW: 2
================================

Deprecated APIs: nenhuma encontrada (sem `crypto.createCipher`, sem `res.send(status, body)`).

Observações fora do catálogo (não entram na contagem):
- Checkout (`checkoutController.js:30-32`) e `deleteUser` (`userController.js:7-9`) fazem várias
  escritas sem transação. Com a conexão SQLite única compartilhada, um `BEGIN` interfere em
  requisições concorrentes; resolver exige conexão por operação ou fila de escrita.
- `PAYMENT_GATEWAY_KEY` é lida em `settings.js:6`, mas o gateway simulado não a usa.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y (autorizado pelo usuário na solicitação de reexecução)

================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
(estrutura MVC mantida; só os arquivos marcados mudaram)

src/
├── app.js
├── constants.js
├── config/settings.js          * sem fallback literal para SEED_USER_PASSWORD
├── database/{connection,init}.js  * init gera senha aleatória para o seed quando não configurada
├── models/                     auditLog, course, enrollment, payment, user
├── controllers/                checkout, report, user
├── routes/                     checkout, admin, user, index
├── middlewares/
│   ├── adminAuth.js            * deny-by-default + crypto.timingSafeEqual
│   └── errorHandler.js
├── services/                   * passwordService sem verifyPassword morto; paymentService
├── validators/checkoutValidator.js
└── utils/                      AppError, logger
.env.example                    * ADMIN_TOKEN com placeholder não vazio

## Issues Resolved
  ✓ AP-17 (HIGH) adminAuth fail-open → PB-12: sem ADMIN_TOKEN responde 403, token ausente/errado 401,
    comparação em tempo constante; .env.example não sobe mais com a credencial vazia
  ✓ AP-02 (LOW) senha literal do seed → senha aleatória quando SEED_USER_PASSWORD não está definida
  ✓ AP-16 (LOW) verifyPassword não utilizado → removido

## Validation
  ✓ Application boots without errors (portas 3071 e 3072)
  ✓ All endpoints respond correctly
      POST /api/checkout aprovado 200 | e-mail já existente 200 | recusado 400 | campos ausentes 400 | curso inexistente 404
      GET  /api/admin/financial-report com token 200, mesmo formato de antes
      DELETE /api/users/1 com token 200; relatório seguinte sem aluno órfão
  ✓ Sensitive endpoints deny by default (no token → 403, wrong → 401, valid → 200)
      | Rota                          | sem ADMIN_TOKEN | header ausente | token errado | token certo |
      |-------------------------------|-----------------|----------------|--------------|-------------|
      | GET /api/admin/financial-report | 403           | 401            | 401          | 200         |
      | DELETE /api/users/:id           | 403           | 401            | 401          | 200         |
      adminAuth.js relido: nenhum caminho chama next() sem credencial configurada.
  ✓ Zero CRITICAL/HIGH anti-patterns remaining

Mudança de contrato (intencional, exigida pelo AP-17):
- GET /api/admin/financial-report e DELETE /api/users/:id exigem o header x-admin-token.
  Sem ADMIN_TOKEN no servidor, respondem 403. api.http já envia o header.
Fora do escopo (observações, não findings): escritas sem transação no checkout/delete e
PAYMENT_GATEWAY_KEY ainda não consumida pelo gateway simulado.
================================
