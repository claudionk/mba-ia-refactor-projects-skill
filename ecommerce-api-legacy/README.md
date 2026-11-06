# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Exemplos de requisições estão em `api.http`.

## Testes

```bash
npm test
```

## Configuração

Copie `.env.example` para `.env` e defina `ADMIN_TOKEN` (gere com `node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"`). `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem o header `x-admin-token` com esse valor:

- `ADMIN_TOKEN` não configurado, ou igual ao placeholder do exemplo: `403`
- Header ausente ou inválido: `401`

`POST /api/checkout` com um e-mail já cadastrado exige a senha dessa conta em `pwd`; caso contrário, responde `401`.

O usuário do seed existe porque a matrícula e o pagamento de exemplo dependem dele. A senha dele é aleatória, gerada a cada boot, e não é conhecida por ninguém.
