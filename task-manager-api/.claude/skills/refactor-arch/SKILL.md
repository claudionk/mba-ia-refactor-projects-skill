---
name: refactor-arch
description: Audita um backend legado e o refatora para MVC em 3 fases (análise da stack, relatório de anti-patterns e refatoração validada), com pausa obrigatória antes de alterar código. Use quando o usuário pedir auditoria de arquitetura, detecção de code smells ou refatoração para MVC.
---

# Skill: refactor-arch

## Objetivo

Você é um especialista em arquitetura de software. Sua missão é analisar, auditar e refatorar projetos para o padrão MVC de forma sistemática e segura.

Esta skill executa **3 fases sequenciais**. Leia e siga cada fase com rigor. Nunca pule para a Fase 3 sem confirmação explícita do usuário ao final da Fase 2.

---

## FASE 1 — ANÁLISE DO PROJETO

**Objetivo:** Entender completamente o projeto antes de qualquer julgamento.

### Reexecução em projeto já refatorado

A auditoria precisa partir do código original. Rodar a skill sobre o resultado de uma execução anterior mede só o que sobrou e produz um relatório que não representa o projeto. Se o histórico do git mostrar que a skill já refatorou este projeto, avise o usuário e, com a autorização dele e a árvore de trabalho limpa, restaure o código do commit original antes de iniciar a Fase 1. Mantenha `.claude/` e arquivos ignorados, como `.env`.

### Passos obrigatórios

1. **Detectar a stack** — Leia os arquivos de manifesto (requirements.txt, package.json, Gemfile, pom.xml, go.mod, etc.) para identificar:
   - Linguagem e versão
   - Framework principal e versão
   - Dependências relevantes (ORM, auth, CORS, etc.)

2. **Mapear os arquivos fonte** — Liste todos os arquivos de código (`.py`, `.js`, `.ts`, `.rb`, `.go`, etc.), excluindo `node_modules/`, `venv/`, `.git/`, `__pycache__/`. Conte e registre o total.

3. **Identificar o domínio** — Leia os nomes de rotas, modelos e variáveis para descrever o que a aplicação faz em uma frase.

4. **Mapear a arquitetura atual** — Identifique se existe separação em camadas, quais responsabilidades estão em quais arquivos.

5. **Identificar banco de dados** — Detecte se usa ORM ou SQL raw, qual banco (SQLite, PostgreSQL, MongoDB etc.), e se usa migrations.

### Output obrigatório da Fase 1

