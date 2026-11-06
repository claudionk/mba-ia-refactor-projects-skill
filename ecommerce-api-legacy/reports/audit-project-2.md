================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Node.js (versão não especificada no package.json; runtime local v26.8.1)
Framework:     Express ^4.18.2
Dependencies:  express, sqlite3 ^5.1.6
Domain:        LMS API com fluxo de checkout, matrículas, pagamentos e relatório financeiro de cursos
Architecture:  Monolítica sem camadas: AppManager.js concentra schema, seed, rotas, regras de negócio e SQL; utils.js mistura config, cache global e "crypto"
Source files:  3 files analyzed
DB:            SQLite em memória (`:memory:`), SQL raw via callbacks, sem migrations
================================

================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js + Express
Files:   3 analyzed | ~180 lines of code
Date:    2026-11-06

> Reexecução a partir do código original (commit 6d1ce62). A execução de 2026-10-30 rodou sobre o
> código já refatorado e por isso ficou com 3 findings. Os comportamentos citados como "executado"
> foram observados rodando o código original sem alterações.

## Summary

CRITICAL: 3 | HIGH: 5 | MEDIUM: 4 | LOW: 4
Total findings: 16

## Findings

### [CRITICAL] Hardcoded Credentials / Secrets
File: src/utils.js:1-7
Anti-pattern: AP-02 — Hardcoded Credentials / Secrets
Description: O objeto `config` versiona credenciais literais:
  dbUser: "admin_master", dbPass: "senha_super_secreta_prod_123"
  paymentGatewayKey: "pk_live_1234567890abcdef", smtpUser: "no-reply@fullcycle.com.br"
Impact: Quem lê o repositório obtém a chave live do gateway e a senha do banco; trocar qualquer uma exige novo deploy.
Recommendation:
  (1) Remover o objeto `config` de utils.js.
  (2) Ler `PORT` e `PAYMENT_GATEWAY_KEY` de `process.env` em `src/config/settings.js`, sem fallback literal para segredos.
  (3) Eliminar `dbUser`, `dbPass` e `smtpUser`, que nenhum código consome.
  (4) Criar `.env.example` sem valores reais.

---

### [CRITICAL] Credencial de seed: usuário criado com senha literal
File: src/AppManager.js:18
Anti-pattern: AP-02 — Hardcoded Credentials / Secrets (sinal "credencial de seed")
Description: O boot cria uma conta real com a senha publicada no repositório e gravada em texto puro:
  INSERT INTO users (name, email, pass) VALUES ('Leonan', 'leonan@fullcycle.com.br', '123')
A matrícula e o pagamento do seed (linhas 20-21) dependem desse usuário. Hoje não há rota de login, mas o catálogo classifica este caso como CRITICAL mesmo assim.
Impact: A credencial passa a valer assim que surgir um login, e o e-mail real fica associado a uma senha pública.
Recommendation (PB-13):
  (1) Remover a senha literal do seed.
  (2) Como a conta é exigida por integridade de dados, gravar o hash de uma senha aleatória gerada no seed.
  (3) Não usar variável com fallback literal; a senha não é logada nem retornada.
  (4) Não aplicar hash a um valor conhecido, pois isso não corrige o finding.

---

### [CRITICAL] Hash inseguro e senha padrão previsível
File: src/utils.js:17-23; src/AppManager.js:68
Anti-pattern: AP-04 — Senha em Texto Puro / Hash Inseguro
Description: `badCrypto` repete 10.000 vezes os 2 primeiros caracteres do base64 da senha e devolve os 10 primeiros, logo não tem salt e só depende do início da senha. Além disso, `badCrypto(p || "123456")` atribui uma senha conhecida a quem faz checkout sem `pwd`.
Impact: Senhas diferentes que começam igual geram o mesmo "hash", e a parte inicial da senha é recuperável por decodificação. Contas sem `pwd` ficam todas com a mesma senha.
Recommendation:
  (1) Criar `src/services/passwordService.js` com `crypto.scrypt` e salt aleatório por senha.
  (2) Remover `badCrypto`.
  (3) Sem `pwd`, gerar senha aleatória em vez de `"123456"`.

---

### [HIGH] Endpoints administrativos e destrutivos sem autenticação
File: src/AppManager.js:80, 131
Anti-pattern: AP-17 — Endpoint Sensível sem Autenticação / Autenticação Fail-Open
Description: `GET /api/admin/financial-report` e `DELETE /api/users/:id` não verificam credencial alguma. Executado: ambos responderam 200 a um cliente anônimo.
Impact: Qualquer cliente lê nomes de alunos e receita, e apaga usuários.
Recommendation (PB-12):
  (1) Criar o middleware `adminAuth` deny-by-default e aplicá-lo às duas rotas.
  (2) Sem `ADMIN_TOKEN` no servidor → 403.
  (3) Header `x-admin-token` ausente ou errado → 401.
  (4) Comparar com `crypto.timingSafeEqual`.
  (5) `.env.example` com placeholder não vazio; atualizar `api.http` para enviar o header.

