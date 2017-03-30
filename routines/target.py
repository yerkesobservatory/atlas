import typing
import numpy as np

def find_target(target: str) -> (str, str):
    """
    Given a string representing a target ('M 31', 'NGC 4584', 'Horsehead Nebula')
    return an (RA, DEC) string tuple of the following form

    ('hh:mm:sss', 'dd:mm:ss')

    as this form is compatible with `tx point`. 
    """

    return ('00:00:000', '00:00:00')
    
