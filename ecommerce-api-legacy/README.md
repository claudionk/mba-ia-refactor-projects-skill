# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Exemplos de requisições estão em `api.http`.

## Configuração

Copie `.env.example` para `.env` e troque os valores. `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem o header `x-admin-token` com o valor de `ADMIN_TOKEN`:

- `ADMIN_TOKEN` não configurado: `403`
- Header ausente ou inválido: `401`

O usuário do seed existe porque a matrícula e o pagamento de exemplo dependem dele. A senha dele é aleatória, gerada a cada boot, e não é conhecida por ninguém.
