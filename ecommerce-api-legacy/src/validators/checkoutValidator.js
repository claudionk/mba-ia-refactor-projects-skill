const AppError = require('../utils/AppError');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Mantém os nomes de campo do contrato público (usr, eml, pwd, c_id, card).
function parseCheckoutBody(body = {}) {
    const { usr, eml, pwd, c_id: courseId, card } = body;

    if (!usr || !eml || !courseId || !card) throw new AppError(400, 'Bad Request');
    if (typeof usr !== 'string' || typeof eml !== 'string' || typeof card !== 'string') {
        throw new AppError(400, 'Bad Request');
    }
    if (!EMAIL_PATTERN.test(eml)) throw new AppError(400, 'Bad Request');
    if (!Number.isInteger(Number(courseId))) throw new AppError(400, 'Bad Request');
    if (pwd !== undefined && pwd !== null && typeof pwd !== 'string') throw new AppError(400, 'Bad Request');

    return { name: usr, email: eml, password: pwd, courseId: Number(courseId), cardNumber: card };
}

function parseUserId(rawId) {
    const id = Number(rawId);
    if (!Number.isInteger(id) || id <= 0) throw new AppError(400, 'Bad Request');
    return id;
}

module.exports = { parseCheckoutBody, parseUserId };
