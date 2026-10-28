from datetime import timedelta

from config import constants
from controllers.task_controller import percentage
from models.category_model import Category
from models.task_model import Task
from models.user_model import User
from utils.errors import NotFoundError
from utils.time_utils import utc_now

PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}


class ReportController:
    @staticmethod
    def summary():
        now = utc_now()
        by_status = Task.count_by_status()
        by_priority = Task.count_by_priority()
        completion_stats = Task.user_completion_stats()
        since = now - timedelta(days=constants.RECENT_DAYS)

        overdue_list = [
            {
                'id': task.id,
                'title': task.title,
                'due_date': str(task.due_date),
                'days_overdue': (now - task.due_date).days,
            }
            for task in Task.find_overdue(now)
        ]

        user_stats = []
        for user in User.list_all():
            total, completed = completion_stats.get(user.id, (0, 0))
            user_stats.append({
                'user_id': user.id,
                'user_name': user.name,
                'total_tasks': total,
                'completed_tasks': completed,
                'completion_rate': percentage(completed, total),
            })

        return {
            'generated_at': str(now),
            'overview': {
                'total_tasks': sum(by_status.values()),
                'total_users': User.count(),
                'total_categories': Category.count(),
            },
            'tasks_by_status': {
                'pending': by_status.get(constants.STATUS_PENDING, 0),
                'in_progress': by_status.get(constants.STATUS_IN_PROGRESS, 0),
                'done': by_status.get(constants.STATUS_DONE, 0),
                'cancelled': by_status.get(constants.STATUS_CANCELLED, 0),
            },
            'tasks_by_priority': {
                label: by_priority.get(priority, 0) for priority, label in PRIORITY_LABELS.items()
            },
            'overdue': {'count': len(overdue_list), 'tasks': overdue_list},
            'recent_activity': {
                'tasks_created_last_7_days': Task.count_created_since(since),
                'tasks_completed_last_7_days': Task.count_done_since(since),
            },
            'user_productivity': user_stats,
        }

    @staticmethod
    def user_report(user_id):
        user = User.get(user_id)
        if not user:
            raise NotFoundError('Usuário nao encontrado')

        tasks = Task.list_by_user(user_id)
        total = len(tasks)
        count = lambda status: sum(1 for task in tasks if task.status == status)
        done = count(constants.STATUS_DONE)

        return {
            'user': {'id': user.id, 'name': user.name, 'email': user.email},
            'statistics': {
                'total_tasks': total,
                'done': done,
                'pending': count(constants.STATUS_PENDING),
                'in_progress': count(constants.STATUS_IN_PROGRESS),
                'cancelled': count(constants.STATUS_CANCELLED),
                'overdue': sum(1 for task in tasks if task.is_overdue()),
                'high_priority': sum(1 for task in tasks if task.priority <= constants.HIGH_PRIORITY_THRESHOLD),
                'completion_rate': percentage(done, total),
            },
        }
