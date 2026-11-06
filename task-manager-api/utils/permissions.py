from utils.errors import AppError


def require_admin(actor, message='Acesso restrito a administradores'):
    if not actor or not actor.is_admin():
        raise AppError(message, 403)


def require_manager(actor, message='Acesso restrito a administradores e gerentes'):
    if not actor or not actor.can_manage():
        raise AppError(message, 403)


def require_owner_or_manager(actor, owner_id, message='Sem permissão para acessar este recurso'):
    if not actor or (actor.id != owner_id and not actor.can_manage()):
        raise AppError(message, 403)
