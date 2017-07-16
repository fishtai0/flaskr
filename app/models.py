from datetime import datetime
import hashlib

from flask import current_app, request

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import UserMixin, AnonymousUserMixin

import peewee as pw
import requests
from requests.exceptions import ConnectionError, HTTPError

from . import db
from . import login_manager
from utils.identicon import IdenticonSVG


class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class Role(db.Model):
    name = pw.CharField(64, unique=True)
    default = pw.BooleanField(default=False, index=True)
    permissions = pw.IntegerField(null=True)

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.select().where(Role.name == r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            role.save()

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
    name = pw.CharField(64, null=True)
    location = pw.CharField(64, null=True)
    about_me = pw.TextField(null=True)
    member_since = pw.DateTimeField(default=datetime.utcnow, null=True)
    last_seen = pw.DateTimeField(default=datetime.utcnow, null=True)
    avatar_hash = pw.CharField(32, null=True)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKR_ADMIN']:
                self.role = (Role.select()
                             .where(Role.permissions == 0xff)
                             .first())
            if self.role is None:
                self.role = Role.select().where(Role.default == True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.lower().encode('utf-8')).hexdigest()

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

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if (self.__class__.select()
            .where(self.__class__.email == new_email)
                .first()) is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.lower().encode('utf-8')).hexdigest()
        self.save()
        return True

    def can(self, permissions):
        return (self.role is not None and
                (self.role.permissions & permissions) == permissions)

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        self.save()

    def gravatar(self, size=100, default='404', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'

        if not self.avatar_hash:
            self.avatar_hash = hashlib.md5(
                self.email.lower().encode('utf-8')).hexdigest()
            self.save()
        hash = self.avatar_hash
        gravatar_url = '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)
        return gravatar_url

    def avatar(self, size=100, **kwargs):
        gravatar_url = self.gravatar(size)
        try:
            r = requests.get(gravatar_url)
            r.raise_for_status()
        except (ConnectionError, HTTPError):
            i = IdenticonSVG(self.avatar_hash, size=size, **kwargs)
            gravatar_url = 'data:image/svg+xml;text,{0}'.format(i.to_string(True))

        return gravatar_url

    def __repr__(self):
        return '<User %r>' % self.username

    class Meta:
        db_table = 'users'


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


@login_manager.user_loader
def load_user(user_id):
    return User.select().where(User.id == int(user_id)).first()
