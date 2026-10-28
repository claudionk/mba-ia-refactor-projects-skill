const express = require('express');
const reportController = require('../controllers/reportController');
const adminAuth = require('../middlewares/adminAuth');

const router = express.Router();

router.get('/api/admin/financial-report', adminAuth, async (req, res, next) => {
    try {
        res.json(await reportController.financialReport());
    } catch (err) {
        next(err);
    }
});

module.exports = router;
