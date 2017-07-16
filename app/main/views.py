from flask import render_template, redirect, url_for, abort, flash

from flask_login import login_required, current_user

import playhouse.flask_utils as futils

from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm
from ..models import Permission, Role, User, Post
from ..decorators import admin_required


@main.route('/', methods=['GET', 'POST'])
def index():
    form = PostForm()
    if (current_user.is_authenticated and
        current_user.can(Permission.WRITE_ARTICLES) and
            form.validate_on_submit()):
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        post.save()
        return redirect(url_for('.index'))
    posts = Post.select().order_by(Post.timestamp.desc())
    return render_template('index.html', form=form, posts=posts)


@main.route('/user/<username>')
def user(username):
    user_query = User.select()
    user = futils.get_object_or_404(user_query, (User.username == username))
    return render_template('user.html', user=user)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        current_user.save()
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user_query = User.select()
    user = futils.get_object_or_404(user_query, (User.id == id))
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.select.where(Role.id == form.role.data).first()
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        user.save()
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)
