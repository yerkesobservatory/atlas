from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms import DecimalField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email

class QueueForm(FlaskForm):
    """ Represents the standard queue submission form.
    """
    target = StringField('Target', validators=[DataRequired()])
    exptime = DecimalField('Exposure Time', validators=[DataRequired()])
    expcount = IntegerField('Exposure Count', validators=[DataRequired()])
    binning = IntegerField('Binning', validators=[DataRequired()])
    filter_u = BooleanField('u')
    filter_g = BooleanField('g')
    filter_r = BooleanField('r')
    filter_i = BooleanField('i')
    filter_z = BooleanField('z')
    submit = SubmitField('Submit')