Imprima exatamente neste formato:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      [linguagem] [versão se disponível]
Framework:     [framework] [versão]
Dependencies:  [lista das principais dependências]
Domain:        [descrição do domínio em 1 frase]
Architecture:  [descrição da arquitetura atual]
Source files:  [N] files analyzed
DB:            [banco de dados e modo de acesso]
================================
```

Consulte o arquivo de referência `01-project-analysis.md` para heurísticas detalhadas de detecção.

---

## FASE 2 — AUDITORIA DE ARQUITETURA

**Objetivo:** Identificar todos os problemas do projeto com localização exata.

### Passos obrigatórios

1. **Ler cada arquivo fonte** e cruzar contra o catálogo de anti-patterns em `02-antipatterns-catalog.md`.

2. **Registrar cada finding** com:
   - Severidade (CRITICAL / HIGH / MEDIUM / LOW)
   - Nome do anti-pattern
   - Arquivo e linhas exatas
   - Descrição do problema específico encontrado
   - Impacto concreto
   - Recomendação de correção

3. **Ordenar os findings** por severidade: CRITICAL → HIGH → MEDIUM → LOW.

4. **Verificar autenticação de endpoints sensíveis (AP-17)** — Para cada rota administrativa, financeira ou destrutiva, confirme que existe middleware/decorator de autenticação **e** que ele nega o acesso quando a credencial não está configurada. Middleware opt-in/fail-open (`if (!token) return next()`) e `.env.example` com a credencial vazia são findings. A recomendação deve sempre ser deny-by-default (PB-12), nunca "opt-in para preservar o contrato". Verifique também a **autorização**: para cada escrita e leitura de dado pessoal, pergunte quem pode agir sobre o recurso de quem. Login válido não basta (PB-14), e identidade enviada no body não prova nada.

5. **Verificar credenciais de seed (AP-02)** — Leia seeds, fixtures, migrations e fallbacks de configuração. Toda conta criada com senha literal é finding CRITICAL, inclusive quando a senha recebe hash ou quando ainda não existe rota de login. A recomendação deve seguir o PB-13.

6. **Verificar APIs deprecated** — Consulte a seção "Deprecated APIs" do catálogo e marque qualquer uso encontrado.

7. **Conferir o mínimo de 5 findings** — Com menos de 5, confirme que a auditoria partiu do código original (ver Fase 1) e releia cada arquivo contra o catálogo inteiro. Se ainda assim não houver 5 findings reais, informe isso ao usuário. Nunca invente nem infle findings para atingir o número.

8. **Gerar o relatório completo** usando o template em `03-report-template.md`.

9. **Salvar o relatório** em `reports/audit-project-N.md` (onde N é o número do projeto, infira pelo contexto ou pergunte).

### Output obrigatório da Fase 2

Imprima o relatório completo no terminal seguindo o template de `03-report-template.md`.

### ⚠️ PAUSA OBRIGATÓRIA

Após imprimir o relatório, **PARE** e pergunte ao usuário:

```
================================
PHASE 2 COMPLETE
================================
Relatório salvo em: reports/audit-project-N.md
Total de findings: [N]

Phase 3 vai reestruturar o projeto para o padrão MVC.
Todos os arquivos originais serão modificados ou movidos.

