from flask_sqlalchemy import SQLAlchemy
from . import db, login_manager
from flask_login import UserMixin
import werkzeug.security as security

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
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer,  primary_key=True)
    firstname = db.Column(db.String(64), index=True, unique=False)
    lastname = db.Column(db.String(64), index=True, unique=False)
    email = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128), index=False, unique=False)
    affiliation = db.Column(db.String(128), index=True, unique=False)
    minor = db.Column(db.Boolean, index=True, unique=False, default=False)
    admin = db.Column(db.Boolean, index=True, unique=False, default=False)

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

    def __repr__(self):
        """ Pretty-printing of user objects. """
        return "<User %r>" % (self.email)