---

### [HIGH] Requisição anônima derruba o servidor (entrada sem validação)
File: src/AppManager.js:29-35, 46, 68, 132
Anti-pattern: AP-11 — Ausência de Validação de Entrada (elevado de MEDIUM para HIGH pelo impacto)
Description: O checkout só testa presença de campos. Executado: `card: 123` lança `TypeError: cc.startsWith is not a function` (linha 46) e `pwd: 123` lança `ERR_INVALID_ARG_TYPE` (linha 68). As exceções ocorrem dentro de callbacks do sqlite3, fora do alcance do Express, e o processo termina com código 1. E-mail, `c_id` e `:id` do DELETE também não são validados.
Impact: Uma única requisição sem credencial derruba a API para todos. Como o banco é `:memory:`, os dados também se perdem.
Recommendation:
  (1) Criar `src/validators/checkoutValidator.js`, validando tipo de `usr`, `eml`, `pwd`, `card`, formato de e-mail e `c_id` inteiro.
  (2) Validar `:id` como inteiro positivo.
  (3) Responder 400 "Bad Request" em entrada inválida.

---

### [HIGH] God Class
File: src/AppManager.js:4-139
Anti-pattern: AP-05 — God Class / God File
Description: `AppManager` acumula conexão, DDL, seed, registro de rotas, regras de checkout, simulação de gateway, relatório e SQL.
Impact: Nenhuma parte pode ser testada ou alterada isoladamente; toda mudança toca o mesmo arquivo.
Recommendation:
  (1) Separar em `config/`, `database/`, `models/` (user, course, enrollment, payment, auditLog), `controllers/`, `routes/`, `middlewares/` e `services/`.
  (2) Remover `AppManager.js` e `utils.js`.

---

### [HIGH] Lógica de negócio em route handlers
File: src/AppManager.js:28-78, 80-129, 131-137
Anti-pattern: AP-06 — Lógica de Negócio em Route Handler
Description: `POST /api/checkout` tem 50 linhas e 5 níveis de callback, e decide aprovação do cartão (`cc.startsWith("4")`) dentro da rota. O relatório calcula receita no handler e o DELETE executa SQL direto.
Impact: Regra acoplada a HTTP e SQL, e tratamento de erro difícil de acertar, como mostra o finding de queda do servidor.
Recommendation:
  (1) Criar controllers de checkout, relatório e usuário com async/await.
  (2) Mover a decisão de pagamento para `services/paymentService.js`.
  (3) Deixar SQL só nos models e, nas rotas, só o mapeamento URL → controller.

---

### [HIGH] Cartão completo e chave do gateway no log
File: src/AppManager.js:45
Anti-pattern: AP-08 — Debug Mode em Produção / Informações Sensíveis no Response
Description: Executado: o log mostrou `Processando cartão 4111222233334444 na chave pk_live_1234567890abcdef`.
Impact: Dados de cartão e chave live em qualquer agregador de logs, o que viola PCI-DSS.
Recommendation:
  (1) Nunca logar a chave.
  (2) Logar no máximo os 4 últimos dígitos mascarados do cartão.

---

### [MEDIUM] N+1 Query Problem
File: src/AppManager.js:83-126
Anti-pattern: AP-09 — N+1 Query Problem
Description: Uma query de matrículas por curso e, para cada matrícula, uma de usuário e uma de pagamento. Executado: a ordem do relatório depende de qual callback termina antes (`Docker` saiu antes de `Clean Architecture`, com id menor).
Impact: Queries crescem com cursos × matrículas e a ordem da resposta é instável.
Recommendation: Query única com JOIN e `ORDER BY`, agregando em memória.

---

### [MEDIUM] Erros ignorados
File: src/AppManager.js:38, 57, 92-93, 104, 106, 133-135
Anti-pattern: AP-12 — Bare Except / Swallowed Exceptions
Description: Falha de banco em 38 vira 404. O `err` da auditoria (57) é ignorado. Em 92-93, `enrollments.length` é lido sem checar `err`. Erros de usuário e pagamento (104, 106) são descartados. O DELETE (133-135) responde 200 mesmo com erro.
Impact: Respostas de sucesso incorretas, falhas sem rastro e possível queda do processo.
Recommendation: Propagar todos os erros para um middleware central que loga e responde 500 genérico.

---

### [MEDIUM] Estado global mutável
File: src/utils.js:9-15, 25; src/AppManager.js:59
Anti-pattern: AP-10 — Estado Global Mutável
Description: `globalCache` recebe uma chave por usuário a cada checkout, nunca é lido e nunca expira. `totalRevenue` é exportado e não é usado.
Impact: Memória cresce sem limite e sem benefício.
Recommendation: Remover `globalCache`, `logAndCache` e `totalRevenue`.

