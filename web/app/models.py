from flask_sqlalchemy import SQLAlchemy
from . import db, login_manager
from flask_login import UserMixin
import werkzeug.security as security
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app

class User(UserMixin, db.Model):
    """ This class represents a user for login/logout, and session management.
    Fields:
        id: unique id
        firstname: first name of user
        lastname: last name of user
        email: email address of user
        password: hashed-password of user
        affiliation:  organization user is affiliated with
        minor: a bool indicating whether user is a minor
        confirmed: whether account has been confirmed
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer,  primary_key=True)
    firstname = db.Column(db.String(64), index=True, unique=False)
    lastname = db.Column(db.String(64), index=True, unique=False)
    email = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128), index=False, unique=False)
    affiliation = db.Column(db.String(128), index=True, unique=False)
    phone = db.Column(db.String(12), index=False, unique=False)
    minor = db.Column(db.Boolean, index=True, unique=False, default=False)
    admin = db.Column(db.Boolean, index=True, unique=False, default=False)
    confirmed = db.Column(db.Boolean, index=True, default=False)

    @property
    def password(self):
        """ Prevent accessing of password hash.
        """
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        """ Computes the hash of a password and stores it in the db session.
        """
        self.password_hash = security.generate_password_hash(password)

    def verify_password(self, password):
        """ Verify that given password matches the stored password hash.
        """
        return security.check_password_hash(self.password_hash, password)

    @login_manager.user_loader
    def load_user(user_id):
        """ Callback to return user given user_id. Required for flask_login.
        """
        return User.query.get(int(user_id))


    def generate_reset_token(self, expiration=3600):
        """ Generate a password reset token to send to a user's email.
        """
        # generate JSON web token
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'id': self.id, 'email': self.email})

    def reset_password(self, token, new_password):
        """ Takes a token received by the web app and if it is valid,
        changes the user's password to the new password.
        """
        # try to load the token using the serializer
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False

        if data.get('id') == self.id and data.get('email') == self.email:
            self.password = new_password
            db.session.add(self)
            return True

        return False

    def generate_confirmation_token(self, expiration=3600):
        """ Generate a confirmation token to send to a user's email
        to validate that their email is correct.
        """
        # generate JSON web token
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        """ Confirm a received token matches the one received.
        """
        s = Serializer(current_app.config['SECRET_KEY'])
        # try and load the token data
        try:
            data = s.loads(token)
        except:
            return False

        # check that token matches user id
        if data.get('confirm') != self.id:
            return False

        # confirm user and add them to the db
        self.confirmed = True
        db.session.add(self)

        return True


    def __repr__(self):
        """ Pretty-printing of user objects. """
        return "<User %r>" % (self.email)
