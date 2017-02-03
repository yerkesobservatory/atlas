from flask import render_template, session, redirect, url_for
from flask_login import login_user, login_required, logout_user
from . import main
from .forms import QueueForm
from .. import db
from ..models import User

@main.route('/', methods=['GET'])
def index():

    return redirect(url_for('auth.login'))

@main.route('/queue', methods=['GET', 'POST'])
@login_required
def queue():

    form = QueueForm()
    if form.validate_on_submit():
        print("Valid queue submission!")

    return render_template('main/queue.html', form=form)

