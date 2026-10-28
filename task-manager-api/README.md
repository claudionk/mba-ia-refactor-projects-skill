# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. Diferente dos outros projetos, este já possui alguma separação de camadas (`models/`, `routes/`, `services/`, `utils/`), mas ainda contém problemas arquiteturais e de qualidade.

## Como rodar

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

A aplicação sobe em `http://localhost:5000`. O `seed.py` popula o banco SQLite (`tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias.

## Estrutura (MVC)

```
app.py              entry point (create_app, blueprints, error handlers)
config/             settings.py (env vars) e constants.py
models/             entidades + acesso a dados (task, user, category)
controllers/        regras de negócio (task, user, category, report)
routes/             blueprints HTTP finos
middlewares/        error_handler.py
services/           notification_service.py
utils/              errors, validators, time_utils
```

Configuração via variáveis de ambiente (veja `.env.example`): `SECRET_KEY`, `DATABASE_URL`, `DEBUG`, `HOST`, `PORT`, `SMTP_*`.

Notas: o campo `password` não é mais retornado pela API; senhas agora usam PBKDF2 (hashes MD5 antigos são migrados no primeiro login). 
## Autenticacao

`POST /login` devolve um token assinado (itsdangerous, usa `SECRET_KEY`, validade `TOKEN_TTL_SECONDS`, padrão 8h). Envie `Authorization: Bearer <token>` em todas as rotas, exceto `/`, `/health`, `/login` e `POST /users` (cadastro).

- `POST /users` com `role` diferente de `user`: só admin.
- `PUT /users/<id>`: o próprio usuário ou admin; alterar `role`: só admin.
- `DELETE /users/<id>`: só admin.
- Sem `SECRET_KEY` a aplicação não inicia fora do modo `DEBUG`.
