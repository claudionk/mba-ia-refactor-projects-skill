import hashlib
import hmac

from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models.base import CrudMixin
from utils.time_utils import utc_now

PASSWORD_METHOD = 'pbkdf2:sha256'


class User(CrudMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, password):
        self.password = generate_password_hash(password, method=PASSWORD_METHOD)

    def _uses_legacy_hash(self):
        return '$' not in self.password

    def check_password(self, password):
        if self._uses_legacy_hash():
            legacy = hashlib.md5(password.encode()).hexdigest()
            return hmac.compare_digest(self.password, legacy)
        return check_password_hash(self.password, password)

    def upgrade_legacy_hash(self, password):
        """Troca um hash MD5 antigo por um hash seguro após login válido."""
        if self._uses_legacy_hash():
            self.set_password(password)
            return True
        return False

    def is_admin(self):
        return self.role == 'admin'

    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def list_all(cls):
        return cls.query.order_by(cls.id).all()
