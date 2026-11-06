# Solução de Criação de Skills — Refatoração Arquitetural Automatizada

Skill `refactor-arch` para o Claude Code: audita um backend legado, pausa para revisão humana e o refatora para MVC, validando o resultado. Foi aplicada a 3 projetos, em 2 stacks.

**Para validar tudo com um comando** (requer Python 3, Node.js e npm):

```bash
python scripts/verify_clean_clone.py
```

O script clona o repositório em uma pasta temporária, instala as dependências do zero, roda os testes de cada projeto e segue os comandos dos READMEs, incluindo tentativas de ataque. O enunciado original está em [`ENUNCIADO.md`](ENUNCIADO.md).

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

## Construção da Skill

### Estrutura da Skill

```
.claude/skills/refactor-arch/
├── SKILL.md                    ← Instruções das 3 fases sequenciais
├── 01-project-analysis.md      ← Heurísticas de detecção de stack e arquitetura
├── 02-antipatterns-catalog.md  ← 17 anti-patterns + 4 deprecated APIs com sinais de detecção
├── 03-report-template.md       ← Template padronizado do relatório de auditoria
├── 04-mvc-guidelines.md        ← Regras MVC: responsabilidades por camada + exemplos
└── 05-refactoring-playbook.md  ← 14 padrões de transformação com código antes/depois
```

### Decisões de Design

**SKILL.md como orquestrador, arquivos de referência como conhecimento:**  
O `SKILL.md` age como um prompt de sistema estruturado que instrui o agente a executar 3 fases em sequência, com pontos de parada explícitos. Os arquivos de referência fornecem o conhecimento de domínio necessário para cada fase, sem misturá-los no arquivo principal — isso mantém o SKILL.md legível e os arquivos de referência focados.

