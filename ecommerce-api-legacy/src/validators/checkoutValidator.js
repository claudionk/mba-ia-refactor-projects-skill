const AppError = require('../utils/AppError');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const POSITIVE_INTEGER_PATTERN = /^[1-9]\d*$/;

const isPositiveInteger = (value) =>
    (typeof value === 'number' || typeof value === 'string') && POSITIVE_INTEGER_PATTERN.test(String(value));

// Mantém os nomes de campo do contrato público (usr, eml, pwd, c_id, card).
function parseCheckoutBody(body = {}) {
    const { usr, eml, pwd, c_id: courseId, card } = body;

    if (!usr || !eml || !courseId || !card) throw new AppError(400, 'Bad Request');
    if (typeof usr !== 'string' || typeof eml !== 'string' || typeof card !== 'string') {
        throw new AppError(400, 'Bad Request');
    }
    if (!EMAIL_PATTERN.test(eml)) throw new AppError(400, 'Bad Request');
    if (!isPositiveInteger(courseId)) throw new AppError(400, 'Bad Request');
    if (pwd !== undefined && pwd !== null && typeof pwd !== 'string') throw new AppError(400, 'Bad Request');

    return { name: usr, email: eml, password: pwd, courseId: Number(courseId), cardNumber: card };
}

function parseUserId(rawId) {
    if (!isPositiveInteger(rawId)) throw new AppError(400, 'Bad Request');
    return Number(rawId);
}

module.exports = { parseCheckoutBody, parseUserId };
