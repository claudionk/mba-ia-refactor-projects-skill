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
Recommendation: Mover para variáveis de ambiente lidas em `config/settings.js` (com `.env.example`), sem valores sensíveis no código; remover chaves não utilizadas (dbUser, dbPass, smtpUser).

---

### [CRITICAL] Senha com Hash Inseguro / Senha Padrão
File: src/utils.js:17-23 (usado em src/AppManager.js:68; seed em src/AppManager.js:18)
Anti-pattern: AP-04 — Senha em Texto Puro / Hash Inseguro
Description: `badCrypto` é um pseudo-hash: concatena 10.000 vezes os 2 primeiros caracteres do base64 da senha e devolve `substring(0, 10)`. Isso é determinístico, sem salt, e na prática revela os 2 primeiros caracteres repetidos (colisões massivas entre senhas distintas). Além disso, `badCrypto(p || "123456")` atribui uma senha padrão previsível quando `pwd` não é enviado, e o seed insere `pass = '123'` em texto puro (linha 18). O loop de 10.000 iterações também bloqueia o event loop a cada novo usuário.
Impact: Senhas de usuários são triviais de quebrar/colidir; contas criadas sem senha ficam com "123456".
Recommendation: Usar hash com salt (`crypto.scrypt`/`bcrypt`) em um serviço de senha; exigir `pwd` ou gerar token aleatório; fazer hash também do seed.

---

### [HIGH] God Class / God File
File: src/AppManager.js:4-139
Anti-pattern: AP-05 — God Class / God File
Description: `AppManager` acumula criação de conexão, DDL e seed (`initDb`), registro de rotas HTTP (`setupRoutes`), regras de negócio de checkout, simulação de gateway de pagamento, geração de relatório e acesso a dados.
Impact: Impossível testar ou evoluir qualquer parte isoladamente; toda mudança toca o mesmo arquivo.
Recommendation: Separar em `config/`, `models/` (User, Course, Enrollment, Payment, AuditLog), `controllers/`, `routes/` e `middlewares/`.

---

### [HIGH] Lógica de Negócio em Route Handler
File: src/AppManager.js:28-78, 80-129, 131-137
Anti-pattern: AP-06 — Lógica de Negócio em Route Handler
Description: O handler de `POST /api/checkout` (~50 linhas) valida entrada, consulta curso e usuário, cria usuário, decide aprovação do cartão (`cc.startsWith("4")`), grava matrícula, pagamento e auditoria e atualiza cache, com callbacks aninhados em 5 níveis. `GET /api/admin/financial-report` calcula receita e monta o relatório dentro da rota, e `DELETE /api/users/:id` executa SQL direto.
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
Recommendation: Adicionar middleware de autenticação/autorização para rotas admin. Obs.: isso altera o contrato das rotas; será tratado na Fase 3 apenas como middleware opt-in (via variável de ambiente) para preservar os contratos existentes.

---

### [MEDIUM] N+1 Query Problem
File: src/AppManager.js:83-126
Anti-pattern: AP-09 — N+1 Query Problem
Description: Para cada curso roda uma query de matrículas; para cada matrícula, uma de usuário e uma de pagamento (3 níveis de queries em loop). A ordem do relatório também fica não determinística (`report.push` na ordem em que os callbacks terminam).
Impact: Número de queries cresce com cursos × matrículas; latência alta e ordem instável.
Recommendation: Uma única query com JOIN (courses ⟕ enrollments ⟕ users ⟕ payments) e agregação em memória, com `ORDER BY`.

---

### [MEDIUM] Ausência de Validação de Entrada
File: src/AppManager.js:29-35, 131-133
Anti-pattern: AP-11 — Ausência de Validação de Entrada
Description: Checkout só testa presença (`!u || !e || !cid || !cc`); não valida formato de e-mail, tipo de `c_id` ou formato do cartão. `req.body` indefinido gera exceção se o JSON for inválido; `:id` do DELETE é usado sem validação.
Impact: Dados inválidos persistidos; erros 500 evitáveis.
Recommendation: Criar validadores (`validators/`) para checkout e id numérico, retornando 400 com mensagem clara.

---

### [MEDIUM] Exceções/Erros Ignorados
File: src/AppManager.js:57-61, 92-94, 104-106, 133-135
Anti-pattern: AP-12 — Bare Except / Swallowed Exceptions
Description: O `err` do INSERT de `audit_logs` (57) é ignorado; em 92 `enrollments` é usado sem checar `err` (TypeError se a query falhar); em 104/106 os erros de user/payment são descartados; o DELETE (133) responde sucesso mesmo com `err`.
Impact: Falhas silenciosas, respostas de sucesso incorretas e possível crash do processo.
Recommendation: Tratar todos os erros, propagar para um middleware de error handling central e logar.

---

### [MEDIUM] Estado Global Mutável
File: src/utils.js:9-15, 25
Anti-pattern: AP-10 — Estado Global Mutável
Description: `globalCache` é um objeto de módulo escrito por `logAndCache` a cada checkout (nunca lido, nunca expira); `totalRevenue` é variável global exportada e não usada.
Impact: Vazamento de memória crescente e estado compartilhado entre requisições.
Recommendation: Remover o cache morto ou encapsular em um módulo de cache com TTL/limite; remover `totalRevenue`.

---

### [MEDIUM] Integridade Referencial: Delete sem Cascata
File: src/AppManager.js:131-137
Anti-pattern: Fora do catálogo (mais próximo de AP-06 — acesso direto a banco em handler)
Description: `DELETE /api/users/:id` apaga só o usuário; a própria mensagem admite: "as matrículas e pagamentos ficaram sujos no banco". Não há FKs no DDL (linhas 12-16).
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
Description: `totalRevenue` é importado em AppManager mas nunca usado; `globalCache`, `totalRevenue` e as chaves `dbUser`, `dbPass`, `smtpUser` do config nunca são consumidos.
Impact: Ruído e superfície de configuração morta.
Recommendation: Remover.

================================
Total: 15 findings
CRITICAL: 2 | HIGH: 4 | MEDIUM: 5 | LOW: 4
================================

Deprecated APIs: nenhuma encontrada (sem `crypto.createCipher`, sem `res.send(status, body)`).

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
>
