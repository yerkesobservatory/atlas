from flask import render_template, session, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from config import config
from . import admin
from .. import db
from ..models import User, Session

@admin.route('/', methods=['GET'])
def index():

    return redirect(url_for('auth.login'))
