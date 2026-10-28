const courseModel = require('../models/courseModel');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const auditLogModel = require('../models/auditLogModel');
const passwordService = require('../services/passwordService');
const paymentService = require('../services/paymentService');
const { PAYMENT_STATUS } = require('../constants');
const AppError = require('../utils/AppError');
const logger = require('../utils/logger');

async function findOrCreateUser({ name, email, password }) {
    const existing = await userModel.getByEmail(email);
    if (existing) return existing.id;

    const passwordHash = await passwordService.hashPassword(password || passwordService.generateRandomPassword());
    return userModel.create({ name, email, passwordHash });
}

async function checkout({ name, email, password, courseId, cardNumber }) {
    const course = await courseModel.getActiveById(courseId);
    if (!course) throw new AppError(404, 'Curso não encontrado');

    const userId = await findOrCreateUser({ name, email, password });

    const status = paymentService.processCard(cardNumber);
    logger.info(`Processando pagamento: curso=${courseId} usuario=${userId} cartao=****${cardNumber.slice(-4)}`);
    if (status === PAYMENT_STATUS.DENIED) throw new AppError(400, 'Pagamento recusado');

    const enrollmentId = await enrollmentModel.create(userId, courseId);
    await paymentModel.create(enrollmentId, course.price, status);
    await auditLogModel.create(`Checkout curso ${courseId} por ${userId}`);

    return { msg: 'Sucesso', enrollment_id: enrollmentId };
}

module.exports = { checkout };
