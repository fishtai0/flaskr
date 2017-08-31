from datetime import datetime
import hashlib

from flask import current_app, request, url_for

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash

from markdown import markdown
import bleach

from flask_login import UserMixin, AnonymousUserMixin

import peewee as pw
import requests
from requests.exceptions import ConnectionError, HTTPError

from app.exceptions import ValidationError
from . import db
from . import login_manager
from .decorators import require_instance
from utils.identicon import IdenticonSVG


@require_instance
def refresh(self):
    """Reload object from database."""
    return type(self).get(self._pk_expr())


db.Model.refresh = refresh


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

    @staticmethod
    def generate_fake(count=100):
        from random import seed
        import forgery_py

        seed()
        fake_data = []
        for i in range(count):
            fake_data.append(
                dict(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password_hash=generate_password_hash(
                         forgery_py.lorem_ipsum.word()),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True)))
        for idx in range(0, len(fake_data), 10):
            with db.database.atomic():
                User.insert_many(fake_data[idx:idx+10]).execute()

    @staticmethod
    def add_self_follows():
        for user in User.select():
            if not user.is_following(user):
                user.follow(user)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self._role()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.lower().encode('utf-8')).hexdigest()

    def _role(self):
        if self.role is None:
            if self.email == current_app.config['FLASKR_ADMIN']:
                self.role = (Role.select()
                             .where(Role.permissions == 0xff)
                             .first())
            if self.role is None:
                self.role = Role.select().where(Role.default == True).first()

    def save(self, *args, **kwargs):
        super(self.__class__, self).save(*args, **kwargs)
        if not self.is_following(self):
            self.follow(self)

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

    @require_instance
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            f.save()

    def unfollow(self, user):
        f = self.followed.where(Follow.followed == user.id).first()
        if f:
            f.delete_instance()

    def is_following(self, user):
        return self.followed.where(
            Follow.followed == user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.where(
            Follow.follower == user.id).first() is not None

    @property
    def followed_posts(self):
        return (Post.select(Post, self.__class__)
                .join(Follow, on=(Post.author == Follow.followed))
                .join(self.__class__, on=(Post.author == self.__class__.id))
                .where(Follow.follower == self))

    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id, _external=True),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts': url_for('api.get_user_posts', id=self.id, _external=True),
            'followed_posts': url_for('api.get_user_followed_posts',
                                      id=self.id, _external=True),
            'post_count': self.posts.count()
        }
        return json_user

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.select().where(User.id == data['id']).first()

    def __repr__(self):
        return '<User %r>' % self.username

    class Meta:
        db_table = 'users'


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.select().where(User.id == int(user_id)).first()


class Follow(db.Model):
    follower = pw.ForeignKeyField(User, related_name='followed',
                                  on_delete='CASCADE')
    followed = pw.ForeignKeyField(User, related_name='followers',
                                  on_delete='CASCADE')
    timestamp = pw.DateTimeField(default=datetime.utcnow)

    @classmethod
    def followers_of(cls, user):
        """Followers of user."""
        return (cls.select(cls, User)
                .join(User, on=cls.follower)
                .where(cls.followed == user))

    @classmethod
    def followed_by(cls, user):
        """Followed by user."""
        return (cls.select(cls, User)
                .join(User, on=cls.followed)
                .where(Follow.follower == user))

    class Meta:
        db_table = 'follows'
        indexes = (
            (('follower', 'followed'), True),
        )


class Post(db.Model):
    body = pw.TextField(null=True)
    body_html = pw.TextField(null=True)
    timestamp = pw.DateTimeField(index=True, default=datetime.utcnow)
    author = pw.ForeignKeyField(User, related_name='posts', null=True)

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.select().count()
        fake_data = []
        for i in range(count):
            u = User.select().offset(randint(0, user_count - 1)).first()
            fake_data.append(
                dict(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                     timestamp=forgery_py.date.date(True),
                     author=u))
        for idx in range(0, len(fake_data), 10):
            with db.database.atomic():
                Post.insert_many(fake_data[idx:idx+10]).execute()

    @require_instance
    def update_body_html(self):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        self.__class__.update(body_html=bleach.linkify(bleach.clean(
            markdown(self.body, output_format='html'),
            tags=allowed_tags, strip=True))).where(self._pk_expr()).execute()

    @classmethod
    def timeline(cls, order='desc'):
        if order == 'desc':
            order = cls.timestamp.desc()
        else:
            order = cls.timestamp.asc()

        return (cls.select(cls, User)
                .join(User, on=cls.author)
                .order_by(order))

    def comments_timeline(self, order='asc'):
        if order == 'asc':
            order = Comment.timestamp.asc()
        else:
            order = Comment.timestamp.desc()

        return (Comment.select(Comment, User)
                .join(User, on=(Comment.author == User.id))
                .where(Comment.post == self.id)
                .order_by(order))

    @classmethod
    def posts_by_user(cls, user, order='desc'):
        if order == 'desc':
            order = cls.timestamp.desc()
        else:
            order = cls.timestamp.asc()
        return (cls.select(cls, User)
                .join(User, on=(cls.author == User.id))
                .where(cls.author == user)
                .order_by(order))

    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id,
                              _external=True),
            'comments': url_for('api.get_post_comments', id=self.id,
                                _external=True),
            'comment_count': self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        # TODO
        return Post(body=body)

    class Meta:
        db_table = 'posts'


class Comment(db.Model):
    body = pw.TextField(null=True)
    body_html = pw.TextField(null=True)
    timestamp = pw.DateTimeField(index=True, default=datetime.utcnow)
    disabled = pw.BooleanField(null=True, default=False)
    author = pw.ForeignKeyField(User, related_name='comments', null=True)
    post = pw.ForeignKeyField(Post, related_name='comments', null=True)

    @require_instance
    def update_body_html(self):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        self.__class__.update(body_html=bleach.linkify(bleach.clean(
            markdown(self.body, output_format='html'),
            tags=allowed_tags, strip=True))).where(self._pk_expr()).execute()

    @classmethod
    def timeline(cls, order='desc'):
        if order == 'desc':
            order = cls.timestamp.desc()
        else:
            order = cls.timestamp.asc()

        return (cls.select(cls, User)
                .join(User, on=cls.author)
                .order_by(order))

    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id, _external=True),
            'post': url_for('api.get_post', id=self.post_id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id,
                              _external=True),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        # TODO
        return Comment(body=body)

    class Meta:
        db_table = 'comments'
