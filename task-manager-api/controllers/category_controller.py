import logging

from config import constants
from models.category_model import Category
from models.task_model import Task
from utils.errors import NotFoundError, ValidationError
from utils.validators import is_valid_color

logger = logging.getLogger(__name__)


def _validate_color(color):
    if not is_valid_color(color):
        raise ValidationError('Cor inválida. Use o formato #RRGGBB')
    return color


class CategoryController:
    @staticmethod
    def _get_or_404(category_id):
        category = Category.get(category_id)
        if not category:
            raise NotFoundError('Categoria nao encontrada')
        return category

    @staticmethod
    def list_categories():
        task_counts = Task.count_by_category()
        result = []
        for category in Category.list_all():
            data = category.to_dict()
            data['task_count'] = task_counts.get(category.id, 0)
            result.append(data)
        return result

    @staticmethod
    def create_category(data):
        if not data:
            raise ValidationError('Dados inválidos')
        name = data.get('name')
        if not name or not isinstance(name, str):
            raise ValidationError('Nome é obrigatório')

        category = Category(
            name=name,
            description=data.get('description', ''),
            color=_validate_color(data.get('color', constants.DEFAULT_COLOR)),
        )
        category.save('Erro ao criar categoria')
        logger.info('Categoria criada: %s', category.id)
        return category.to_dict()

    @staticmethod
    def update_category(category_id, data):
        category = CategoryController._get_or_404(category_id)
        if not data:
            raise ValidationError('Dados inválidos')

        if 'name' in data:
            if not data['name'] or not isinstance(data['name'], str):
                raise ValidationError('Nome inválido')
            category.name = data['name']
        if 'description' in data:
            category.description = data['description']
        if 'color' in data:
            category.color = _validate_color(data['color'])

        category.save('Erro ao atualizar')
        return category.to_dict()

    @staticmethod
    def delete_category(category_id):
        category = CategoryController._get_or_404(category_id)
        category.remove('Erro ao deletar')
        logger.info('Categoria deletada: %s', category_id)
        return {'message': 'Categoria deletada'}
