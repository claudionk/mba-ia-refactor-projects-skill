# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo.

## Configuração

Toda configuração vem de variáveis de ambiente (ver `.env.example`). O projeto não lê `.env` sozinho: exporte as variáveis no shell ou use seu gerenciador de ambiente.

| Variável      | Padrão      | Função                                                                 |
|---------------|-------------|------------------------------------------------------------------------|
| `SECRET_KEY`  | aleatória   | Chave da aplicação. Sem valor, é gerada a cada boot.                   |
| `ADMIN_TOKEN` | vazio       | Token das rotas administrativas. Vazio = rotas admin desabilitadas.    |
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
