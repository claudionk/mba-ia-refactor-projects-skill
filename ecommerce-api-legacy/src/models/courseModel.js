const { get, all } = require('../database/connection');

const getActiveById = (id) => get("SELECT * FROM courses WHERE id = ? AND active = 1", [id]);

const getAll = () => all("SELECT * FROM courses ORDER BY id");

module.exports = { getActiveById, getAll };