Proceed with refactoring (Phase 3)? [y/n]
>
```

**Não execute a Fase 3 sem que o usuário responda `y` ou `yes`.**

---

## FASE 3 — REFATORAÇÃO PARA MVC

**Objetivo:** Reestruturar o projeto para o padrão MVC eliminando todos os findings CRITICAL e HIGH, e o máximo possível de MEDIUM e LOW.

### Passos obrigatórios

1. **Criar a estrutura de diretórios MVC** conforme as guidelines em `04-mvc-guidelines.md`:
   - `config/` — configurações e variáveis de ambiente
   - `models/` — entidades e acesso a dados
   - `controllers/` — lógica de negócio
   - `views/` ou `routes/` — roteamento HTTP
   - `middlewares/` — error handling, autenticação, etc.

2. **Aplicar os padrões de transformação** do playbook em `05-refactoring-playbook.md` para cada finding identificado na Fase 2.

   **Aplicar por inteiro a recomendação de cada CRITICAL e HIGH.** Antes de editar, divida a `Recommendation` de cada um desses findings em ações verificáveis e execute todas:
   - Um finding só está resolvido quando **todas** as ações foram feitas como o relatório descreve. Resolver parte dele mantém o finding aberto.
   - Trocar a ação recomendada por uma alternativa mais fraca não é correção. Exemplos: aplicar hash a uma senha de seed quando o relatório manda criar a conta por comando de setup; gerar uma chave aleatória quando o relatório manda falhar sem a variável.
   - Preservar contrato ou manter dados de demonstração não justifica omitir uma ação.
   - Se uma ação depender de decisão do usuário ou não puder ser aplicada, pergunte antes de encerrar a fase. Sem resposta, registre o finding como `✗ OPEN` com o motivo. Nesse caso, é proibido declarar "Zero CRITICAL/HIGH".

3. **Preservar toda a funcionalidade existente** — Os mesmos endpoints devem existir nas mesmas URLs com os mesmos contratos de request/response.
   **Exceção obrigatória:** endpoints sensíveis (AP-17) passam a exigir credencial. Preservar contrato **nunca** justifica deixá-los abertos. Documente a mudança no output.

4. **Seguir a ordem de refatoração**:
   a. Extrair configurações para `config/settings` (corrige hardcoded secrets)
   a1. **Eliminar credenciais de seed (PB-13)** — Nenhuma senha literal no seed, com ou sem hash. Admin nasce de comando de setup; conta exigida por integridade de dados recebe senha aleatória.
   a2. **Proteger endpoints sensíveis com deny-by-default (PB-12), em qualquer stack** — Python e Node.js seguem o mesmo padrão: sem credencial configurada → 403; credencial errada → 401; comparação em tempo constante; `.env.example` com placeholder não vazio, que nunca vale como credencial. É proibido o padrão opt-in que libera a rota quando a variável não está definida.
   a3. **Aplicar autorização por dono ou papel (PB-14)** — Identidade vem do token assinado, nunca do body; recurso de outro usuário responde 403.
   b. Criar/reorganizar models com queries seguras
   c. Criar controllers com lógica de negócio
   d. Criar routes/views limpos
   e. Criar middleware de error handling
   f. Atualizar entry point (`app.py` / `app.js`)

5. **Validar o resultado**:
   - Inicie a aplicação e confirme que ela sobe sem erros
   - Faça uma requisição para cada endpoint principal e confirme resposta
   - Para cada rota protegida, teste os 3 cenários de PB-12 (sem `ADMIN_TOKEN` → 403, token errado → 401, token correto → 200) e registre os status obtidos
   - Releia os middlewares de autenticação e confirme que nenhum caminho chama `next()`/a view quando a credencial não está configurada
   - Execute a validação do PB-13 e registre os resultados
   - **Teste como atacante:** com o `.env` copiado do `.env.example`, tente usar cada placeholder como credencial e forjar token com o segredo de exemplo. Como usuário comum, tente ler e alterar recursos de outro usuário e criar conta privilegiada. Registre os status obtidos
   - **Valide em clone limpo:** clone o commit em uma pasta nova, sem `.env` nem dependências instaladas, e siga os comandos do README ao pé da letra. Comando que falha é defeito do README ou do código
   - **Grave testes automatizados no projeto** cobrindo contrato e ataques, executáveis com a biblioteca padrão da stack quando possível. Um teste só vale depois de ter falhado contra o comportamento vulnerável
   - Releia no relatório a `Recommendation` de cada CRITICAL e HIGH e aponte, para cada ação, o arquivo e a linha que a implementam, ou o teste que a comprova. Ação sem evidência mantém o finding aberto
   - Confirme que nenhum finding CRITICAL ou HIGH permanece. Só declare isso depois de todos os itens acima

### Output obrigatório da Fase 3

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
[árvore de diretórios do projeto refatorado]

## Issues Resolved
  ✓ [lista de findings corrigidos]
  ✗ OPEN [finding CRITICAL/HIGH não resolvido por inteiro e o motivo, se houver]

## Recommendation Coverage (CRITICAL/HIGH)
  [finding] — [ação recomendada] → [arquivo:linha ou teste que comprova]

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
  ✓ Sensitive endpoints deny by default (no token → 403, wrong → 401, valid → 200)
  ✓ No seed credentials (PB-13)
  ✓ Placeholders and forged tokens rejected; owner/role authorization enforced (PB-12, PB-14)
  ✓ Clean clone: README commands work and automated tests pass
  ✓ Every CRITICAL/HIGH recommendation applied in full
  ✓ Zero CRITICAL/HIGH anti-patterns remaining
================================
```

---

## Referências

Consulte os arquivos de referência nesta ordem quando precisar de orientação:

| Quando precisar de...              | Consulte...                  |
|------------------------------------|------------------------------|
| Heurísticas de detecção de stack   | `01-project-analysis.md`     |
| Classificar um problema encontrado | `02-antipatterns-catalog.md` |
| Formatar o relatório               | `03-report-template.md`      |
| Definir a estrutura MVC alvo       | `04-mvc-guidelines.md`       |
| Transformar código concreto        | `05-refactoring-playbook.md` |

