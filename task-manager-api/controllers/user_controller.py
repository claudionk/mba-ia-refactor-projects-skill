import logging

from config import constants
from models.task_model import Task
from models.user_model import User
from services.auth_service import create_token
from utils.errors import AppError, ConflictError, NotFoundError, ValidationError
from utils.validators import is_valid_email

logger = logging.getLogger(__name__)


def _require_admin(actor, message='Acesso restrito a administradores'):
    if not actor or not actor.is_admin():
        raise AppError(message, 403)


def _validate_role(role):
    if role not in constants.VALID_ROLES:
        raise ValidationError('Role inválido')
    return role


class UserController:
    @staticmethod
    def _get_or_404(user_id):
        user = User.get(user_id)
        if not user:
            raise NotFoundError('Usuário nao encontrado')
        return user

    @staticmethod
    def list_users():
        task_counts = Task.count_by_user()
        result = []
        for user in User.list_all():
            data = user.to_dict()
            data['task_count'] = task_counts.get(user.id, 0)
            result.append(data)
        return result

    @staticmethod
    def get_user(user_id):
        user = UserController._get_or_404(user_id)
        data = user.to_dict()
        data['tasks'] = [task.to_dict() for task in Task.list_by_user(user_id)]
        return data

    @staticmethod
    def create_user(data, actor=None):
        if not data:
            raise ValidationError('Dados inválidos')
        name, email, password = data.get('name'), data.get('email'), data.get('password')
        if not name:
            raise ValidationError('Nome é obrigatório')
        if not email:
            raise ValidationError('Email é obrigatório')
        if not password:
            raise ValidationError('Senha é obrigatória')
        if not is_valid_email(email):
            raise ValidationError('Email inválido')
        if not isinstance(password, str) or len(password) < constants.MIN_PASSWORD_LENGTH:
            raise ValidationError('Senha deve ter no mínimo 4 caracteres')
        if User.find_by_email(email):
            raise ConflictError('Email já cadastrado')
        role = _validate_role(data.get('role', constants.DEFAULT_ROLE))
        if role != constants.DEFAULT_ROLE:
            _require_admin(actor, 'Apenas administradores podem definir role diferente de user')

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        user.save('Erro ao criar usuário')
        logger.info('Usuário criado: %s - %s', user.id, user.name)
        return user.to_dict()

    @staticmethod
    def update_user(user_id, data, actor):
        user = UserController._get_or_404(user_id)
        if actor.id != user_id:
            _require_admin(actor)
        if not data:
            raise ValidationError('Dados inválidos')

        if 'name' in data:
            if not isinstance(data['name'], str) or not data['name']:
                raise ValidationError('Nome inválido')
            user.name = data['name']
        if 'email' in data:
            if not is_valid_email(data['email']):
                raise ValidationError('Email inválido')
            existing = User.find_by_email(data['email'])
            if existing and existing.id != user_id:
                raise ConflictError('Email já cadastrado')
            user.email = data['email']
        if 'password' in data:
            password = data['password']
            if not isinstance(password, str) or len(password) < constants.MIN_PASSWORD_LENGTH:
                raise ValidationError('Senha muito curta')
            user.set_password(password)
        if 'role' in data:
            _require_admin(actor, 'Apenas administradores podem alterar role')
            user.role = _validate_role(data['role'])
        if 'active' in data:
            if not isinstance(data['active'], bool):
                raise ValidationError('Campo active deve ser booleano')
            user.active = data['active']

        user.save('Erro ao atualizar')
        return user.to_dict()

    @staticmethod
    def delete_user(user_id, actor):
        _require_admin(actor)
        user = UserController._get_or_404(user_id)
        Task.delete_by_user(user_id)
        user.remove('Erro ao deletar')
        logger.info('Usuário deletado: %s', user_id)
        return {'message': 'Usuário deletado com sucesso'}

    @staticmethod
    def list_user_tasks(user_id):
        UserController._get_or_404(user_id)
        return [task.to_user_task_dict() for task in Task.list_by_user(user_id)]

    @staticmethod
    def login(data):
        if not data:
            raise ValidationError('Dados inválidos')
        email, password = data.get('email'), data.get('password')
        if not email or not password or not isinstance(password, str):
            raise ValidationError('Email e senha são obrigatórios')

        user = User.find_by_email(email)
        if not user or not user.check_password(password):
            raise AppError('Credenciais invalidas', 401)
        if not user.active:
            raise AppError('Usuário inativo', 403)

        if user.upgrade_legacy_hash(password):
            user.save('Erro ao atualizar')
        return {
            'message': 'Login realizado com sucesso',
            'user': user.to_dict(),
            'token': create_token(user),
        }
