import pymodm
from pymodm import fields


class Observation(pymodm.MongoModel):

    # unique primary id of this object
    id = fields.ObjectIdField(primary_key=True)

    # the target name or RA/DEC
    target = fields.CharField(min_length=2)

    # the time for each exposure
    exposure_time = fields.FloatField(min_value=0, max_value=1800)

    # the number of exposures of this object
    exposure_count = fields.IntegerField(min_value=1, max_value=100)

    # the filters to be used
    filters = fields.ListField(field=CharField)

    # the date it was submitted
    submit_date = fields.DateTimeField()

    # has this been executed
    executed = fields.BooleanField()
    
    # the date it was executed
    exec_date = fields.DateTimeField()

    

    
    
