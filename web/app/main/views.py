import json
import paho.mqtt.client as mqtt
from flask import render_template, session, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from config import config
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

        # build the JSON form
        msg = build_msg(form)
        print(msg)

        # connect to mqtt broker
        client = connect()

        # send request
        client.publish('/seo/queue', json.dumps(msg))

        # disconnect from broker
        client.disconnect()
        
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(u"{}: {}".format(getattr(form, field).label.text, error), 'login')
                print(u"{}: {}".format(getattr(form, field).label.text, error))

    return render_template('main/queue.html', form=form)


def build_msg(form):
    """ Given a QueueForm, build the corresponding JSON message and return it
    """
    # build JSON
    msg = {}
    msg['type'] = 'request'
    msg['target'] = form.target.data
    msg['exposure_time'] = form.exptime.data
    msg['exposure_count'] = form.expcount.data
    msg['binning'] = form.binning.data
    msg['user'] = (current_user.email).split('@')[0]
    msg['note'] = form.note.data
    msg['filters'] = []

    # add filters
    if form.filter_u.data is True:
        msg['filters'].append('u')
    if form.filter_g.data is True:
        msg['filters'].append('g')
    if form.filter_r.data is True:
        msg['filters'].append('r')
    if form.filter_i.data is True:
        msg['filters'].append('i')
    if form.filter_z.data is True:
        msg['filters'].append('z')
    if form.filter_clear.data is True:
        msg['filters'].append('clear')
    if form.filter_ha.data is True:
        msg['filters'].append('ha')

    return msg


def connect():
    """ Use the Flask config information to connect to the 
    MQTT broker in order to send the queue requset. 
    """

    # extract values from config
    host = config.get('default').MQTT_HOST
    port = config.get('default').MQTT_PORT

    # create client
    client = mqtt.Client()

    # try and connect
    try:
        client.connect(host, port, 60)
        return client
    except:
        # TODO: Somehow notify the user that the submission failed
        print(sys.exc_info())

    return None
