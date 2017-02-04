from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms import DecimalField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class LoginForm(FlaskForm):
    """ Represents the login form for the SEO website.
    """
    email = StringField('Email', validators=[DataRequired(), Email(), Length(5, 64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 64)])
    submit = SubmitField('Submit')


class RegistrationForm(FlaskForm):
    """ Allows a user to fill out their details and register
    for web access.
    """
    token = StringField('Token', validators=[DataRequired()])
    firstname = StringField('First Name', validators=[DataRequired(), Length(3, 64)])
    lastname = StringField('Last Name', validators=[DataRequired(), Length(3, 64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(3, 64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(12, 128)])
    affiliation = StringField('Affiliation', validators=[DataRequired(), Length(3, 64)])
    minor = BooleanField('Minor', validators=[DataRequired()])
    submit = SubmitField('Submit')


class PasswordRequestForm(FlaskForm):
    """ Allows a user to enter their email and have their password reset.
    """
    email = StringField('Email', validators=[DataRequired(), Email(), Length(3, 64)])
    submit = SubmitField('Submit')


class PasswordResetForm(FlaskForm):
    """ Allows a user to enter a new password for their account.
    """
    password = PasswordField('New Password', [DataRequired(),
                                              EqualTo('confirm', message='Passwords must match')])
    confirm  = PasswordField('Repeat Password')
    submit = SubmitField('Submit')
