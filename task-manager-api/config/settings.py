import os

from dotenv import load_dotenv

load_dotenv()

DEV_SECRET_KEY = 'dev-only-key-change-in-prod'


def _as_bool(value):
    return str(value).lower() in ('1', 'true', 'yes')


class Settings:
    SECRET_KEY = os.environ.get('SECRET_KEY', DEV_SECRET_KEY)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = _as_bool(os.environ.get('DEBUG', 'false'))
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', '5000'))
    TOKEN_TTL_SECONDS = int(os.environ.get('TOKEN_TTL_SECONDS', str(8 * 3600)))
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
