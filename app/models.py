from werkzeug.security import generate_password_hash, check_password_hash

import peewee as pw

from . import db


class Role(db.Model):
    name = pw.CharField(64, unique=True)

    def __repr__(self):
        return '<Role %r>' % self.name

    class Meta:
        db_table = 'roles'


class User(db.Model):
    username = pw.CharField(64, unique=True, index=True)
    role = pw.ForeignKeyField(Role, related_name='users', null=True)
    password_hash = pw.CharField(128)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username

    class Meta:
        db_table = 'users'
