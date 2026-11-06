# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # troque os valores
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos de exemplo. O seed não cria usuários: clientes se cadastram por `POST /usuarios` e a conta admin é criada pelo comando abaixo.

## Conta administrativa

```bash
ADMIN_EMAIL=voce@exemplo.com ADMIN_PASSWORD='uma-senha-forte' flask --app app criar-admin
```

Sem as duas variáveis, o comando falha e nenhuma conta é criada.

> **Banco criado por versões anteriores:** o seed antigo criava `admin@loja.com`, `joao@email.com` e `maria@email.com` com senhas publicadas no repositório. Remover o seed não revoga essas contas. Apague o `loja.db` para recriar o banco.

## Configuração

Toda configuração vem de variáveis de ambiente, lidas do shell ou do arquivo `.env` na raiz do projeto (ver `.env.example`). Variáveis do shell têm prioridade.

| Variável      | Padrão      | Função                                                                 |
|---------------|-------------|------------------------------------------------------------------------|
| `SECRET_KEY`  | obrigatória | Chave da aplicação. Sem valor, a aplicação não inicia.                 |
| `ADMIN_TOKEN` | vazio       | Token das rotas administrativas. Vazio = rotas admin desabilitadas.    |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | vazio | Dados da conta criada por `criar-admin`. Vazio = o comando falha. |
| `DEBUG`       | `false`     | Modo debug do Flask. Não use em produção.                              |
| `HOST`        | `127.0.0.1` | Interface de escuta.                                                   |
| `PORT`        | `5000`      | Porta HTTP.                                                            |
| `DB_PATH`     | `loja.db`   | Caminho do arquivo SQLite.                                             |

## Autenticação administrativa

Rotas administrativas exigem o header `X-Admin-Token` com o valor de `ADMIN_TOKEN`:

- `GET /usuarios`, `GET /usuarios/<id>`
- `GET /pedidos`, `PUT /pedidos/<id>/status`
- `POST /produtos`, `PUT /produtos/<id>`, `DELETE /produtos/<id>`
- `GET /relatorios/vendas`
- `POST /admin/reset-db`

Sem token: `401`. Token inválido: `401`. `ADMIN_TOKEN` não configurado: `403`.

### Rotas públicas

As demais rotas não exigem token. Elas formam o fluxo de um cliente da loja e precisam ficar acessíveis sem credencial administrativa:

- Catálogo: `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>`
- Cadastro, login e pedidos: `POST /usuarios`, `POST /login`, `POST /pedidos`
- Pedidos de um usuário: `GET /pedidos/usuario/<id>`
- Monitoramento: `GET /`, `GET /health`

> **Atenção:** `GET /pedidos/usuario/<id>` não valida o dono do pedido. Qualquer pessoa consegue ler os pedidos de outro usuário. Pendência conhecida, fora do escopo atual.

Senhas são armazenadas com hash (`werkzeug.security`). Contas criadas antes desta versão, com senha em texto puro, são migradas no primeiro login bem-sucedido.
