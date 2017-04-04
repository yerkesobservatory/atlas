import datetime
import sqlalchemy
from sqlalchemy import String, Integer, Boolean, Date, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
import werkzeug.security as security

Base = declarative_base()

class User(Base):
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
    id = sqlalchemy.Column(Integer,  primary_key=True)
    firstname = sqlalchemy.Column(String(64), index=True, unique=False)
    lastname = sqlalchemy.Column(String(64), index=True, unique=False)
    email = sqlalchemy.Column(String(64), index=True, unique=True)
    password_hash = sqlalchemy.Column(String(128), index=False, unique=False)
    affiliation = sqlalchemy.Column(String(128), index=True, unique=False)
    phone = sqlalchemy.Column(String(12), index=False, unique=False)
    minor = sqlalchemy.Column(Boolean, index=True, unique=False, default=False)
    admin = sqlalchemy.Column(Boolean, index=True, unique=False, default=False)
    today = datetime.date.today()
    default_expiry = datetime.date(today.year+1, today.month, today.day)
    expire = sqlalchemy.Column(Date, unique=False, default=default_expiry)
    confirmed = sqlalchemy.Column(Boolean, index=True, default=False)

    # relationships - one-to-many with session objects
    sessions = sqlalchemy.orm.relationship('Session', backref='user')

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

        
    def __repr__(self):
        """ Pretty-printing of user objects. """
        return "<User %r>" % (self.email)


    
class Session(Base):
    """ This class represents a session for queue observation.
    Fields:
        id: unique id
        target: a string representing the target name or RA/DEC pairs
        exposure_time: the time in seconds for each exposure
        exposure_count: the number of exposures to take for each filter
        filter_*: whether to use that filter in the exposure
        binning: the binning to use with the CCD
        user_id: the ID of the user who submitted this request
        submit_date: the date that the session was submitted
        executed: whether the session has been executed
        exec_date: the date and time that the user was executed
    """
    __tablename__ = 'queue'
    id = sqlalchemy.Column(Integer,  primary_key=True)
    target = sqlalchemy.Column(String(32), index=True, unique=False)
    exposure_time = sqlalchemy.Column(Float, unique=False)
    exposure_count = sqlalchemy.Column(Integer, unique=False)
    filter_i = sqlalchemy.Column(Boolean, unique=False, default=False)
    filter_r = sqlalchemy.Column(Boolean, unique=False, default=False)
    filter_g = sqlalchemy.Column(Boolean, unique=False, default=False)
    filter_u = sqlalchemy.Column(Boolean, unique=False, default=False)
    filter_z = sqlalchemy.Column(Boolean, unique=False, default=False)
    filter_ha = sqlalchemy.Column(Boolean, unique=False, default=False)
    filter_clear = sqlalchemy.Column(Boolean, unique=False, default=True)
    binning = sqlalchemy.Column(Integer, unique=False, default=2)
    user_id = sqlalchemy.Column(Integer, sqlalchemy.ForeignKey('users.id'))
    today = datetime.date.today()
    submit_date = sqlalchemy.Column(Date, index=True, unique=False, default=today)
    executed = sqlalchemy.Column(Boolean, index=True, unique=False, default=False)
    exec_date = sqlalchemy.Column(DateTime, index=True, nullable=True, unique=False, default=None)


    def __repr__(self):
        return "<Session {}: Target: {}, User: {}>".format(self.id, self.target, self.user.email)
