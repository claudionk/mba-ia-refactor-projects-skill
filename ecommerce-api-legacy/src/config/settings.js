require('dotenv').config({ quiet: true });

module.exports = {
    port: Number(process.env.PORT) || 3000,
    dbPath: process.env.DB_PATH || ':memory:',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY,
    adminToken: process.env.ADMIN_TOKEN,
    seedUserPassword: process.env.SEED_USER_PASSWORD,
};
