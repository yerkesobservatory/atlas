

def schedule(sessions: list) -> list:
    """ This function gets given a list of dictionaries representing session
    objects, and needs to return a ordered/scheduled list of the same objects.
    """

    # example for how to extract fields
    session = sessions[0] # first imaging session in list
    target = session['target']
    exposure_time = session['exposure_time']
    exposure_count = session['exposure_count']
    filters = session['filters']
    session_time = (len(filters) + 1)*exposure_count*exposure_time+90 # total execution time in seconds for session
    # blah blah
