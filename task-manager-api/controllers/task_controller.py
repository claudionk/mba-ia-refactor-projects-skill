import logging

from config import constants
from models.category_model import Category
from models.task_model import Task
from models.user_model import User
from utils.errors import NotFoundError, ValidationError
from utils.time_utils import utc_now
from utils.validators import validate_task_fields

logger = logging.getLogger(__name__)


def percentage(part, total):
    return round((part / total) * 100, 2) if total > 0 else 0


class TaskController:
    @staticmethod
    def _get_or_404(task_id):
        task = Task.get(task_id)
        if not task:
            raise NotFoundError('Task nao encontrada')
        return task

    @staticmethod
    def _check_references(fields):
        if fields.get('user_id') and not User.get(fields['user_id']):
            raise NotFoundError('Usuário nao encontrado')
        if fields.get('category_id') and not Category.get(fields['category_id']):
            raise NotFoundError('Categoria nao encontrada')

    @staticmethod
    def list_tasks():
        result = []
        for task in Task.list_with_relations():
            data = task.to_dict(include_overdue=True)
            data['user_name'] = task.user.name if task.user else None
            data['category_name'] = task.category.name if task.category else None
            result.append(data)
        return result

    @staticmethod
    def get_task(task_id):
        return TaskController._get_or_404(task_id).to_dict(include_overdue=True)

    @staticmethod
    def create_task(data):
        fields = validate_task_fields(data, partial=False)
        TaskController._check_references(fields)
        task = Task(**fields)
        task.save('Erro ao criar task')
        logger.info('Task criada: %s - %s', task.id, task.title)
        return task.to_dict()

    @staticmethod
    def update_task(task_id, data):
        task = TaskController._get_or_404(task_id)
        if not data:
            raise ValidationError('Dados inválidos')
        fields = validate_task_fields(data, partial=True)
        TaskController._check_references(fields)
        for key, value in fields.items():
            setattr(task, key, value)
        task.save('Erro ao atualizar')
        logger.info('Task atualizada: %s', task.id)
        return task.to_dict()

    @staticmethod
    def delete_task(task_id):
        task = TaskController._get_or_404(task_id)
        task.remove('Erro ao deletar')
        logger.info('Task deletada: %s', task_id)
        return {'message': 'Task deletada com sucesso'}

    @staticmethod
    def search_tasks(text, status, priority, user_id):
        try:
            priority = int(priority) if priority else None
            user_id = int(user_id) if user_id else None
        except ValueError:
            raise ValidationError('Parâmetros priority e user_id devem ser inteiros')
        return [task.to_dict() for task in Task.search(text, status, priority, user_id)]

    @staticmethod
    def stats():
        by_status = Task.count_by_status()
        total = sum(by_status.values())
        done = by_status.get(constants.STATUS_DONE, 0)
        return {
            'total': total,
            'pending': by_status.get(constants.STATUS_PENDING, 0),
            'in_progress': by_status.get(constants.STATUS_IN_PROGRESS, 0),
            'done': done,
            'cancelled': by_status.get(constants.STATUS_CANCELLED, 0),
            'overdue': len(Task.find_overdue(utc_now())),
            'completion_rate': percentage(done, total),
        }
