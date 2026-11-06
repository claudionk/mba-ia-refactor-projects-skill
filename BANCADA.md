# Bancada de Testes E2E

Este guia ensina a instalar, executar e testar os 3 projetos do repositório, sem precisar conhecer o código. Todos os comandos podem ser copiados e colados.

**Tempo estimado:** 5 minutos para o teste automático (Parte 2) e cerca de 30 minutos para os testes manuais (Partes 3 a 5).

## O que está sendo testado

São 3 APIs (programas que respondem a requisições HTTP, sem tela) que foram refatoradas e corrigidas. O teste responde a três perguntas:

1. A aplicação instala e inicia seguindo as instruções?
2. As funções originais continuam respondendo?
3. As falhas de segurança foram mesmo fechadas?

| Projeto | Pasta | O que é | Tecnologia | Porta na bancada |
|---|---|---|---|---|
| 1 | `code-smells-project` | Loja: produtos, usuários e pedidos | Python + Flask | 5001 |
| 2 | `ecommerce-api-legacy` | Cursos: checkout e relatório financeiro | Node.js + Express | 3101 |
| 3 | `task-manager-api` | Gerenciador de tarefas | Python + Flask | 5003 |

**Como ler os resultados:** cada teste devolve um código HTTP de 3 dígitos.

| Código | Significado | Exemplo |
|---|---|---|
| 200 / 201 | Deu certo / foi criado | Listar produtos |
| 400 | Dados inválidos, recusados | Quantidade negativa |
| 401 | Não identificado: falta login ou token válido | Pedido sem login |
| 403 | Identificado, mas sem permissão | Apagar dado de outra pessoa |
| 404 | Não encontrado | Curso inexistente |
| 500, ou erro de conexão | **Defeito.** Nenhum teste deste guia espera esse resultado | |

> Nos testes de segurança, **401 e 403 são o resultado correto**: significa que o sistema barrou a ação.

---

## Parte 1 — Preparar a máquina

### 1.1 Instalar os programas

| Programa | Versão usada na validação deste guia | Download |
|---|---|---|
| Git | Qualquer versão recente | https://git-scm.com/downloads |
| Python | 3.14 | https://www.python.org/downloads/ |
| Node.js (já inclui o npm) | 26 | https://nodejs.org/ |

No **Windows**, ao instalar o Python, marque a opção **"Add Python to PATH"**.

### 1.2 Abrir o terminal

