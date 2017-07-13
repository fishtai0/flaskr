from flask import current_app

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import UserMixin

import peewee as pw

from . import db
from . import login_manager


class Role(db.Model):
    name = pw.CharField(64, unique=True)

    def __repr__(self):
        return '<Role %r>' % self.name

    class Meta:
        db_table = 'roles'


class User(UserMixin, db.Model):
    email = pw.CharField(64, unique=True, index=True)
    username = pw.CharField(64, unique=True, index=True)
    role = pw.ForeignKeyField(Role, related_name='users', null=True)
    password_hash = pw.CharField(128)
    confirmed = pw.BooleanField(default=False)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600*2):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        self.save()
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        self.save()
        return True

    def __repr__(self):
        return '<User %r>' % self.username

    class Meta:
        db_table = 'users'


@login_manager.user_loader
def load_user(user_id):
    return User.select().where(User.id == int(user_id)).first()
