from flask import render_template, session, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from config import config
from . import main
from .forms import QueueForm
from .. import db
from ..models import User, Session

@main.route('/', methods=['GET'])
def index():

    return redirect(url_for('auth.login'))

@main.route('/queue', methods=['GET', 'POST'])
@login_required
def queue():

    form = QueueForm()
    if form.validate_on_submit():

        # build the session
        session = build_session(form)

        # add session to db
        db.session.add(session)

        # commit new session
        db.session.commit()

        # return thanks
        return render_template('main/thanksqueue.html')

        
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(u"{}: {}".format(getattr(form, field).label.text, error), 'login')
                print(u"{}: {}".format(getattr(form, field).label.text, error))

    return render_template('main/queue.html', form=form)


def build_session(form):
    """ Given a QueueForm, build the corresponding Session object and return it
    """
    return Session(target=form.target.data,
                   exposure_time=form.exptime.data,
                   exposure_count=form.expcount.data,
                   binning=form.binning.data,
                   user=current_user,
                   filter_i=form.filter_i.data,
                   filter_r=form.filter_r.data,
                   filter_g=form.filter_g.data,
                   filter_u=form.filter_u.data,
                   filter_z=form.filter_z.data,
                   filter_ha=form.filter_ha.data,
                   filter_clear=form.filter_clear.data)
