from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, login_required, logout_user
from ..models import User
from .forms import LoginForm
from . import auth

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """ Authenticates a user using email/password.
    """
    # create login form
    form = LoginForm()

    # validate POST fields from form
    if form.validate_on_submit():

        # check if user exists
        user = User.query.filter_by(email=form.email.data).first()

        # # verify password
        if user is not None and user.verify_password(form.password.data):
            login_user(user, False)
            return redirect(request.args.get('next') or url_for('main.queue'))

        # invalid password
        flash('Invalid e-mail or password')

    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    """ Logs a user out - should only be visible when logged in.
    """
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))
