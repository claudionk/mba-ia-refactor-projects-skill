const { PAYMENT_STATUS, APPROVED_CARD_PREFIX } = require('../constants');

// Simula o gateway: cartões iniciados em "4" são aprovados.
function processCard(cardNumber) {
    return cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
}

module.exports = { processCard };
