from flask import jsonify, current_app, url_for

import playhouse.flask_utils as futils

from . import api
from ..models import User, Post

from utils.paginate_peewee import Pagination


@api.route('/users/<int:id>')
def get_user(id):
    user = futils.get_object_or_404(User.select(), (User.id == id))
    return jsonify(user.to_json())


@api.route('/users/<int:id>/posts')
def get_user_posts(id):
    user = futils.get_object_or_404(User.select(), (User.id == id))
    pagination = Pagination(Post.posts_by_user(user),
                            current_app.config['FLASKR_POSTS_PER_PAGE'],
                            check_bounds=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_posts', page=pagination.page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_posts', page=pagination.page+1, _external=True)
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/users/<int:id>/timeline/')
def get_user_followed_posts(id):
    user = futils.get_object_or_404(User.select(), (User.id == id))
    pagination = Pagination(user.followed_posts.order_by(Post.timestamp.desc()),
                            current_app.config['FLASKR_POSTS_PER_PAGE'],
                            check_bounds=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_followed_posts', page=pagination.page-1,
                       _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_followed_posts', page=pagination.page+1,
                       _external=True)
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })
