const format = (level, msg) => `[${new Date().toISOString()}] ${level}: ${msg}`;

module.exports = {
    info: (msg) => console.log(format('INFO', msg)),
    error: (msg, err) => console.error(format('ERROR', msg), err || ''),
};
