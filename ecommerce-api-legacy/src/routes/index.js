const express = require('express');
const checkoutRoutes = require('./checkoutRoutes');
const adminRoutes = require('./adminRoutes');
const userRoutes = require('./userRoutes');

const router = express.Router();

router.use(checkoutRoutes);
router.use(adminRoutes);
router.use(userRoutes);

module.exports = router;
