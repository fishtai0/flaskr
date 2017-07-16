import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    PROJECT_DIR = basedir
    SECRET_KEY = (os.environ.get('SECRET_KEY') or
                  '44617457d542163d10ada66726b31ef80a88ac1a41013ea5')

    # bootstrap
    BOOTSTRAP_SERVE_LOCAL = True

    PEEWEE_MODELS_MODULE = 'app.models'
    FLASKR_ADMIN = os.environ.get('FLASKR_ENV') or 'fishtai0@outlook.com'

    @classmethod
    def init_app(cls, app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    PEEWEE_DATABASE_URI = (
        os.environ.get('DEV_DATABASE_URL') or
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')
    )


class TestingConfig(Config):
    TESTING = True
    PEEWEE_DATABASE_URI = (
        os.environ.get('DEV_DATABASE_URL') or
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
    )


class ProductionConfig(Config):
    DEBUG = False

    PEEWEE_DATABASE_URI = (
        os.environ.get('PROD_DATABASE_URL') or
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    )


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
