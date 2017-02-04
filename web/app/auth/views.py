from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from ..models import User
from .forms import LoginForm, RegistrationForm, PasswordResetForm, PasswordRequestForm
from . import auth
from ..email import send_email

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


@auth.route('/register',  methods=['GET', 'POST'])
def register():
    """ Presents registration form for users to fill out; if it is
    filled out correctly, adds the user to the database and sends a
    confirmation email to them.
    """
    # create registration form
    form = RegistrationForm()

    if form.validate_on_submit():

        # create serializer to decode token
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False

        # check that email and lastname matches
        if data.get('email') != form.email.data or data.get('lastname') != form.lastname.data:
            return False

        # check if user exists
        if User.query.filter_by(email=form.email.data).first():
            return redirect(request.args.get('next') or url_for('auth.login'))

        # if not, create a new user
        user = User(firstname=form.firstname.data,
                    lastname=form.lastname.data,
                    email=form.email.data,
                    password=form.password.data,
                    affiliation=form.affiliation.data,
                    minor=form.minor.data)

        # add the user to the database
        db.session.add(user)
        db.session.commit()

        # generate confirmation token and send
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm your Account',
                   'auth/email/confirm',  user=user, token=token)
        flash('A confirmation email has been sent to you by email')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    """ This processes the link sent in the email once the user has clicked
    on it. This checks if the token is valid, and if so, redirects to the queue.
    """

    # check if user has already been confirmed
    if current_user.confirmed:
        return redirect(url_for('auth.login'))

    # check if valid token
    if current_user.confirm(token):
        flash('Thank you for confirming your account!')
    else:
        # token is invalid
        flash('The confirmation link is invalid or has expired')
        return redirect(url_for('auth.confirm'))

    return redirect(url_for('main.queue'))


@auth.route('/confirm')
@login_required
def resend_confirmation():
    """ This resends the confirmation email to a user with a new token.
    """
    # generate new token
    token = current_user.generate_confirmation_token()

    # send the email
    send_email(user.email, 'Confirm your Account',
               'auth/email/confirm',  user=user, token=token)

    flash('A new confirmation email has been sent to you by email')

    return redirect(url_for('auth.login'))


@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():

    form = PasswordRequestForm()

    # if form is valid
    if form.validate_on_submit():

        user = User.query.filter_by(email=form.email.data).first()

        # if user exists
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset your Password',
                       'auth/email/reset_passsword', user=user,
                       token=token, next=request.args.get('next'))

            flash('An email with instructions to reset your password '
                  'has been sent to you')

            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):

    # check if user is already logged in
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))

    form = PasswordResetForm()

 # if form is valid
    if form.validate_on_submit():

        # check if user exists
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('main.index'))

        # update password
        if user.reset_password(token, form.password.data):
            flash('Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))

    return render_template('auth/reset_password.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    """ Logs a user out - should only be visible when logged in.
    """
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))
