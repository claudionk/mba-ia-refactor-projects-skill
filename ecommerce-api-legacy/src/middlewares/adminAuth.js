const settings = require('../config/settings');
const AppError = require('../utils/AppError');

// Opt-in: só exige token quando ADMIN_TOKEN estiver configurado, preservando o contrato atual.
function adminAuth(req, res, next) {
    if (!settings.adminToken) return next();
    if (req.get('x-admin-token') !== settings.adminToken) return next(new AppError(401, 'Unauthorized'));
    return next();
}

module.exports = adminAuth;
