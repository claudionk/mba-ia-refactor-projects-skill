# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. Diferente dos outros projetos, este já possui alguma separação de camadas (`models/`, `routes/`, `services/`, `utils/`), mas ainda contém problemas arquiteturais e de qualidade.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env
```

No `.env`, defina `SECRET_KEY` (gere com `python -c "import secrets; print(secrets.token_hex(32))"`), `ADMIN_EMAIL` e `ADMIN_PASSWORD`. Depois:

```bash
python seed.py                  # usuários, categorias e tasks de exemplo
flask --app app create-admin    # conta admin
python app.py
```

A aplicação sobe em `http://localhost:5000`. Exemplos de requisições estão em `api.http`.

## Testes

```bash
python -m unittest discover -s tests -t .
```

## Estrutura (MVC)

```
app.py              entry point (create_app, blueprints, error handlers)
config/             settings.py (env vars) e constants.py
models/             entidades + acesso a dados (task, user, category)
controllers/        regras de negócio (task, user, category, report)
routes/             blueprints HTTP finos
middlewares/        error_handler.py
services/           notification_service.py
utils/              errors, permissions, validators, time_utils
```

Configuração via variáveis de ambiente (veja `.env.example`): `SECRET_KEY`, `DATABASE_URL`, `DEBUG`, `HOST`, `PORT`, `SMTP_*`.

Notas: o campo `password` não é mais retornado pela API; senhas agora usam PBKDF2 (hashes MD5 antigos são migrados no primeiro login). 
## Autenticação e permissões

`POST /login` devolve um token assinado, com validade de `TOKEN_TTL_SECONDS` (padrão: 8h). Envie `Authorization: Bearer <token>`. Sem `SECRET_KEY`, ou com o placeholder do `.env.example`, a aplicação não inicia.

| Rota | Quem pode |
|---|---|
| `GET /`, `GET /health`, `POST /login` | Qualquer um |
| `POST /users` | Qualquer um, com `role: user`; outro papel só admin |
| `GET /users` | Admin e manager |
| `GET /users/<id>`, `GET /users/<id>/tasks` | O próprio, admin e manager |
| `PUT /users/<id>` | O próprio e admin; alterar `role` só admin |
| `DELETE /users/<id>` | Admin |
| `GET /tasks`, `/tasks/<id>`, `/tasks/search`, `/tasks/stats` | Qualquer usuário logado |
| `POST /tasks` | Qualquer usuário logado; atribuir a outro só admin e manager |
| `PUT /tasks/<id>`, `DELETE /tasks/<id>` | O dono, admin e manager |
| `GET /categories` | Qualquer usuário logado |
| `POST`, `PUT` e `DELETE /categories` | Admin e manager |
| `GET /reports/summary` | Admin e manager |
| `GET /reports/user/<id>` | O próprio, admin e manager |

As senhas usam PBKDF2 e não são retornadas pela API. Hashes MD5 antigos são migrados no primeiro login válido.

> **Banco criado por versões anteriores:** o seed antigo criava contas com senhas publicadas no repositório. Rode `python seed.py` de novo para substituí-las, pois ele recria os usuários.