---

### [MEDIUM] DELETE deixa matrículas e pagamentos órfãos
File: src/AppManager.js:131-137
Anti-pattern: Fora do catálogo (mais próximo de AP-06)
Description: Só a linha de `users` é apagada, e a própria resposta admite o problema. Executado: depois do DELETE o relatório mostra `{"student":"Unknown","paid":997}`.
Impact: Dados órfãos distorcem o relatório financeiro.
Recommendation: Apagar também pagamentos e matrículas do usuário e ajustar a mensagem, mantendo o status 200.

---

### [LOW] console.log para logging
File: src/app.js:13; src/AppManager.js:45; src/utils.js:13
Anti-pattern: AP-13 — Print / Console.log para Logging
Description: Logs ad-hoc, sem nível nem estrutura.
Impact: Difícil filtrar em produção, e já misturou dados sensíveis ao log.
Recommendation: Módulo `utils/logger.js` com níveis, usado em toda a aplicação.

---

### [LOW] Magic numbers e strings
File: src/AppManager.js:46, 48, 108; src/utils.js:6, 19-22
Anti-pattern: AP-14 — Magic Numbers / Magic Strings
Description: `"PAID"`/`"DENIED"` literais, regra `startsWith("4")`, porta `3000`, `10000`, `substring(0, 2)` e `substring(0, 10)`.
Impact: Erros de digitação silenciosos e regras difíceis de localizar.
Recommendation: Constantes `PAYMENT_STATUS` e `APPROVED_CARD_PREFIX`; porta vinda de `settings`.

---

### [LOW] Nomes sem semântica
File: src/AppManager.js:29-33, 52, 89, 102
Anti-pattern: AP-15 — Nomes de Variáveis Sem Semântica
Description: `u`, `e`, `p`, `cid`, `cc`, `c`, `enr`, `enrId`.
Impact: Leitura difícil. Os campos do payload (`usr`, `eml`, `pwd`, `c_id`) são contrato público e devem ser mantidos.
Recommendation: `name`, `email`, `password`, `courseId`, `cardNumber` internamente, mapeados no validator.

---

### [LOW] Imports e exports não utilizados
File: src/AppManager.js:2; src/utils.js:2-3, 5, 25
Anti-pattern: AP-16 — Imports Não Utilizados
Description: `totalRevenue` é importado e não é usado. `globalCache`, `totalRevenue`, `dbUser`, `dbPass` e `smtpUser` não têm consumidor.
Impact: Ruído e superfície de configuração morta.
Recommendation: Remover.

================================
Total: 16 findings
CRITICAL: 3 | HIGH: 5 | MEDIUM: 4 | LOW: 4
================================

Deprecated APIs: nenhuma encontrada (sem `crypto.createCipher`, sem `res.send(status, body)`).

Observações fora do catálogo (não entram na contagem):
- A chave `pk_live_` e a senha continuam no histórico do git mesmo depois da refatoração. Se fossem reais, precisariam ser trocadas no gateway e no banco.
- Checkout (linhas 50-61) e DELETE fazem várias escritas sem transação. Com a conexão SQLite única, um `BEGIN` interfere em requisições concorrentes.
- Pagamento recusado deixa o usuário criado, pois o INSERT (linha 69) ocorre antes da decisão (linha 46).
- Checkout com e-mail existente matricula aquele usuário sem conferir `pwd`.
- O gateway é simulado: `PAYMENT_GATEWAY_KEY` não tem uso além do log removido.

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y (respondido pelo usuário em 2026-11-06, após ver o relatório)

================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure

src/
├── app.js                      entry point
├── constants.js                PAYMENT_STATUS, APPROVED_CARD_PREFIX
├── config/settings.js          lê process.env, sem segredos no código
├── database/
│   ├── connection.js           sqlite com helpers run/get/all em Promise
│   └── init.js                 schema + seed; conta do seed com senha aleatória
├── models/                     user, course, enrollment, payment, auditLog
├── controllers/                checkout, report, user
├── routes/                     checkout, admin, user, index
├── middlewares/                adminAuth (deny-by-default), errorHandler
├── services/                   passwordService (scrypt + salt), paymentService
├── validators/checkoutValidator.js
└── utils/                      logger, AppError
.env.example
Removidos: src/AppManager.js e src/utils.js.

A estrutura MVC reaproveita a da entrega anterior (b8a64df), que já atendia aos findings. Foram alterados `database/init.js`, `config/settings.js`, `validators/checkoutValidator.js`, `.env.example` e `README.md`.

