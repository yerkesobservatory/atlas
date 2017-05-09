import pymodm
import datetime
from pymodm import fields


class Observation(pymodm.MongoModel):

    # create connection to database
    pymodm.connect("mongodb://localhost:3001/meteor", alias="atlas")

    # # the target name or RA/DEC
    target = fields.CharField(min_length=2)

    # # the time for each exposure
    exposure_time = fields.FloatField(min_value=0, max_value=1800)

    # # the number of exposures of this object
    exposure_count = fields.IntegerField(min_value=1, max_value=100)

    # # the filters to be used
    # filters = fields.ListField(field=fields.CharField, default=['clear'])

    # # the date it was submitted
    submit_date = fields.DateTimeField(default=datetime.datetime.now())

    # # has this been executed
    executed = fields.BooleanField(default=False)
    
    # # the date it was executed
    exec_date = fields.DateTimeField(default=None)

    class Meta:
        collection_name = 'observations'
        connection_alias = 'atlas'
        cascade = True