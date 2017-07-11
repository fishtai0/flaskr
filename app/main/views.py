from datetime import datetime

from flask import render_template, session, redirect, url_for

from . import main
from .forms import NameForm
from ..models import User


@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = (User.select()
                .where(User.username == form.name.data)
                .first())
        if user is None:
            user = User(username=form.name.data)
            user.save()
            session['known'] = False
        else:
            session['known'] = True
        session['name'] = form.name.data
        form.name.data = ''
        return redirect(url_for('.index'))
    return render_template('index.html',
                           form=form, name=session.get('name'),
                           known=session.get('known', False),
                           current_time=datetime.utcnow())