## Issues Resolved
  ✓ CRITICAL: AP-02 secrets, AP-02 credencial de seed, AP-04 hash e senha padrão
  ✓ HIGH: AP-17, AP-11 (queda do servidor), AP-05, AP-06, AP-08
  ✓ MEDIUM: AP-09, AP-12, AP-10, DELETE sem cascata
  ✓ LOW: AP-13, AP-14, AP-15, AP-16

## Recommendation Coverage (CRITICAL/HIGH)
  AP-02 secrets
    (1) config removido → src/utils.js não existe mais
    (2) process.env sem fallback de segredo → src/config/settings.js:4-7
    (3) dbUser/dbPass/smtpUser eliminados → busca sem ocorrências em src/
    (4) .env.example sem valores reais → .env.example:1-5
  AP-02 credencial de seed (PB-13)
    (1) senha literal removida → src/database/init.js:12-13; busca por '123' sem ocorrências
    (2) hash de senha aleatória → src/database/init.js:12; teste: hash muda a cada boot
    (3) sem variável nem fallback → SEED_USER_PASSWORD removida; a senha não aparece em log nem em resposta
    (4) sem hash de valor conhecido → teste: '123', '123456' e 'change-me-seed' não abrem a conta
  AP-04 hash e senha padrão
    (1) scrypt + salt → src/services/passwordService.js:6-14
    (2) badCrypto removido → busca sem ocorrências em src/
    (3) sem pwd, senha aleatória → src/controllers/checkoutController.js:16; teste: checkout sem pwd → 200
  AP-17 (PB-12)
    (1) adminAuth nas 2 rotas → src/routes/adminRoutes.js:7; src/routes/userRoutes.js:8
    (2) sem ADMIN_TOKEN → 403 → src/middlewares/adminAuth.js:13-15; teste abaixo
    (3) header ausente/errado → 401 → src/middlewares/adminAuth.js:16-18; teste abaixo
    (4) tempo constante → src/middlewares/adminAuth.js:8
    (5) placeholder e header → .env.example:5; api.http:29, 33
  AP-11 queda do servidor
    (1) validator → src/validators/checkoutValidator.js:10-22
    (2) :id inteiro positivo → src/validators/checkoutValidator.js:24-27
    (3) 400 em entrada inválida → teste: 9 entradas → 400; processo continua vivo
  AP-05 God Class
    (1) camadas separadas → árvore acima
    (2) AppManager.js e utils.js removidos
  AP-06 lógica em handlers
    (1) controllers async/await → src/controllers/
    (2) decisão de pagamento → src/services/paymentService.js:4-6
    (3) SQL só nos models → src/models/; DDL e seed em src/database/init.js
  AP-08 log sensível
    (1) chave não é logada e (2) cartão mascarado → src/controllers/checkoutController.js:27; teste: nenhum segredo no log

## Validation (aplicação real, portas 3101-3104)
  ✓ Application boots without errors
  ✓ All endpoints respond correctly (mesmos status e corpos da linha de base do original)
      POST /api/checkout: aprovado 200 | e-mail existente 200 | sem pwd 200 | c_id string 200
                          recusado 400 | sem campos 400 | curso inexistente 404
      GET /api/admin/financial-report: 200, agora com ordem estável
      DELETE /api/users/1: 200; o relatório seguinte não tem aluno "Unknown"
  ✓ Sensitive endpoints deny by default (no token → 403, wrong → 401, valid → 200)
      | Rota                            | sem ADMIN_TOKEN | header ausente | token errado | token certo |
      |---------------------------------|-----------------|----------------|--------------|-------------|
      | GET /api/admin/financial-report | 403             | 401            | 401          | 200         |
      | DELETE /api/users/:id           | 403             | 401            | 401          | 200         |
      adminAuth.js relido: nenhum caminho chama next() sem credencial configurada.
  ✓ No seed credentials (PB-13)
      Senhas do relatório: nenhuma ocorrência em src/, .env.example e api.http.
      Conta do seed: hash diferente a cada boot; nenhuma senha conhecida a abre.
      Conta admin e comando de setup: não se aplicam, pois o projeto não tem usuário admin nem login.
  ✓ Every CRITICAL/HIGH recommendation applied in full (cobertura acima)
  ✓ Zero CRITICAL/HIGH anti-patterns remaining

Mudanças de contrato (intencionais):
- GET /api/admin/financial-report e DELETE /api/users/:id exigem o header x-admin-token (AP-17).
- A mensagem do DELETE mudou para "Usuário deletado junto com suas matrículas e pagamentos."; o status continua 200.
- Entradas de tipo inválido, que derrubavam o processo, agora recebem 400.
- E-mail inválido e c_id não inteiro positivo agora recebem 400.
- A API lê a configuração de variáveis de ambiente; sem PORT, usa 3000.

Permanecem como observações, fora dos findings: as listadas ao final da Fase 2.
================================
