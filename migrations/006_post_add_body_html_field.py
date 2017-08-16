"""Peewee migrations -- 006_post_add_body_html_field.py.
"""

from app.models import Post


def migrate(migrator, database, fake=False, **kwargs):
    migrator.add_fields(Post, body_html=Post.body_html)


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_fields(Post, 'body_html')
