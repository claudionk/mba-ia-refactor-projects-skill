const express = require('express');
const checkoutController = require('../controllers/checkoutController');
const { parseCheckoutBody } = require('../validators/checkoutValidator');

const router = express.Router();

router.post('/api/checkout', async (req, res, next) => {
    try {
        const result = await checkoutController.checkout(parseCheckoutBody(req.body));
        res.status(200).json(result);
    } catch (err) {
        next(err);
    }
});

module.exports = router;
