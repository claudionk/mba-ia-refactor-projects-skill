from sqlalchemy import case, func
from sqlalchemy.orm import joinedload

from config import constants
from database import db
from models.base import CrudMixin
from utils.time_utils import utc_now


class Task(CrudMixin, db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=constants.STATUS_PENDING)
    priority = db.Column(db.Integer, default=constants.DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    def is_overdue(self, now=None):
        if not self.due_date or self.status in constants.CLOSED_STATUSES:
            return False
        return self.due_date < (now or utc_now())

    def to_dict(self, include_overdue=False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }
        if include_overdue:
            data['overdue'] = self.is_overdue()
        return data

    def to_user_task_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': str(self.created_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'overdue': self.is_overdue(),
        }

    @classmethod
    def list_with_relations(cls):
        return cls.query.options(joinedload(cls.user), joinedload(cls.category)).order_by(cls.id).all()

    @classmethod
    def search(cls, text='', status='', priority=None, user_id=None):
        query = cls.query
        if text:
            pattern = f'%{text}%'
            query = query.filter(db.or_(cls.title.like(pattern), cls.description.like(pattern)))
        if status:
            query = query.filter(cls.status == status)
        if priority is not None:
            query = query.filter(cls.priority == priority)
        if user_id is not None:
            query = query.filter(cls.user_id == user_id)
        return query.order_by(cls.id).all()

    @classmethod
    def list_by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id).order_by(cls.id).all()

    @classmethod
    def delete_by_user(cls, user_id):
        for task in cls.list_by_user(user_id):
            db.session.delete(task)

    @classmethod
    def _count_grouped(cls, column):
        rows = db.session.query(column, func.count(cls.id)).group_by(column).all()
        return {key: total for key, total in rows}

    @classmethod
    def count_by_status(cls):
        return cls._count_grouped(cls.status)

    @classmethod
    def count_by_priority(cls):
        return cls._count_grouped(cls.priority)

    @classmethod
    def count_by_user(cls):
        return cls._count_grouped(cls.user_id)

    @classmethod
    def count_by_category(cls):
        return cls._count_grouped(cls.category_id)

    @classmethod
    def user_completion_stats(cls):
        done = func.sum(case((cls.status == constants.STATUS_DONE, 1), else_=0))
        rows = db.session.query(cls.user_id, func.count(cls.id), done).group_by(cls.user_id).all()
        return {user_id: (total, int(completed or 0)) for user_id, total, completed in rows}

    @classmethod
    def find_overdue(cls, now):
        return cls.query.filter(
            cls.due_date.isnot(None),
            cls.due_date < now,
            cls.status.notin_(constants.CLOSED_STATUSES),
        ).order_by(cls.id).all()

    @classmethod
    def count_created_since(cls, since):
        return cls.query.filter(cls.created_at >= since).count()

    @classmethod
    def count_done_since(cls, since):
        return cls.query.filter(cls.status == constants.STATUS_DONE, cls.updated_at >= since).count()
