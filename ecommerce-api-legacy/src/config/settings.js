require('dotenv').config({ quiet: true });

const PLACEHOLDER_PREFIX = 'troque-por-';

// Placeholder do .env.example nunca vale como credencial.
const secret = (value) => (value && !value.startsWith(PLACEHOLDER_PREFIX) ? value : undefined);

module.exports = {
    port: Number(process.env.PORT) || 3000,
    dbPath: process.env.DB_PATH || ':memory:',
    paymentGatewayKey: secret(process.env.PAYMENT_GATEWAY_KEY),
    adminToken: secret(process.env.ADMIN_TOKEN),
};
