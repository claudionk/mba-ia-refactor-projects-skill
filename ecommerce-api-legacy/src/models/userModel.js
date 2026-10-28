const { run, get } = require('../database/connection');

const getByEmail = (email) => get("SELECT id FROM users WHERE email = ?", [email]);

const create = async ({ name, email, passwordHash }) => {
    const { lastID } = await run("INSERT INTO users (name, email, pass) VALUES (?, ?, ?)", [name, email, passwordHash]);
    return lastID;
};

const remove = (id) => run("DELETE FROM users WHERE id = ?", [id]);

module.exports = { getByEmail, create, remove };
