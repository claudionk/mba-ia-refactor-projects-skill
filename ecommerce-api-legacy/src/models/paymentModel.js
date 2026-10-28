const { run } = require('../database/connection');

const create = (enrollmentId, amount, status) =>
    run("INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)", [enrollmentId, amount, status]);

const removeByUserId = (userId) => run(
    "DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)",
    [userId]
);

module.exports = { create, removeByUserId };