- **Windows com Git Bash:** procure "Git Bash" no menu Iniciar (ele é instalado junto com o Git) e siga as Partes 1 a 5 normalmente.
- **Windows com PowerShell:** siga a [Parte 9](#parte-9--roteiro-para-powershell-windows), que traz todos os comandos adaptados. Os blocos das Partes 1 a 5 não funcionam no PowerShell.
- **Linux e macOS:** use o Terminal.

O Prompt de Comando (`cmd`) não é suportado.

### 1.3 Conferir a instalação

```bash
git --version
python --version
node --version
npm --version
```

Cada comando deve mostrar um número de versão.

> **Linux e macOS:** se `python` não for encontrado, troque `python` por `python3` nos comandos até o passo de ativar o ambiente virtual.

### 1.4 Baixar o projeto

```bash
git clone https://github.com/claudionk/mba-ia-refactor-projects-skill.git bancada-refactor
cd bancada-refactor
```

Todos os passos abaixo partem desta pasta, `bancada-refactor`.

---

## Parte 2 — Teste automático (comece por aqui)

Este comando faz tudo sozinho em uma pasta temporária: instala os 3 projetos do zero, roda os testes automatizados e simula ataques.

```bash
python scripts/verify_clean_clone.py
```

**Resultado esperado:** todas as linhas com `[PASS]` e, na última, `TUDO OK`.

- **Com `FAIL`:** anote a linha na [Folha de Resultados](#parte-6--folha-de-resultados). A bancada está reprovada neste ponto.
- **Se não executar:** veja [Problemas comuns](#parte-8--problemas-comuns).

As Partes 3 a 5 repetem o essencial à mão, para você ver cada resultado com os próprios olhos.

---

## Parte 3 — Projeto 1: Loja (`code-smells-project`)

### 3.1 Instalar

```bash
cd code-smells-project
python -m venv .venv
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
pip install -r requirements.txt
```

O início da linha do terminal deve passar a mostrar `(.venv)`. Esse é o ambiente virtual ativado.

### 3.2 Rodar os testes automatizados

```bash
python -m unittest discover -s tests -t .
```

**Esperado** ao final (os avisos e o tempo acima dessas linhas podem variar):

```text
Ran 16 tests in ...s

OK
```

### 3.3 Confirmar que o arquivo de exemplo não abre a aplicação

```bash
cp .env.example .env
python app.py 2>&1 | tail -n 1
```

**Esperado:** a aplicação **recusa iniciar**, e a mensagem começa com:

```text
RuntimeError: Defina SECRET_KEY no ambiente ou no .env.
```

### 3.4 Configurar e criar o administrador

```bash
rm -f loja.db
cat > .env <<EOF
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
ADMIN_TOKEN=bancada-admin-token
ADMIN_EMAIL=admin@bancada.com
ADMIN_PASSWORD=senha-admin-bancada
PORT=5001
DB_PATH=loja.db
EOF
flask --app app criar-admin
```

**Esperado:**

```text
Admin criado: id=1
```

> Os valores acima servem só para esta bancada.

### 3.5 Iniciar o servidor (Terminal 1)

```bash
python app.py
```

O terminal fica "preso" mostrando mensagens, e isso é o normal: o servidor está no ar. **Deixe esta janela aberta.**

### 3.6 Preparar o Terminal 2

Abra **outra janela** do terminal, entre na pasta com `cd` (por exemplo, `cd bancada-refactor/code-smells-project`) e cole:

```bash
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
BASE=http://127.0.0.1:5001
J='Content-Type: application/json'
ADM='X-Admin-Token: bancada-admin-token'
st() { curl -s -o /dev/null -w "%{http_code}\n" "$@"; }
```

`st` é um atalho que mostra só o código de resposta. Cole os blocos abaixo **em ordem**, um de cada vez, e compare cada número mostrado com o valor de `esperado` (a parte depois do `#` é só um comentário).

### 3.7 Testes

**A aplicação funciona:**

```bash
st $BASE/health                       # P1-01 esperado: 200
st $BASE/produtos                     # P1-02 esperado: 200
st "$BASE/produtos/busca?q=Mouse"     # P1-03 esperado: 200
```

**Rotas administrativas estão protegidas:**

```bash
st $BASE/usuarios                                    # P1-04 esperado: 401
st -H 'X-Admin-Token: errado' $BASE/usuarios         # P1-05 esperado: 401
st -H "$ADM" $BASE/usuarios                          # P1-06 esperado: 200
st -X POST -H "$J" -d '{"sql":"SELECT 1"}' $BASE/admin/query   # P1-07 esperado: 404
```

**As senhas antigas, que estavam publicadas no código, não entram mais:**

```bash
st -X POST -H "$J" -d '{"email":"admin@loja.com","senha":"admin123"}' $BASE/login   # P1-08 esperado: 401
st -X POST -H "$J" -d '{"email":"joao@email.com","senha":"123456"}' $BASE/login     # P1-09 esperado: 401
```

**O ataque de SQL Injection não extrai dados.** Este teste mostra o corpo da resposta:

```bash
curl -s -G --data-urlencode "q=x%') UNION SELECT id,nome,email,senha,tipo,criado_em,NULL,NULL FROM usuarios --" $BASE/produtos/busca
```

**P1-10 esperado:** o campo `dados` vem vazio (`"dados":[]`) e nenhum e-mail aparece.

**Segredos não aparecem no monitoramento:**

```bash
curl -s $BASE/health
```

**P1-11 esperado:** a resposta não contém `secret_key` nem `db_path`.

**Cada cliente só acessa os próprios pedidos.** Primeiro, crie duas clientes e faça login com a Ana:

```bash
st -X POST -H "$J" -d '{"nome":"Ana","email":"ana@x.com","senha":"senha-ana"}' $BASE/usuarios   # P1-12 esperado: 201
st -X POST -H "$J" -d '{"nome":"Bia","email":"bia@x.com","senha":"senha-bia"}' $BASE/usuarios   # P1-13 esperado: 201
TOKEN=$(curl -s -X POST -H "$J" -d '{"email":"ana@x.com","senha":"senha-ana"}' $BASE/login | python -c "import sys,json; print(json.load(sys.stdin)['token'])")
ANA="Authorization: Bearer $TOKEN"
```

Na bancada, o admin é o usuário 1, a Ana é o usuário 2 e a Bia é o usuário 3.

```bash
PEDIDO_ANA='{"usuario_id":2,"itens":[{"produto_id":1,"quantidade":1}]}'
PEDIDO_BIA='{"usuario_id":3,"itens":[{"produto_id":1,"quantidade":1}]}'
st -X POST -H "$J" -d "$PEDIDO_ANA" $BASE/pedidos                 # P1-14 esperado: 401
st -X POST -H "$J" -H "$ANA" -d "$PEDIDO_ANA" $BASE/pedidos       # P1-15 esperado: 201
st -X POST -H "$J" -H "$ANA" -d "$PEDIDO_BIA" $BASE/pedidos       # P1-16 esperado: 403
st -H "$ANA" $BASE/pedidos/usuario/2                              # P1-17 esperado: 200
st -H "$ANA" $BASE/pedidos/usuario/3                              # P1-18 esperado: 403
st $BASE/pedidos/usuario/2                                        # P1-19 esperado: 401
```

**Entrada inválida é recusada:**

```bash
st -X POST -H "$J" -H "$ANA" -d '{"usuario_id":2,"itens":[{"produto_id":1,"quantidade":-100}]}' $BASE/pedidos   # P1-20 esperado: 400
st -X POST -H "$J" -d '{"email":"admin@bancada.com","senha":"senha-admin-bancada"}' $BASE/login                 # P1-21 esperado: 200
```

### 3.8 Encerrar

No **Terminal 1**, pressione `Ctrl+C` para parar o servidor. Depois volte à pasta principal:

```bash
cd ..
```

---

## Parte 4 — Projeto 2: Cursos (`ecommerce-api-legacy`)

Este projeto não usa ambiente virtual. Se o terminal ainda mostrar `(.venv)`, não há problema.

Os dados ficam em memória: ao reiniciar o servidor, tudo volta ao estado inicial.

### 4.1 Instalar e rodar os testes automatizados

```bash
cd ecommerce-api-legacy
npm install
npm test
```

**Esperado** ao final da saída (os números `tests` e `pass` iguais, e `fail` zero):

```text
ℹ tests 10
ℹ pass 10
ℹ fail 0
```

Avisos do `npm install` sobre pacotes antigos ou vulnerabilidades (`npm audit`) não reprovam a bancada.

### 4.2 Confirmar que o arquivo de exemplo não abre as rotas administrativas

```bash
cp .env.example .env
echo "PORT=3101" >> .env
```

**Terminal 1:**

```bash
npm start
```

**Terminal 2:** abra outra janela, entre na pasta (`cd bancada-refactor/ecommerce-api-legacy`) e cole:

```bash
BASE=http://127.0.0.1:3101
J='Content-Type: application/json'
ADM='x-admin-token: bancada-admin-token'
st() { curl -s -o /dev/null -w "%{http_code}\n" "$@"; }
st -H 'x-admin-token: troque-por-um-token-admin-forte' $BASE/api/admin/financial-report   # P2-01 esperado: 403
```

O token de exemplo é público, então não pode dar acesso.

Agora, no **Terminal 1**, pressione `Ctrl+C` para parar o servidor.

### 4.3 Configurar

No **Terminal 1**:

```bash
cat > .env <<EOF
PORT=3101
DB_PATH=:memory:
ADMIN_TOKEN=bancada-admin-token
EOF
```

### 4.4 Iniciar o servidor (Terminal 1)

```bash
npm start
```

**Esperado:** uma mensagem com `rodando na porta 3101`. Deixe a janela aberta.

### 4.5 Testes (Terminal 2)

**Rotas administrativas estão protegidas:**

```bash
st $BASE/api/admin/financial-report                                  # P2-02 esperado: 401
st -H 'x-admin-token: errado' $BASE/api/admin/financial-report       # P2-03 esperado: 401
st -H "$ADM" $BASE/api/admin/financial-report                        # P2-04 esperado: 200
st -X DELETE $BASE/api/users/1                                       # P2-05 esperado: 401
```

**O checkout funciona.** `card` iniciado em `4` é aprovado; os demais são recusados:

```bash
COMPRA='{"usr":"Gui","eml":"gui@x.com","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
st -X POST -H "$J" -d "$COMPRA" $BASE/api/checkout    # P2-06 esperado: 200
st -X POST -H "$J" -d '{"usr":"Joao","eml":"joao@x.com","pwd":"abc","c_id":1,"card":"5111222233334444"}' $BASE/api/checkout   # P2-07 esperado: 400
st -X POST -H "$J" -d '{}' $BASE/api/checkout         # P2-08 esperado: 400
st -X POST -H "$J" -d '{"usr":"Gui","eml":"novo@x.com","pwd":"abc","c_id":99,"card":"4111"}' $BASE/api/checkout   # P2-09 esperado: 404
```

**Ninguém compra em nome de outra conta sem a senha dela.** O e-mail `gui@x.com` foi criado acima:

```bash
st -X POST -H "$J" -d '{"usr":"Gui","eml":"gui@x.com","pwd":"senhaforte","c_id":1,"card":"4111222233334444"}' $BASE/api/checkout   # P2-10 esperado: 200
st -X POST -H "$J" -d '{"usr":"Gui","eml":"gui@x.com","pwd":"errada","c_id":1,"card":"4111222233334444"}' $BASE/api/checkout       # P2-11 esperado: 401
st -X POST -H "$J" -d '{"usr":"Gui","eml":"gui@x.com","c_id":1,"card":"4111222233334444"}' $BASE/api/checkout                      # P2-12 esperado: 401
st -X POST -H "$J" -d '{"usr":"X","eml":"leonan@fullcycle.com.br","pwd":"123","c_id":1,"card":"4111222233334444"}' $BASE/api/checkout   # P2-13 esperado: 401
```

**As entradas que derrubavam o servidor original agora são recusadas.** Estes são os testes mais importantes deste projeto:

```bash
st -X POST -H "$J" -d '{"usr":"X","eml":"x@x.com","pwd":"abc","c_id":1,"card":123}' $BASE/api/checkout   # P2-14 esperado: 400
st -X POST -H "$J" -d '{"usr":"X","eml":"y@x.com","pwd":123,"c_id":1,"card":"4111"}' $BASE/api/checkout   # P2-15 esperado: 400
st -H "$ADM" $BASE/api/admin/financial-report                                                             # P2-16 esperado: 200
```

O P2-16 confirma que o servidor continua no ar depois dos ataques.

**Excluir usuário não deixa registros órfãos:**

```bash
st -X DELETE -H "$ADM" $BASE/api/users/1   # P2-17 esperado: 200
curl -s -H "$ADM" $BASE/api/admin/financial-report
```

**P2-18 esperado:** o relatório não contém `Unknown` nem `Leonan`.

**O log não expõe dados de cartão.** Olhe as mensagens no **Terminal 1**.

**P2-19 esperado:** o cartão aparece só como `****4444`. O número `4111222233334444` e a chave `pk_live_` não podem aparecer em lugar nenhum.

### 4.6 Encerrar

No **Terminal 1**, pressione `Ctrl+C`. Depois volte à pasta principal:

```bash
cd ..
```

---

## Parte 5 — Projeto 3: Tarefas (`task-manager-api`)

### 5.1 Instalar

```bash
cd task-manager-api
python -m venv .venv
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
pip install -r requirements.txt
```

### 5.2 Rodar os testes automatizados

```bash
python -m unittest discover -s tests -t .
```

**Esperado** ao final:

```text
Ran 19 tests in ...s

OK
```

### 5.3 Confirmar que o arquivo de exemplo não abre a aplicação

```bash
cp .env.example .env
python app.py 2>&1 | tail -n 1
```

**Esperado:** a aplicação **recusa iniciar**, e a mensagem começa com:

```text
RuntimeError: Defina SECRET_KEY no ambiente ou no .env.
```

### 5.4 Configurar, popular o banco e criar o administrador

```bash
cat > .env <<EOF
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
ADMIN_EMAIL=admin@bancada.com
ADMIN_PASSWORD=senha-admin-bancada
PORT=5003
EOF
python seed.py
flask --app app create-admin
```

**Esperado:**

```text
3 usuários
4 categorias
10 tasks
Admin criado: id=4
```

Essas linhas aparecem junto de outras mensagens. No Windows, acentos podem sair trocados, e isso não é defeito.

### 5.5 Iniciar o servidor (Terminal 1)

```bash
python app.py
```

Deixe a janela aberta.

### 5.6 Preparar o Terminal 2

Abra outra janela, entre na pasta (`cd bancada-refactor/task-manager-api`) e cole:

```bash
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
BASE=http://127.0.0.1:5003
J='Content-Type: application/json'
st() { curl -s -o /dev/null -w "%{http_code}\n" "$@"; }
pega_token() { python -c "import sys,json; print(json.load(sys.stdin)['token'])"; }
```

### 5.7 Testes

**A aplicação funciona e exige login:**

```bash
st $BASE/health                                 # P3-01 esperado: 200
st $BASE/tasks                                  # P3-02 esperado: 401
st -X DELETE $BASE/tasks/1                      # P3-03 esperado: 401
st -H 'Authorization: Bearer fake-jwt-token-1' $BASE/users   # P3-04 esperado: 401
```

**As senhas antigas, que estavam publicadas no código, não entram mais:**

```bash
st -X POST -H "$J" -d '{"email":"joao@email.com","password":"1234"}' $BASE/login   # P3-05 esperado: 401
st -X POST -H "$J" -d '{"email":"maria@email.com","password":"abcd"}' $BASE/login  # P3-06 esperado: 401
```

**O administrador acessa tudo:**

```bash
ADMIN="Authorization: Bearer $(curl -s -X POST -H "$J" -d '{"email":"admin@bancada.com","password":"senha-admin-bancada"}' $BASE/login | pega_token)"
st -H "$ADMIN" $BASE/tasks             # P3-07 esperado: 200
st -H "$ADMIN" $BASE/tasks/stats       # P3-08 esperado: 200
st -H "$ADMIN" "$BASE/tasks/search?q=login"   # P3-09 esperado: 200
st -H "$ADMIN" $BASE/users             # P3-10 esperado: 200
st -H "$ADMIN" $BASE/categories        # P3-11 esperado: 200
st -H "$ADMIN" $BASE/reports/summary   # P3-12 esperado: 200
```

**A senha não sai na resposta:**

```bash
curl -s -H "$ADMIN" $BASE/users/1
```

**P3-13 esperado:** a resposta não contém o campo `password`.

**Cadastro público não cria conta privilegiada:**

```bash
st -X POST -H "$J" -d '{"name":"Hacker","email":"hacker@x.com","password":"senha123","role":"admin"}' $BASE/users   # P3-14 esperado: 403
st -X POST -H "$J" -d '{"name":"Comum","email":"comum@x.com","password":"senha123"}' $BASE/users                    # P3-15 esperado: 201
COMUM="Authorization: Bearer $(curl -s -X POST -H "$J" -d '{"email":"comum@x.com","password":"senha123"}' $BASE/login | pega_token)"
```

**Usuário comum não mexe no que é dos outros.** Estes são os testes mais importantes deste projeto:

```bash
st -X DELETE -H "$COMUM" $BASE/tasks/1          # P3-16 esperado: 403
st -X PUT -H "$J" -H "$COMUM" -d '{"title":"Invadida"}' $BASE/tasks/1   # P3-17 esperado: 403
st -X DELETE -H "$COMUM" $BASE/categories/1     # P3-18 esperado: 403
st -X DELETE -H "$COMUM" $BASE/users/1          # P3-19 esperado: 403
st -H "$COMUM" $BASE/users                      # P3-20 esperado: 403
st -H "$COMUM" $BASE/reports/summary            # P3-21 esperado: 403
```

**Usuário comum consegue trabalhar com o que é dele:**

```bash
st -H "$COMUM" $BASE/tasks                                              # P3-22 esperado: 200
st -X POST -H "$J" -H "$COMUM" -d '{"title":"Minha tarefa"}' $BASE/tasks   # P3-23 esperado: 201
```

**Entrada inválida é recusada:**

```bash
st -X POST -H "$J" -H "$COMUM" -d '{"title":"Teste","priority":"x"}' $BASE/tasks   # P3-24 esperado: 400
st -H "$COMUM" "$BASE/tasks/search?priority=abc"                                   # P3-25 esperado: 400
```

### 5.8 Encerrar

No **Terminal 1**, pressione `Ctrl+C`.

---

## Parte 6 — Folha de Resultados

Preencha e anexe ao seu relatório. Em caso de falha, anote o código obtido.

| Item | Critério | Resultado (OK / Falhou) | Observação |
|---|---|---|---|
| Parte 2 | `TUDO OK` no teste automático | | |
| **Projeto 1** | | | |
| 3.2 | 16 testes OK | | |
| 3.3 | Recusa iniciar com o `.env` de exemplo | | |
| 3.4 | Admin criado | | |
| P1-01 a P1-21 | Todos conforme o esperado | | |
| **Projeto 2** | | | |
| 4.1 | 10 testes, 0 falhas | | |
| P2-01 a P2-19 | Todos conforme o esperado | | |
| **Projeto 3** | | | |
| 5.2 | 19 testes OK | | |
| 5.3 | Recusa iniciar com o `.env` de exemplo | | |
| 5.4 | Seed e admin criados | | |
| P3-01 a P3-25 | Todos conforme o esperado | | |

**Data:** ______ **Testador:** ______ **Commit** (`git log -1 --oneline`): ______ **Sistema operacional:** ______

---

## Parte 7 — O que realmente é crítico

Se o tempo for curto, valide nesta ordem. **Qualquer falha em "Bloqueador" reprova a bancada**, mesmo com todo o resto certo.

### Bloqueadores

| # | O que validar | Testes | Por que é crítico |
|---|---|---|---|
| 1 | Os 3 projetos instalam e iniciam seguindo este guia | 3.1, 3.5, 4.1, 4.4, 5.1, 5.5 | É o critério obrigatório do desafio. Sem isso, nada mais importa |
| 2 | Funções originais continuam respondendo | P1-01 a P1-03, P2-06 a P2-09, P3-07 a P3-12 | A refatoração não pode quebrar o sistema |
| 3 | Segredo de exemplo não abre o sistema | 3.3, 5.3, P2-01 | Quem copia o exemplo não pode subir com uma credencial pública |
| 4 | Senhas publicadas no código antigo não entram | P1-08, P1-09, P2-13, P3-05, P3-06 | Motivo de uma reprovação anterior |
| 5 | Rotas administrativas exigem credencial | P1-04 a P1-06, P2-02 a P2-05, P3-02 a P3-04 | Motivo de uma reprovação anterior. Sem isso, qualquer pessoa lê e apaga dados |
| 6 | Um usuário não acessa o que é de outro | P1-16, P1-18, P2-11, P2-12, P3-14, P3-16 a P3-21 | Login sem controle de permissão equivale a sistema aberto |
| 7 | Uma requisição anônima não derruba o servidor | P2-14 a P2-16 | No original, uma única requisição tirava a API do ar |
| 8 | Ataque de SQL Injection não extrai dados | P1-10 | No original, permitia ler as senhas de todos |
| 9 | Testes automatizados passam | 3.2, 4.1, 5.2 | Reúnem cenários que não são repetidos à mão |

### Importantes (registrar, mas não reprovam sozinhos)

| O que validar | Testes |
|---|---|
| Dados sensíveis fora das respostas e do log | P1-11, P2-19, P3-13 |
| Entrada inválida recebe 400 em vez de 500 | P1-20, P2-08, P3-24, P3-25 |
| Excluir usuário não deixa registros órfãos | P2-17, P2-18 |
| Comando de criação de admin | 3.4, 5.4 |

> **Atenção à classificação:** se um item "Importante" der **500 ou derrubar o servidor**, trate como bloqueador (item 7).

### Não é defeito (não perca tempo)

- Avisos do `pip` ou do `npm`, incluindo `npm audit` e versão nova do pip.
- `WARNING: This is a development server` ao iniciar o Flask.
- Acentos trocados no terminal do Windows.
- Horários, identificadores e tempo de execução diferentes dos exemplos.
- Respostas 401 e 403 nos testes de segurança: são o resultado correto.

### Limitações já conhecidas (não abra como defeito novo)

Estão documentadas na seção "Limitações Conhecidas" do `README.md`. Por exemplo: cancelar pedido não devolve estoque, CORS aberto e senha mínima de 4 caracteres no projeto 3.

---

## Parte 8 — Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `python: command not found` | Python fora do PATH, ou instalado como `python3` | Reinstale marcando "Add Python to PATH" (Windows) ou use `python3` (Linux/macOS) |
| `flask: command not found` | Ambiente virtual desativado | Rode `source .venv/Scripts/activate 2>/dev/null \|\| source .venv/bin/activate` na pasta do projeto |
| `Address already in use` ou `EADDRINUSE` | Outro programa usa a porta | Pare o outro programa, ou troque o `PORT` no `.env` e o `BASE` no Terminal 2 |
| Código `000` em todos os testes | Servidor parado | Veja o Terminal 1. Se parou com erro, anote a mensagem e reinicie |
| `st: command not found` | Terminal novo, sem a preparação | Cole de novo o bloco que define `BASE`, `J` e `st` |
| `RuntimeError: Defina SECRET_KEY` fora dos passos 3.3 e 5.3 | `.env` ainda é a cópia do exemplo | Refaça o passo de configuração (3.4 ou 5.4) |
| Erro ao instalar o `sqlite3` no `npm install` | Falta pacote pronto para a sua versão do Node | Use uma versão LTS do Node.js, apague `node_modules` e rode `npm install` de novo |
| `KeyError: 'token'` ou token vazio | Login falhou | Confira se o admin foi criado e se o servidor está no ar |
| Quer refazer um projeto do zero | Dados da rodada anterior | Projeto 1: pare o servidor e refaça a partir do 3.4. Projeto 2: só reinicie o servidor. Projeto 3: pare o servidor e refaça a partir do 5.4 |
| Códigos diferentes do esperado em P1-12, P1-15 ou P3-15 | Rodada anterior deixou dados | Refaça o projeto do zero, conforme a linha acima |

Se persistir, registre na Folha de Resultados o comando executado, a mensagem completa e o resultado de `git log -1 --oneline`.

---

## Parte 9 — Roteiro para PowerShell (Windows)

Este é o mesmo roteiro das Partes 1 a 5, para quem prefere o PowerShell ao Git Bash. Os números das seções e dos testes são os mesmos, e os resultados esperados também. Por isso, a [Folha de Resultados](#parte-6--folha-de-resultados) e a [Parte 7](#parte-7--o-que-realmente-é-crítico) continuam valendo.

Funciona no Windows PowerShell 5.1 (já vem com o Windows) e no PowerShell 7. Os textos de explicação abaixo são curtos: em caso de dúvida sobre um passo, consulte a seção de mesmo número no roteiro principal.

### Preparar a máquina

**1.1 e 1.2.** Instale os programas da [seção 1.1](#11-instalar-os-programas) e abra o PowerShell. Depois, libere a execução de scripts, que o `npm` e o ambiente virtual do Python precisam. A liberação vale só para esta janela:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
```

**1.3 Conferir a instalação.** Cada comando deve mostrar um número de versão:

```powershell
git --version
python --version
node --version
npm --version
curl.exe --version
```

> Use sempre `curl.exe`, com a extensão. No PowerShell 5.1, `curl` sem extensão é outro comando, com outras opções.

**1.4 Baixar o projeto:**

```powershell
git clone https://github.com/claudionk/mba-ia-refactor-projects-skill.git bancada-refactor
cd bancada-refactor
```

### Teste automático (Parte 2)

```powershell
python scripts/verify_clean_clone.py
```

**Resultado esperado:** todas as linhas com `[PASS]` e, na última, `TUDO OK`.

### Projeto 1: Loja (Parte 3)

**3.1 Instalar.** O início da linha deve passar a mostrar `(.venv)`:

```powershell
cd code-smells-project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**3.2 Rodar os testes automatizados.** Esperado ao final: `Ran 16 tests` e `OK`.

```powershell
python -m unittest discover -s tests -t .
```

**3.3 Confirmar que o arquivo de exemplo não abre a aplicação.** Esperado: a última linha começa com `RuntimeError: Defina SECRET_KEY no ambiente ou no .env.`

```powershell
Copy-Item .env.example .env
python app.py 2>&1 | ForEach-Object { "$_" } | Select-Object -Last 1
```

**3.4 Configurar e criar o administrador.** Esperado: `Admin criado: id=1`.

```powershell
Remove-Item loja.db -ErrorAction SilentlyContinue
$segredo = python -c "import secrets; print(secrets.token_hex(32))"
@"
SECRET_KEY=$segredo
ADMIN_TOKEN=bancada-admin-token
ADMIN_EMAIL=admin@bancada.com
ADMIN_PASSWORD=senha-admin-bancada
PORT=5001
DB_PATH=loja.db
"@ | Set-Content .env -Encoding ascii
flask --app app criar-admin
```

> Os valores acima servem só para esta bancada. Mantenha `-Encoding ascii`: outras codificações podem corromper a primeira linha do `.env` no PowerShell 5.1.

**3.5 Iniciar o servidor (Terminal 1).** O terminal fica "preso" mostrando mensagens, e isso é o normal. **Deixe esta janela aberta.**

```powershell
python app.py
```

**3.6 Preparar o Terminal 2.** Abra **outra janela** do PowerShell e cole:

```powershell
$BASE = 'http://127.0.0.1:5001'
$J = 'Content-Type: application/json'
$ADM = 'X-Admin-Token: bancada-admin-token'
function st { curl.exe -s -o NUL -w '%{http_code}\n' @args }
function corpo($json) { $arquivo = Join-Path $env:TEMP 'bancada-corpo.json'; [IO.File]::WriteAllText($arquivo, $json); "@$arquivo" }
```

`st` mostra só o código de resposta. `corpo` grava o JSON em um arquivo temporário e o entrega ao `curl.exe`, o que evita o problema das aspas nos argumentos do PowerShell. Cole os blocos abaixo **em ordem** e compare cada número com o valor de `esperado`.

**3.7 Testes.** A aplicação funciona:

```powershell
st "$BASE/health"                     # P1-01 esperado: 200
st "$BASE/produtos"                   # P1-02 esperado: 200
st "$BASE/produtos/busca?q=Mouse"     # P1-03 esperado: 200
```

Rotas administrativas estão protegidas:

```powershell
st "$BASE/usuarios"                                  # P1-04 esperado: 401
st -H 'X-Admin-Token: errado' "$BASE/usuarios"       # P1-05 esperado: 401
st -H $ADM "$BASE/usuarios"                          # P1-06 esperado: 200
st -X POST -H $J -d (corpo '{"sql":"SELECT 1"}') "$BASE/admin/query"   # P1-07 esperado: 404
```

As senhas antigas, que estavam publicadas no código, não entram mais:

```powershell
st -X POST -H $J -d (corpo '{"email":"admin@loja.com","senha":"admin123"}') "$BASE/login"   # P1-08 esperado: 401
st -X POST -H $J -d (corpo '{"email":"joao@email.com","senha":"123456"}') "$BASE/login"     # P1-09 esperado: 401
```

O ataque de SQL Injection não extrai dados. **P1-10 esperado:** o campo `dados` vem vazio (`"dados":[]`) e nenhum e-mail aparece.

```powershell
curl.exe -s -G --data-urlencode "q=x%') UNION SELECT id,nome,email,senha,tipo,criado_em,NULL,NULL FROM usuarios --" "$BASE/produtos/busca"
```

Segredos não aparecem no monitoramento. **P1-11 esperado:** a resposta não contém `secret_key` nem `db_path`.

```powershell
curl.exe -s "$BASE/health"
```

Cada cliente só acessa os próprios pedidos. Primeiro, crie duas clientes e faça login com a Ana:

```powershell
st -X POST -H $J -d (corpo '{"nome":"Ana","email":"ana@x.com","senha":"senha-ana"}') "$BASE/usuarios"   # P1-12 esperado: 201
st -X POST -H $J -d (corpo '{"nome":"Bia","email":"bia@x.com","senha":"senha-bia"}') "$BASE/usuarios"   # P1-13 esperado: 201
$TOKEN = (curl.exe -s -X POST -H $J -d (corpo '{"email":"ana@x.com","senha":"senha-ana"}') "$BASE/login" | ConvertFrom-Json).token
$ANA = "Authorization: Bearer $TOKEN"
```

Na bancada, o admin é o usuário 1, a Ana é o usuário 2 e a Bia é o usuário 3.

```powershell
$PEDIDO_ANA = '{"usuario_id":2,"itens":[{"produto_id":1,"quantidade":1}]}'
$PEDIDO_BIA = '{"usuario_id":3,"itens":[{"produto_id":1,"quantidade":1}]}'
st -X POST -H $J -d (corpo $PEDIDO_ANA) "$BASE/pedidos"             # P1-14 esperado: 401
st -X POST -H $J -H $ANA -d (corpo $PEDIDO_ANA) "$BASE/pedidos"     # P1-15 esperado: 201
st -X POST -H $J -H $ANA -d (corpo $PEDIDO_BIA) "$BASE/pedidos"     # P1-16 esperado: 403
st -H $ANA "$BASE/pedidos/usuario/2"                                # P1-17 esperado: 200
st -H $ANA "$BASE/pedidos/usuario/3"                                # P1-18 esperado: 403
st "$BASE/pedidos/usuario/2"                                        # P1-19 esperado: 401
```

Entrada inválida é recusada:

```powershell
st -X POST -H $J -H $ANA -d (corpo '{"usuario_id":2,"itens":[{"produto_id":1,"quantidade":-100}]}') "$BASE/pedidos"   # P1-20 esperado: 400
st -X POST -H $J -d (corpo '{"email":"admin@bancada.com","senha":"senha-admin-bancada"}') "$BASE/login"               # P1-21 esperado: 200
```

**3.8 Encerrar.** No **Terminal 1**, pressione `Ctrl+C`. Depois volte à pasta principal:

```powershell
cd ..
```

### Projeto 2: Cursos (Parte 4)

**4.1 Instalar e rodar os testes automatizados.** Esperado ao final: `tests 10`, `pass 10` e `fail 0`.

```powershell
cd ecommerce-api-legacy
npm install
npm test
```

**4.2 Confirmar que o arquivo de exemplo não abre as rotas administrativas.**

```powershell
Copy-Item .env.example .env
Add-Content .env 'PORT=3101' -Encoding ascii
```

**Terminal 1:**

```powershell
npm start
```

**Terminal 2:** abra outra janela do PowerShell e cole. O token de exemplo é público, então não pode dar acesso.

```powershell
$BASE = 'http://127.0.0.1:3101'
$J = 'Content-Type: application/json'
$ADM = 'x-admin-token: bancada-admin-token'
function st { curl.exe -s -o NUL -w '%{http_code}\n' @args }
function corpo($json) { $arquivo = Join-Path $env:TEMP 'bancada-corpo.json'; [IO.File]::WriteAllText($arquivo, $json); "@$arquivo" }
st -H 'x-admin-token: troque-por-um-token-admin-forte' "$BASE/api/admin/financial-report"   # P2-01 esperado: 403
```

Agora, no **Terminal 1**, pressione `Ctrl+C`.

**4.3 Configurar.** No **Terminal 1**:

```powershell
@"
PORT=3101
DB_PATH=:memory:
ADMIN_TOKEN=bancada-admin-token
"@ | Set-Content .env -Encoding ascii
```

**4.4 Iniciar o servidor (Terminal 1).** Esperado: uma mensagem com `rodando na porta 3101`. Deixe a janela aberta.

```powershell
npm start
```

**4.5 Testes (Terminal 2).** Rotas administrativas estão protegidas:

```powershell
st "$BASE/api/admin/financial-report"                                # P2-02 esperado: 401
st -H 'x-admin-token: errado' "$BASE/api/admin/financial-report"     # P2-03 esperado: 401
st -H $ADM "$BASE/api/admin/financial-report"                        # P2-04 esperado: 200
st -X DELETE "$BASE/api/users/1"                                     # P2-05 esperado: 401
```

O checkout funciona. `card` iniciado em `4` é aprovado; os demais são recusados:

```powershell
$COMPRA = '{"usr":"Gui","eml":"gui@x.com","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
st -X POST -H $J -d (corpo $COMPRA) "$BASE/api/checkout"    # P2-06 esperado: 200
st -X POST -H $J -d (corpo '{"usr":"Joao","eml":"joao@x.com","pwd":"abc","c_id":1,"card":"5111222233334444"}') "$BASE/api/checkout"   # P2-07 esperado: 400
st -X POST -H $J -d (corpo '{}') "$BASE/api/checkout"       # P2-08 esperado: 400
st -X POST -H $J -d (corpo '{"usr":"Gui","eml":"novo@x.com","pwd":"abc","c_id":99,"card":"4111"}') "$BASE/api/checkout"   # P2-09 esperado: 404
```

Ninguém compra em nome de outra conta sem a senha dela. O e-mail `gui@x.com` foi criado acima:

```powershell
st -X POST -H $J -d (corpo '{"usr":"Gui","eml":"gui@x.com","pwd":"senhaforte","c_id":1,"card":"4111222233334444"}') "$BASE/api/checkout"   # P2-10 esperado: 200
st -X POST -H $J -d (corpo '{"usr":"Gui","eml":"gui@x.com","pwd":"errada","c_id":1,"card":"4111222233334444"}') "$BASE/api/checkout"       # P2-11 esperado: 401
st -X POST -H $J -d (corpo '{"usr":"Gui","eml":"gui@x.com","c_id":1,"card":"4111222233334444"}') "$BASE/api/checkout"                      # P2-12 esperado: 401
st -X POST -H $J -d (corpo '{"usr":"X","eml":"leonan@fullcycle.com.br","pwd":"123","c_id":1,"card":"4111222233334444"}') "$BASE/api/checkout"   # P2-13 esperado: 401
```

As entradas que derrubavam o servidor original agora são recusadas. O P2-16 confirma que o servidor continua no ar depois dos ataques:

```powershell
st -X POST -H $J -d (corpo '{"usr":"X","eml":"x@x.com","pwd":"abc","c_id":1,"card":123}') "$BASE/api/checkout"    # P2-14 esperado: 400
st -X POST -H $J -d (corpo '{"usr":"X","eml":"y@x.com","pwd":123,"c_id":1,"card":"4111"}') "$BASE/api/checkout"   # P2-15 esperado: 400
st -H $ADM "$BASE/api/admin/financial-report"                                                                     # P2-16 esperado: 200
```

Excluir usuário não deixa registros órfãos. **P2-18 esperado:** o relatório não contém `Unknown` nem `Leonan`.

```powershell
st -X DELETE -H $ADM "$BASE/api/users/1"   # P2-17 esperado: 200
curl.exe -s -H $ADM "$BASE/api/admin/financial-report"
```

O log não expõe dados de cartão. Olhe as mensagens no **Terminal 1**. **P2-19 esperado:** o cartão aparece só como `****4444`. O número `4111222233334444` e a chave `pk_live_` não podem aparecer em lugar nenhum.

**4.6 Encerrar.** No **Terminal 1**, pressione `Ctrl+C`. Depois volte à pasta principal:

```powershell
cd ..
```

### Projeto 3: Tarefas (Parte 5)

**5.1 Instalar:**

```powershell
cd task-manager-api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**5.2 Rodar os testes automatizados.** Esperado ao final: `Ran 19 tests` e `OK`.

```powershell
python -m unittest discover -s tests -t .
```

**5.3 Confirmar que o arquivo de exemplo não abre a aplicação.** Esperado: a última linha começa com `RuntimeError: Defina SECRET_KEY no ambiente ou no .env.`

```powershell
Copy-Item .env.example .env
python app.py 2>&1 | ForEach-Object { "$_" } | Select-Object -Last 1
```

**5.4 Configurar, popular o banco e criar o administrador.** Esperado, junto de outras mensagens: `3 usuários`, `4 categorias`, `10 tasks` e `Admin criado: id=4`. Acentos podem sair trocados, e isso não é defeito.

```powershell
$segredo = python -c "import secrets; print(secrets.token_hex(32))"
@"
SECRET_KEY=$segredo
ADMIN_EMAIL=admin@bancada.com
ADMIN_PASSWORD=senha-admin-bancada
PORT=5003
"@ | Set-Content .env -Encoding ascii
python seed.py
flask --app app create-admin
```

**5.5 Iniciar o servidor (Terminal 1).** Deixe a janela aberta.

```powershell
python app.py
```

**5.6 Preparar o Terminal 2.** Abra outra janela do PowerShell e cole:

```powershell
$BASE = 'http://127.0.0.1:5003'
$J = 'Content-Type: application/json'
function st { curl.exe -s -o NUL -w '%{http_code}\n' @args }
function corpo($json) { $arquivo = Join-Path $env:TEMP 'bancada-corpo.json'; [IO.File]::WriteAllText($arquivo, $json); "@$arquivo" }
function pega_token($json) { (curl.exe -s -X POST -H $J -d (corpo $json) "$BASE/login" | ConvertFrom-Json).token }
```

**5.7 Testes.** A aplicação funciona e exige login:

```powershell
st "$BASE/health"                               # P3-01 esperado: 200
st "$BASE/tasks"                                # P3-02 esperado: 401
st -X DELETE "$BASE/tasks/1"                    # P3-03 esperado: 401
st -H 'Authorization: Bearer fake-jwt-token-1' "$BASE/users"   # P3-04 esperado: 401
```

As senhas antigas, que estavam publicadas no código, não entram mais:

```powershell
st -X POST -H $J -d (corpo '{"email":"joao@email.com","password":"1234"}') "$BASE/login"   # P3-05 esperado: 401
st -X POST -H $J -d (corpo '{"email":"maria@email.com","password":"abcd"}') "$BASE/login"  # P3-06 esperado: 401
```

O administrador acessa tudo:

```powershell
$ADMIN = "Authorization: Bearer $(pega_token '{"email":"admin@bancada.com","password":"senha-admin-bancada"}')"
st -H $ADMIN "$BASE/tasks"             # P3-07 esperado: 200
st -H $ADMIN "$BASE/tasks/stats"       # P3-08 esperado: 200
st -H $ADMIN "$BASE/tasks/search?q=login"   # P3-09 esperado: 200
st -H $ADMIN "$BASE/users"             # P3-10 esperado: 200
st -H $ADMIN "$BASE/categories"        # P3-11 esperado: 200
st -H $ADMIN "$BASE/reports/summary"   # P3-12 esperado: 200
```

A senha não sai na resposta. **P3-13 esperado:** a resposta não contém o campo `password`.

```powershell
curl.exe -s -H $ADMIN "$BASE/users/1"
```

Cadastro público não cria conta privilegiada:

```powershell
st -X POST -H $J -d (corpo '{"name":"Hacker","email":"hacker@x.com","password":"senha123","role":"admin"}') "$BASE/users"   # P3-14 esperado: 403
st -X POST -H $J -d (corpo '{"name":"Comum","email":"comum@x.com","password":"senha123"}') "$BASE/users"                    # P3-15 esperado: 201
$COMUM = "Authorization: Bearer $(pega_token '{"email":"comum@x.com","password":"senha123"}')"
```

Usuário comum não mexe no que é dos outros. Estes são os testes mais importantes deste projeto:

```powershell
st -X DELETE -H $COMUM "$BASE/tasks/1"          # P3-16 esperado: 403
st -X PUT -H $J -H $COMUM -d (corpo '{"title":"Invadida"}') "$BASE/tasks/1"   # P3-17 esperado: 403
st -X DELETE -H $COMUM "$BASE/categories/1"     # P3-18 esperado: 403
st -X DELETE -H $COMUM "$BASE/users/1"          # P3-19 esperado: 403
st -H $COMUM "$BASE/users"                      # P3-20 esperado: 403
st -H $COMUM "$BASE/reports/summary"            # P3-21 esperado: 403
```

Usuário comum consegue trabalhar com o que é dele:

```powershell
st -H $COMUM "$BASE/tasks"                                                # P3-22 esperado: 200
st -X POST -H $J -H $COMUM -d (corpo '{"title":"Minha tarefa"}') "$BASE/tasks"   # P3-23 esperado: 201
```

Entrada inválida é recusada:

```powershell
st -X POST -H $J -H $COMUM -d (corpo '{"title":"Teste","priority":"x"}') "$BASE/tasks"   # P3-24 esperado: 400
st -H $COMUM "$BASE/tasks/search?priority=abc"                                           # P3-25 esperado: 400
```

**5.8 Encerrar.** No **Terminal 1**, pressione `Ctrl+C`.

### Problemas comuns no PowerShell

Valem também os itens da [Parte 8](#parte-8--problemas-comuns). Estes são exclusivos do PowerShell:

| Sintoma | Causa provável | Solução |
|---|---|---|
| `a execução de scripts foi desabilitada neste sistema` ao rodar `npm` ou `Activate.ps1` | Política de execução do Windows | Rode o comando `Set-ExecutionPolicy` da seção 1.2 nesta janela |
| `flask` não é reconhecido | Ambiente virtual desativado | Rode `.\.venv\Scripts\Activate.ps1` na pasta do projeto |
| `st` ou `corpo` não é reconhecido | Terminal novo, sem a preparação | Cole de novo o bloco que define `$BASE`, `$J`, `st` e `corpo` |
| Erro sobre `-H` ou `Invoke-WebRequest` | Comando digitado com `curl` em vez de `curl.exe` | Use `curl.exe`, com a extensão |
| `RuntimeError: Defina SECRET_KEY` mesmo depois de configurar | `.env` gravado com outra codificação | Refaça o passo de configuração mantendo `-Encoding ascii` |