**Por que 17 anti-patterns + 4 deprecated APIs:**  
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
- **Provar em vez de declarar:** as duas primeiras entregas foram reprovadas porque a skill afirmava "zero CRITICAL/HIGH" sem ligar essa frase às recomendações do relatório. A Fase 3 agora exige evidência por ação recomendada, tentativa de ataque e validação em clone limpo. A seção [Iterações](#iterações) conta essa evolução.
- **Callback Hell vs. Async/Await (Node.js):** O projeto usa sqlite3 com callbacks, mas a refatoração ideal usa Promises/async-await. O playbook inclui a transformação completa (PB-05) para não deixar ambiguidade.
- **Projeto 3 parcialmente organizado:** A skill precisa ser útil mesmo quando a estrutura já existe parcialmente. A solução foi fazer a Fase 1 mapear explicitamente o que está certo e o que falta, para a Fase 3 complementar sem destruir o que já está bem.
- **Pausa obrigatória na Fase 2:** A instrução de pausa está em destaque visual no SKILL.md (bloco `⚠️`) e no output da Fase 2, para que o agente não a ignore ao executar sequencialmente.

---

## Resultados

### Resumo dos Relatórios de Auditoria

Todos os relatórios partem do código original (commit `6d1ce62`).

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---|---|---|---|---|---|
| `code-smells-project` | 6 | 5 | 5 | 4 | 20 | [`audit-project-1.md`](reports/audit-project-1.md) |
| `ecommerce-api-legacy` | 3 | 6 | 4 | 4 | 17 | [`audit-project-2.md`](reports/audit-project-2.md) |
| `task-manager-api` | 4 | 5 | 3 | 5 | 17 | [`audit-project-3.md`](reports/audit-project-3.md) |

Os relatórios dos projetos 2 e 3 trazem a saída da Fase 3, com a cobertura de cada recomendação CRITICAL e HIGH. O do projeto 1 traz um adendo com as correções pós-revisão.

### Estrutura Antes/Depois

| Projeto | Antes | Depois |
|---|---|---|
| `code-smells-project` | `app.py`, `controllers.py`, `models.py` e `database.py` na raiz, misturando HTTP, regra de negócio e SQL | `config/`, `models/`, `controllers/`, `routes/`, `middlewares/`, `services/`, `tests/` e `app.py` como entry point |
| `ecommerce-api-legacy` | `src/app.js`, `src/AppManager.js` (God Class) e `src/utils.js` | `src/` com `config/`, `database/`, `models/`, `controllers/`, `routes/`, `middlewares/`, `services/`, `validators/`, `utils/`, além de `tests/` |
| `task-manager-api` | `models/`, `routes/`, `services/` e `utils/`, com a lógica de negócio nas routes e sem controllers | Acrescenta `config/`, `controllers/`, `middlewares/` e `tests/`; as routes ficam só com HTTP |

### Logs de Execução

Saída de `python scripts/verify_clean_clone.py --source https://github.com/claudionk/mba-ia-refactor-projects-skill.git`, contra o repositório público:

```
Clone limpo de https://github.com/claudionk/mba-ia-refactor-projects-skill.git
Commit: 438b55b docs: Preenche Resultados do README e adiciona verificação em clone limpo

== code-smells-project (Python/Flask)
  [PASS] pip install -r requirements.txt
  [PASS] python -m unittest discover -s tests -t . (Ran 16 tests in 5.613s)
  [PASS] com o .env.example sem editar, a aplicação recusa iniciar e explica
  [PASS] flask --app app criar-admin (Admin criado: id=1)
  [PASS] GET /health
  [PASS] GET /produtos
  [PASS] GET /usuarios sem token -> 401
  [PASS] GET /usuarios com X-Admin-Token -> 200
  [PASS] login com a senha antiga do seed -> 401
  [PASS] login do admin criado devolve token
  [PASS] POST /pedidos sem login -> 401
  [PASS] POST /pedidos do próprio cliente -> 201
  [PASS] GET /pedidos/usuario/<outro> -> 403

== ecommerce-api-legacy (Node.js/Express)
  [PASS] npm ci
  [PASS] npm test (tests 10; fail 0)
  [PASS] com o .env.example sem editar, o placeholder não abre o relatório -> 403
  [PASS] POST /api/checkout -> 200
  [PASS] checkout com card numérico -> 400
  [PASS] relatório sem token -> 401
  [PASS] relatório com token -> 200

== task-manager-api (Python/Flask + SQLAlchemy)
  [PASS] pip install -r requirements.txt
  [PASS] python -m unittest discover -s tests -t . (Ran 19 tests in 18.385s)
  [PASS] com o .env.example sem editar, a aplicação recusa iniciar e explica
  [PASS] python seed.py
  [PASS] flask --app app create-admin (Admin criado: id=4)
  [PASS] GET /health
  [PASS] GET /tasks sem token -> 401
  [PASS] login com a senha antiga do seed -> 401
  [PASS] GET /tasks do admin traz as 10 tasks do seed
  [PASS] GET /tasks/stats -> 200
  [PASS] GET /reports/summary -> 200
  [PASS] usuário comum apagando task de outro -> 403
  [PASS] usuário comum apagando categoria -> 403
  [PASS] usuário comum lendo /users -> 403
  [PASS] cadastro anônimo com role admin -> 403

TUDO OK
```

Os mesmos testes foram executados contra o commit anterior a esta correção, para confirmar que detectam as falhas: 18 falhas no projeto 3 e 3 no projeto 2. No projeto 1, os 16 testes dão erro no `setUp`, porque o login antigo não devolvia token.

### Checklist de Validação — Projeto 1 (`code-smells-project`)

**Fase 1 — Análise**
- [x] Linguagem detectada corretamente (Python)
- [x] Framework detectado corretamente (Flask)
- [x] Domínio da aplicação descrito corretamente (E-commerce API)
- [x] Número de arquivos analisados condiz com a realidade (4 arquivos)

**Fase 2 — Auditoria**
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados
- [x] Detecção de APIs deprecated incluída (nenhuma encontrada)
- [x] Skill pausa e pede confirmação antes da Fase 3

**Fase 3 — Refatoração**
- [x] Estrutura de diretórios segue padrão MVC
- [x] Configuração extraída para módulo de config (sem hardcoded)
- [x] Models criados para abstrair dados
- [x] Views/Routes separadas para visualização ou roteamento
- [x] Controllers concentram o fluxo da aplicação
- [x] Error handling centralizado
- [x] Entry point claro
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente

### Checklist de Validação — Projeto 2 (`ecommerce-api-legacy`)

**Fase 1 — Análise**
- [x] Linguagem detectada corretamente (Node.js / JavaScript)
- [x] Framework detectado corretamente (Express)
- [x] Domínio da aplicação descrito corretamente (LMS com checkout)
- [x] Número de arquivos analisados condiz com a realidade (3 arquivos em src/)

**Fase 2 — Auditoria**
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados
- [x] Detecção de APIs deprecated incluída (nenhuma encontrada)
- [x] Skill pausa e pede confirmação antes da Fase 3

**Fase 3 — Refatoração**
- [x] Estrutura de diretórios segue padrão MVC
- [x] Configuração extraída para módulo de config (sem hardcoded)
- [x] Models criados para abstrair dados
- [x] Views/Routes separadas para visualização ou roteamento
- [x] Controllers concentram o fluxo da aplicação
- [x] Error handling centralizado
- [x] Entry point claro
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente

### Checklist de Validação — Projeto 3 (`task-manager-api`)

**Fase 1 — Análise**
- [x] Linguagem detectada corretamente (Python)
- [x] Framework detectado corretamente (Flask + SQLAlchemy)
- [x] Domínio da aplicação descrito corretamente (Task Manager API)
- [x] Número de arquivos analisados condiz com a realidade (15 arquivos em múltiplos diretórios)

**Fase 2 — Auditoria**
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados
- [x] Detecção de APIs deprecated incluída (`Model.query.get()` do SQLAlchemy)
- [x] Skill pausa e pede confirmação antes da Fase 3

**Fase 3 — Refatoração**
- [x] Estrutura de diretórios segue padrão MVC
- [x] Configuração extraída para módulo de config (sem hardcoded)
- [x] Models criados para abstrair dados
- [x] Views/Routes separadas para visualização ou roteamento
- [x] Controllers concentram o fluxo da aplicação
- [x] Error handling centralizado
- [x] Entry point claro
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente

### Comportamento em Stacks Diferentes

- **Python/Flask e Node.js/Express:** a Fase 1 detectou as duas stacks pelos manifestos, e os mesmos anti-patterns foram encontrados com sinais específicos de cada linguagem (`?` no `sqlite3`, `crypto.scrypt` no Node, `werkzeug.security` no Python).
- **Monolito e projeto parcialmente organizado:** nos projetos 1 e 2, a Fase 3 criou as camadas do zero. No projeto 3, manteve o que existia e acrescentou o que faltava.
- **Contrato:** cada mudança de contrato foi uma decisão de segurança e está registrada no relatório e no README do projeto.

### Iterações

| Rodada | O que a revisão apontou | Causa | Mudança na skill |
|---|---|---|---|
| 1ª | Rotas admin do projeto 2 abertas sem `ADMIN_TOKEN` (`b8a64df`) | Catálogo sem anti-pattern de autenticação; a Fase 3 aceitava opt-in para preservar contrato | AP-17, PB-12 e validação 403/401/200 |
| 2ª | Senhas de seed mantidas com hash; relatório do projeto 2 com 3 findings, por ter sido gerado sobre código refatorado | AP-02 sem credencial de seed; a Fase 3 aceitava recomendação cumprida em parte | Sinal de seed no AP-02, PB-13, aplicação integral com evidência, reexecução a partir do original |
| 3ª (auditoria interna) | Clone limpo: token forjado com o segredo do exemplo, placeholder aceito como credencial, usuário comum apagando dados de outros e README desatualizado | Validação só na máquina de desenvolvimento e correção do caso apontado, sem revisar os outros projetos | PB-14, placeholder recusado, ataque e clone limpo obrigatórios, testes no projeto e frontmatter no `SKILL.md` |

### Limitações Conhecidas

Fora do escopo dos findings e registradas para evolução:

- **`code-smells-project`:** cancelar pedido não devolve estoque; o relatório de vendas soma pedidos cancelados; CORS aberto para qualquer origem; `usuario_id` de pedido criado por admin não é conferido.
- **`ecommerce-api-legacy`:** checkout e DELETE fazem várias escritas sem transação; pagamento recusado deixa o usuário criado; o gateway é simulado.
- **`task-manager-api`:** senha mínima de 4 caracteres, mantida do contrato original; `NotificationService` não é chamado por nenhuma rota; CORS aberto para qualquer origem.
- **Histórico do git:** as credenciais dos códigos originais continuam no histórico. São fictícias neste desafio; em um projeto real, precisariam ser trocadas.

---

## Como Executar

### Pré-requisitos

- **Claude Code** instalado e configurado (`claude` disponível no PATH), para executar a skill
- Python 3.x e Node.js 18+

### Execução da Skill

A skill audita o código atual. Para reproduzir a auditoria dos relatórios, parta do código original (commit `6d1ce62`), como orienta o `SKILL.md`.

```bash
cd code-smells-project
claude "/refactor-arch"

cd ../ecommerce-api-legacy
claude "/refactor-arch"

cd ../task-manager-api
claude "/refactor-arch"
```

A skill pausa ao final da Fase 2 e aguarda `y` antes de refatorar.

### Como validar que a refatoração funcionou

**Tudo de uma vez, em clone limpo:** `python scripts/verify_clean_clone.py`

Para rodar cada projeto à mão, gere os segredos com `python -c "import secrets; print(secrets.token_hex(32))"`. Com o `.env` copiado sem edição, os projetos 1 e 3 recusam iniciar e explicam o que falta. É proposital: o `.env.example` não contém nenhum segredo válido.

**Projeto 1 (Python/Flask):**
```bash
cd code-smells-project
pip install -r requirements.txt
cp .env.example .env              # defina SECRET_KEY e ADMIN_TOKEN
python -m unittest discover -s tests -t .
python app.py
# Em outro terminal:
curl http://localhost:5000/health
curl http://localhost:5000/produtos
curl -H "X-Admin-Token: <seu ADMIN_TOKEN>" http://localhost:5000/usuarios
```

**Projeto 2 (Node.js/Express):**
```bash
cd ecommerce-api-legacy
npm install
cp .env.example .env              # defina ADMIN_TOKEN
npm test
npm start
# Em outro terminal:
curl -H "x-admin-token: <seu ADMIN_TOKEN>" http://localhost:3000/api/admin/financial-report
```

**Projeto 3 (Python/Flask):**
```bash
cd task-manager-api
pip install -r requirements.txt
cp .env.example .env              # defina SECRET_KEY, ADMIN_EMAIL e ADMIN_PASSWORD
python -m unittest discover -s tests -t .
python seed.py
flask --app app create-admin
python app.py
# Em outro terminal:
curl http://localhost:5000/health
curl -X POST http://localhost:5000/login -H "Content-Type: application/json" -d '{"email":"<ADMIN_EMAIL>","password":"<ADMIN_PASSWORD>"}'
curl -H "Authorization: Bearer <token>" http://localhost:5000/tasks
```

Cada projeto tem um README com a configuração e as permissões de cada rota.

---

## Estrutura do Repositório

```
mba-ia-refactor-projects-skill/
├── README.md
├── ENUNCIADO.md                     # Enunciado original do desafio
├── scripts/verify_clean_clone.py    # Validação em clone limpo
├── reports/                         # Relatórios de auditoria
│   ├── audit-project-1.md
│   ├── audit-project-2.md
│   └── audit-project-3.md
├── code-smells-project/             # Projeto 1 — Python/Flask (E-commerce API)
│   ├── .claude/skills/refactor-arch/
│   │   ├── SKILL.md
│   │   ├── 01-project-analysis.md
│   │   ├── 02-antipatterns-catalog.md
│   │   ├── 03-report-template.md
│   │   ├── 04-mvc-guidelines.md
│   │   └── 05-refactoring-playbook.md
│   ├── reports/  config/  models/  controllers/  routes/  middlewares/  services/  tests/
│   ├── app.py
│   └── database.py
├── ecommerce-api-legacy/            # Projeto 2 — Node.js/Express (LMS API)
│   ├── .claude/skills/refactor-arch/   # Cópia da skill
│   ├── reports/  tests/
│   ├── src/                         # config, database, models, controllers, routes, middlewares,
│   │                                # services, validators, utils e app.js
│   └── api.http
└── task-manager-api/                # Projeto 3 — Python/Flask (Task Manager)
    ├── .claude/skills/refactor-arch/   # Cópia da skill
    ├── reports/  config/  models/  controllers/  routes/  middlewares/  services/  utils/  tests/
    ├── app.py
    ├── seed.py
    └── api.http
```
