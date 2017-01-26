from flask_wtf import Form
from wtforms import StringField, SubmitField, PasswordField
from wtforms import DecimalField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(Form):
    """ Represents the login form for the SEO website. 
    """
    email = StringField('Email', validators=[DataRequired(), Email(), Length(5, 64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 64)])
    submit = SubmitField('Submit')
