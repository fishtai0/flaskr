from flask import jsonify, request, g, url_for, current_app

import playhouse.flask_utils as futils

from ..models import Post, Permission
from . import api
from .decorators import permission_required
from .errors import forbidden

from utils.paginate_peewee import Pagination


@api.route('/posts/')
def get_posts():
    pagination = Pagination(Post.timeline(),
                            current_app.config['FLASKR_POSTS_PER_PAGE'],
                            check_bounds=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_posts', page=pagination.page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_posts', page=pagination.page+1, _external=True)
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/posts/<int:id>')
def get_post(id):
    post = futils.get_object_or_404(Post.select(), (Post.id == id))
    return jsonify(post.to_json())


@api.route('/posts/', methods=['POST'])
@permission_required(Permission.WRITE_ARTICLES)
def new_post():
    post = Post.from_json(request.get_json())
    post.author = g.current_user
    post.save()
    post.update_body_html()
    post = post.refresh()
    return jsonify(post.to_json()), 201, \
        {'Location': url_for('api.get_post', id=post.id, _external=True)}


@api.route('/posts/<int:id>', methods=['PUT'])
@permission_required(Permission.WRITE_ARTICLES)
def edit_post(id):
    post = futils.get_object_or_404(Post.select(), (Post.id == id))
    if g.current_user != post.author and \
       not g.current_user.can(Permission.ADMINISTER):
        return forbidden('Insufficient permissions')
    post.body = request.get_json().get('body', post.body)
    post.save()
    post.update_body_html()
    post = post.refresh()
    return jsonify(post.to_json())
