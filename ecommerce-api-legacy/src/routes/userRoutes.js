const express = require('express');
const userController = require('../controllers/userController');
const adminAuth = require('../middlewares/adminAuth');
const { parseUserId } = require('../validators/checkoutValidator');

const router = express.Router();

router.delete('/api/users/:id', adminAuth, async (req, res, next) => {
    try {
        await userController.deleteUser(parseUserId(req.params.id));
        res.send('Usuário deletado junto com suas matrículas e pagamentos.');
    } catch (err) {
        next(err);
    }
});

module.exports = router;
