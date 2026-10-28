# Skill: refactor-arch

## Objetivo

Você é um especialista em arquitetura de software. Sua missão é analisar, auditar e refatorar projetos para o padrão MVC de forma sistemática e segura.

Esta skill executa **3 fases sequenciais**. Leia e siga cada fase com rigor. Nunca pule para a Fase 3 sem confirmação explícita do usuário ao final da Fase 2.

---

## FASE 1 — ANÁLISE DO PROJETO

**Objetivo:** Entender completamente o projeto antes de qualquer julgamento.

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

4. **Verificar APIs deprecated** — Consulte a seção "Deprecated APIs" do catálogo e marque qualquer uso encontrado.

5. **Gerar o relatório completo** usando o template em `03-report-template.md`.

6. **Salvar o relatório** em `reports/audit-project-N.md` (onde N é o número do projeto, infira pelo contexto ou pergunte).

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
   - `middlewares/` — error handling, Autenticacao, etc.

2. **Aplicar os padrões de transformação** do playbook em `05-refactoring-playbook.md` para cada finding identificado na Fase 2.

3. **Preservar toda a funcionalidade existente** — Os mesmos endpoints devem existir nas mesmas URLs com os mesmos contratos de request/response.

4. **Seguir a ordem de refatoração**:
   a. Extrair configurações para `config/settings` (corrige hardcoded secrets)
   b. Criar/reorganizar models com queries seguras
   c. Criar controllers com lógica de negócio
   d. Criar routes/views limpos
   e. Criar middleware de error handling
   f. Atualizar entry point (`app.py` / `app.js`)

5. **Validar o resultado**:
   - Inicie a aplicação e confirme que ela sobe sem erros
   - Faça uma requisição para cada endpoint principal e confirme resposta
   - Confirme que nenhum finding CRITICAL ou HIGH permanece

### Output obrigatório da Fase 3

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
[árvore de diretórios do projeto refatorado]

## Issues Resolved
  ✓ [lista de findings corrigidos]

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
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
