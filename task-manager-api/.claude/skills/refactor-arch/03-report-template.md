# Referência: Template de Relatório de Auditoria

Este arquivo define o formato padrão do relatório gerado na **Fase 2**. Use exatamente esta estrutura ao gerar o relatório — tanto para exibir no terminal quanto para salvar em `reports/audit-project-N.md`.

---

## Template Completo

```markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: [nome do diretório do projeto]
Stack:   [Linguagem] + [Framework]
Files:   [N] analyzed | ~[LOC estimado] lines of code
Date:    [data de execução]

## Summary

CRITICAL: [N] | HIGH: [N] | MEDIUM: [N] | LOW: [N]
Total findings: [N]

## Findings

### [CRITICAL] [Nome do Anti-Pattern — ex: SQL Injection]
File: [caminho/arquivo.py]:[linha-início]-[linha-fim]
Anti-pattern: AP-XX — [nome do catálogo]
Description: [Descrição específica do problema encontrado neste arquivo, com trecho de código relevante]
Impact: [Consequência concreta se não corrigido]
Recommendation: [Ação específica para corrigir]

---

### [CRITICAL] [Nome do Anti-Pattern]
File: [caminho/arquivo.py]:[linha]
Anti-pattern: AP-XX — [nome do catálogo]
Description: [...]
Impact: [...]
Recommendation: [...]

---

[... repetir para cada finding, ordenado CRITICAL → HIGH → MEDIUM → LOW ...]

---

### [LOW] [Nome do Anti-Pattern]
File: [caminho/arquivo.py]:[linha-início]-[linha-fim]
Anti-pattern: AP-XX — [nome do catálogo]
Description: [...]
Impact: [...]
Recommendation: [...]

================================
Total: [N] findings
CRITICAL: [N] | HIGH: [N] | MEDIUM: [N] | LOW: [N]
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
>
```

---

## Regras de Preenchimento

### Cabeçalho
- `Project`: use o nome do diretório raiz onde a skill está sendo executada
- `Stack`: formato `Linguagem + Framework`, ex: `Python + Flask`, `Node.js + Express`
- `Files`: número total de arquivos de código analisados (sem contar config, lock files, etc.)
- `LOC estimado`: soma aproximada de linhas de código dos arquivos analisados
- `Date`: data de execução no formato `YYYY-MM-DD`

### Summary
- Liste os contadores antes dos findings para dar visão rápida da gravidade
- O total deve ser a soma dos 4 níveis

### Findings — Regras obrigatórias

1. **Ordenação:** Sempre CRITICAL primeiro, depois HIGH, MEDIUM e LOW. Dentro de cada nível, ordene por impacto (mais grave primeiro).

2. **Localização exata:** Sempre informe arquivo + linha(s). Use `:N` para linha única, `:N-M` para range.
   - Correto: `models.py:28`
   - Correto: `models.py:105-120`
   - Errado: `models.py` (sem linha)

3. **Descrição específica:** A descrição deve ser sobre **este projeto específico**, não genérica. Inclua um trecho do código problemático se ajudar a localizar.

4. **Impacto concreto:** Descreva o que pode acontecer de errado no **contexto desta aplicação**.

5. **Recomendação acionável:** A recomendação deve ser específica o suficiente para implementar, não genérica.

### Separador de findings
Use `---` (três hífens) entre cada finding para facilitar a leitura.

---

## Exemplo de Finding Bem Preenchido

```markdown
### [CRITICAL] SQL Injection
File: models.py:109-111
Anti-pattern: AP-01 — SQL Injection
Description: A função `login_usuario` constrói a query de Autenticacao por
concatenação direta de strings, sem parâmetros. Qualquer valor nos campos
email ou senha pode alterar a lógica da query:
  cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
  Um atacante pode usar email = "' OR '1'='1" para autenticar sem credenciais.
Impact: Autenticacao bypassável por qualquer usuário anônimo; possível exfiltração
completa da tabela de usuários.
Recommendation: Substituir por query parametrizada:
  cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
```

---

## Exemplo de Finding de Deprecated API

```markdown
### [HIGH] Deprecated API — SQLAlchemy Model.query.get()
File: routes/task_routes.py:42, 67, 117, 158, 188, 227
Anti-pattern: DEP-01 — SQLAlchemy Model.query.get() depreciado
Description: O método `Model.query.get(id)` foi depreciado no SQLAlchemy 2.0
e removido no 2.1. O projeto usa esse padrão em pelo menos 6 locais:
  user = User.query.get(t.user_id)  # linha 42
  task = Task.query.get(task_id)    # linha 67
  [... etc ...]
Impact: O código quebrará ao atualizar o SQLAlchemy para versão 2.1+.
Recommendation: Substituir todas as ocorrências por:
  user = db.session.get(User, t.user_id)
  task = db.session.get(Task, task_id)
```
