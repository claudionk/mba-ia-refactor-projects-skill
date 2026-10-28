const express = require('express');
const settings = require('./config/settings');
const initDb = require('./database/init');
const routes = require('./routes');
const errorHandler = require('./middlewares/errorHandler');
const logger = require('./utils/logger');

async function start() {
    await initDb();

    const app = express();
    app.use(express.json());
    app.use(routes);
    app.use(errorHandler);

    app.listen(settings.port, () => {
        logger.info(`Frankenstein LMS rodando na porta ${settings.port}...`);
    });
}

start().catch((err) => {
    logger.error('Falha ao iniciar a aplicação', err);
    process.exit(1);
});
