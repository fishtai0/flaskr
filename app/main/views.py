from flask import render_template

import playhouse.flask_utils as futils

from . import main
from ..models import User


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/user/<username>')
def user(username):
    user_query = User.select()
    user = futils.get_object_or_404(user_query, (User.username == username))
    return render_template('user.html', user=user)
