const crypto = require('crypto');
const settings = require('../config/settings');
const AppError = require('../utils/AppError');

function tokensMatch(received, expected) {
    const a = Buffer.from(received);
    const b = Buffer.from(expected);
    return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// Deny-by-default: sem ADMIN_TOKEN configurado as rotas admin ficam desabilitadas (403).
function adminAuth(req, res, next) {
    if (!settings.adminToken) {
        return next(new AppError(403, 'Operação administrativa desabilitada: ADMIN_TOKEN não configurado'));
    }
    if (!tokensMatch(req.get('x-admin-token') || '', settings.adminToken)) {
        return next(new AppError(401, 'Unauthorized'));
    }
    return next();
}

module.exports = adminAuth;
