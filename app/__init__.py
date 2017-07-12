from flask import Flask

from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_pw import Peewee

from config import config


bootstrap = Bootstrap()
moment = Moment()
db = Peewee()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    app.cli.add_command(db.cli, 'db')

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    return app
