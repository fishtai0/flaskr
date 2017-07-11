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

    def __repr__(self):
        return '<User %r>' % self.username

    class Meta:
        db_table = 'users'
