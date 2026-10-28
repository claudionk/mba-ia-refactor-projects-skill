const { run, all } = require('../database/connection');

const create = async (userId, courseId) => {
    const { lastID } = await run("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", [userId, courseId]);
    return lastID;
};

const removeByUserId = (userId) => run("DELETE FROM enrollments WHERE user_id = ?", [userId]);

// Uma única query substitui o N+1 do relatório (matrículas + usuário + pagamento).
const listWithStudentAndPayment = () => all(`
    SELECT e.id AS enrollment_id, e.course_id,
           u.name AS student_name,
           p.amount AS payment_amount, p.status AS payment_status
    FROM enrollments e
    LEFT JOIN users u ON u.id = e.user_id
    LEFT JOIN payments p ON p.enrollment_id = e.id
    ORDER BY e.id
`);

module.exports = { create, removeByUserId, listWithStudentAndPayment };
