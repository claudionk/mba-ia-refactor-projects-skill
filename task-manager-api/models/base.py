import logging

from sqlalchemy.exc import SQLAlchemyError

from database import db
from utils.errors import AppError

logger = logging.getLogger(__name__)


class CrudMixin:
    @classmethod
    def get(cls, entity_id):
        return db.session.get(cls, entity_id)

    @classmethod
    def count(cls):
        return cls.query.count()

    def save(self, error_message):
        try:
            db.session.add(self)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception(error_message)
            raise AppError(error_message, 500)

    def remove(self, error_message):
        try:
            db.session.delete(self)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception(error_message)
            raise AppError(error_message, 500)
