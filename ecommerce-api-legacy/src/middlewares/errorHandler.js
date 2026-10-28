const logger = require('../utils/logger');

// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
    const status = err.status || err.statusCode || 500;
    if (status >= 500) {
        logger.error(`Erro não tratado em ${req.method} ${req.originalUrl}`, err);
        return res.status(500).send('Erro interno do servidor');
    }
    return res.status(status).send(err.message);
}

module.exports = errorHandler;
