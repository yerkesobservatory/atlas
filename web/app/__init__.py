from flask import Flask, render_template
from config import config
import flask_mail
import flask_bootstrap
import flask_sqlalchemy
import flask_login

# initialize global contexts
mail = flask_mail.Mail()
db = flask_sqlalchemy.SQLAlchemy()
boostrap = flask_bootstrap.Bootstrap()

# init authentication
login_manager = flask_login.LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'

def create_app(config_name):
    """ Create the app using the appropriate configuration specified
    in config.py - uses blueprints stored in views.py and errors.py
    """

    # create app and load config from file
    app = Flask(__name__, template_folder='templates/')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # initialize flask extensions
    boostrap.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)

    # register main routes and error handlers
    # must be imported here to avoid circular dep
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # register authentication routing
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # done
    return app
