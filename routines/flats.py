from telescope.telescope import Telescope

def take_flats(telescope: Telescope) -> bool:
    """ Pinpoint the telescope to a given RA and Dec. 

    Use a connected telescope to take a complete series of flat images and save
    them in the directory specified in the config files. This can be called before
    sunset and it will wait until an appropriate time to take flats. Return True
    if flats were taken successfully.

    Parameters
    ----------
    telescope: Telescope
        A connected telescope object

    Returns
    -------
    res: bool
        True if successful, False if otherwise
    """
    return True
    
