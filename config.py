import os


class Config(object):
    MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', False)
    DEBUG = False
    TESTING = False
    CSRF_ENABLED = True
    SECRET_KEY = os.environ['SECRET_KEY']
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    SQLALCHEMY_BINDS = {
        'lbc_data': os.environ.get('DATA_DATABASE_URL', os.environ['DATABASE_URL'])
    }
    BROWSERID_URL = os.environ['BROWSERID_URL']
    BROWSERID_LOGIN_URL = '/log-in'
    BROWSERID_LOGOUT_URL = '/log-out'

    GOOGLE_PRIVATE_KEY = os.environ.get('GOOGLE_PRIVATE_KEY', '').replace("\\n", "\n")
    GOOGLE_CLIENT_EMAIL = os.environ.get('GOOGLE_CLIENT_EMAIL', '')
    GOOGLE_SPREADSHEET_ID = os.environ.get('GOOGLE_SPREADSHEET_ID', '')

    # Flask-Security
    SECURITY_PASSWORD_HASH = 'pbkdf2_sha512'
    SECURITY_CONFIRMABLE = True
    SECURITY_TRACKABLE = True
    SECURITY_PASSWORD_SALT = 'something_super_secret_change_in_production'

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_BINDS = {
        'lbc_data': os.environ.get('DATA_DATABASE_URL')
    }

class StagingConfig(Config):
    DEVELOPMENT = True
    DEBUG = True

class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True
    SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    MAINTENANCE_MODE = False
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_BINDS = {
        'lbc_data': 'sqlite:///:memory:'
    }
