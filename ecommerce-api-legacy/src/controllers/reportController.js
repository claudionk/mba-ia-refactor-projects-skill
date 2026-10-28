const courseModel = require('../models/courseModel');
const enrollmentModel = require('../models/enrollmentModel');
const { PAYMENT_STATUS } = require('../constants');

async function financialReport() {
    const [courses, rows] = await Promise.all([
        courseModel.getAll(),
        enrollmentModel.listWithStudentAndPayment(),
    ]);

    const report = courses.map((course) => ({ course: course.title, revenue: 0, students: [] }));
    const byCourseId = new Map(courses.map((course, index) => [course.id, report[index]]));

    rows.forEach((row) => {
        const entry = byCourseId.get(row.course_id);
        if (!entry) return;
        if (row.payment_status === PAYMENT_STATUS.PAID) entry.revenue += row.payment_amount;
        entry.students.push({
            student: row.student_name || 'Unknown',
            paid: row.payment_amount || 0,
        });
    });

    return report;
}

module.exports = { financialReport };
