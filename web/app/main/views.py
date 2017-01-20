from flask import render_template, session, redirect, url_for
from . import main
from .forms import LoginForm
from .. import db
from ..models import User

@main.route('/', methods=['GET'])
def index():

    # create new login form
    # form = LoginForm()
    
    # form has been successfully validated
    # if form.validate_on_submit():
    #     return redirect(url_for('.index'))

    # return page
    # return render_template('index.html',
    #                        form=form,  name=session.get('name'),
    #                        known=session.get('known', False))

    return render_template('main/index.html')
                           
                        
        
