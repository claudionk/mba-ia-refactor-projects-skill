const crypto = require('crypto');

const KEY_LENGTH = 64;
const SALT_BYTES = 16;

const scrypt = (password, salt) => new Promise((resolve, reject) => {
    crypto.scrypt(password, salt, KEY_LENGTH, (err, key) => (err ? reject(err) : resolve(key)));
});

async function hashPassword(password) {
    const salt = crypto.randomBytes(SALT_BYTES);
    const key = await scrypt(password, salt);
    return `${salt.toString('hex')}:${key.toString('hex')}`;
}

async function verifyPassword(password, stored) {
    const [saltHex, keyHex] = stored.split(':');
    const expected = Buffer.from(keyHex, 'hex');
    const actual = await scrypt(password, Buffer.from(saltHex, 'hex'));
    return crypto.timingSafeEqual(expected, actual);
}

const generateRandomPassword = () => crypto.randomBytes(18).toString('base64url');

module.exports = { hashPassword, verifyPassword, generateRandomPassword };
