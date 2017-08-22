from flask import jsonify, request, g, url_for, current_app

import playhouse.flask_utils as futils

from ..models import Post, Permission, Comment
from . import api
from .decorators import permission_required

from utils.paginate_peewee import Pagination


@api.route('/comments/')
def get_comments():
    pagination = Pagination(
        Comment.timeline(),
        current_app.config['FLASKR_COMMENTS_PER_PAGE'],
        check_bounds=False)
    comments = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_comments', page=pagination.page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_comments', page=pagination.page+1, _external=True)
    return jsonify({
        'comments': [comment.to_json() for comment in comments],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/comments/<int:id>')
def get_comment(id):
    comment = futils.get_object_or_404(Comment.select(),
                                       (Comment.id == id))
    return jsonify(comment.to_json())


@api.route('/posts/<int:id>/comments/')
def get_post_comments(id):
    post = futils.get_object_or_404(Post.select(),
                                    (Post.id == id))
    pagination = Pagination(post.comments_timeline(),
                            current_app.config['FLASKR_COMMENTS_PER_PAGE'],
                            check_bounds=False)
    comments = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_post_comments', page=pagination.page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_post_comments', page=pagination.page+1, _external=True)
    return jsonify({
        'comments': [comment.to_json() for comment in comments],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/posts/<int:id>/comments', methods=['POST'])
@permission_required(Permission.COMMENT)
def new_post_comment(id):
    post = futils.get_object_or_404(Post.select(), (Post.id == id))
    comment = Comment.from_json(request.json)
    comment.author = g.current_user
    comment.post = post
    comment.save()
    comment.update_body_html()
    comment = comment.refresh()
    return jsonify(comment.to_json()), 201, \
        {'Location': url_for('api.get_comment', id=comment.id,
                             _external=True)}
