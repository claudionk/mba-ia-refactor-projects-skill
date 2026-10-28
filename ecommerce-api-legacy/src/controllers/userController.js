const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');

// Remove também matrículas e pagamentos do usuário, evitando registros órfãos.
async function deleteUser(id) {
    await paymentModel.removeByUserId(id);
    await enrollmentModel.removeByUserId(id);
    await userModel.remove(id);
}

module.exports = { deleteUser };
