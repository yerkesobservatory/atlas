from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms import DecimalField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, Length

class QueueForm(FlaskForm):
    """ Represents the standard queue submission form.
    """
    target = StringField('Target', validators=[DataRequired()])
    exptime = IntegerField('Exposure Time', validators=[DataRequired()])
    expcount = IntegerField('Exposure Count', validators=[DataRequired()])
    binning = IntegerField('Binning', validators=[DataRequired()])
    filter_clear = BooleanField('clear')
    filter_ha = BooleanField('ha')
    filter_u = BooleanField('u')
    filter_g = BooleanField('g')
    filter_r = BooleanField('r')
    filter_i = BooleanField('i')
    filter_z = BooleanField('z')
    note = StringField('Note', validators=[Length(0, 16)])
    submit = SubmitField('Submit')
