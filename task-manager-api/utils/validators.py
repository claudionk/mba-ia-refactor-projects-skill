import re
from datetime import datetime

from config import constants
from utils.errors import ValidationError


def parse_date(value, message):
    try:
        return datetime.strptime(value, constants.DATE_FORMAT)
    except (ValueError, TypeError):
        raise ValidationError(message)


def is_valid_email(email):
    return isinstance(email, str) and re.match(constants.EMAIL_PATTERN, email) is not None


def is_valid_color(color):
    return isinstance(color, str) and len(color) == 7 and color[0] == '#'


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_title(title):
    if not isinstance(title, str):
        raise ValidationError('Título inválido')
    if len(title) < constants.MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > constants.MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')
    return title


def validate_status(status):
    if status not in constants.VALID_STATUSES:
        raise ValidationError('Status inválido')
    return status


def validate_priority(priority):
    if not _is_int(priority) or not constants.MIN_PRIORITY <= priority <= constants.MAX_PRIORITY:
        raise ValidationError('Prioridade deve ser entre 1 e 5')
    return priority


def normalize_tags(tags):
    if isinstance(tags, list):
        return ','.join(str(tag) for tag in tags)
    if tags is None or isinstance(tags, str):
        return tags
    raise ValidationError('Tags invalidas')


def validate_task_fields(data, partial):
    """Valida o payload de task e devolve apenas os campos a persistir.

    partial=False (criação): título obrigatório e defaults aplicados.
    partial=True (atualização): só os campos presentes são considerados.
    """
    fields = {}

    if partial:
        if 'title' in data:
            fields['title'] = validate_title(data['title'])
        if 'description' in data:
            fields['description'] = data['description']
        if 'status' in data:
            fields['status'] = validate_status(data['status'])
        if 'priority' in data:
            fields['priority'] = validate_priority(data['priority'])
    else:
        if not data.get('title'):
            raise ValidationError('Título é obrigatório')
        fields['title'] = validate_title(data['title'])
        fields['description'] = data.get('description', '')
        fields['status'] = validate_status(data.get('status', constants.STATUS_PENDING))
        fields['priority'] = validate_priority(data.get('priority', constants.DEFAULT_PRIORITY))

    for key in ('user_id', 'category_id'):
        if key in data or not partial:
            fields[key] = data.get(key)

    if data.get('due_date'):
        message = 'Formato de data inválido' if partial else 'Formato de data inválido. Use YYYY-MM-DD'
        fields['due_date'] = parse_date(data['due_date'], message)
    elif partial and 'due_date' in data:
        fields['due_date'] = None

    if (partial and 'tags' in data) or (not partial and data.get('tags')):
        fields['tags'] = normalize_tags(data['tags'])

    return fields
