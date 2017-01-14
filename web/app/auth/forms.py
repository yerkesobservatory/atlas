from flask_wtf import Form
from wtforms import StringField, SubmitField, PasswordField
from wtforms import DecimalField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email

class LoginForm(Form):
    """ Represents the login form for the SEO website. 
    """
    email = StringField('Email', validators=[DataRequired(), Email(), Length(5, 64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')
