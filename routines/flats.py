""" This function uses a connected telescope object to take a series of
flats.
"""


def take_flats(telescope: 'Telescope') -> bool:
    """ Automatically take a series of flats

    MORE DETAIL HERE

    Parameters
    ----------
    telescope: Telescope
        A connected telescope object

    Returns
    -------
    res: bool
        True if focus was successful, False if otherwise
    """
    # wait until sun is at -1
    telescope.wait_until_good(sun=-1)

    # turn any dome lamps off
    telescope.lamps_off()

    # open the observatory
    telescope.open_dome()

    # wait until chip cools down
    while True:
        count: int = 0
        temp: float = telescope.chip_temp('primary')

        if temp < 2:
            telescope.log.info('Telescope CCD reached 2 degrees. Continuing...')
            break
        else:
            count += 1
            telescope.keep_open(60)
            telescope.wait(60) # wait for 60 seconds so we can cool

        if count > 5:
            telescope.log.warning('Telescope CCD unable to reach temperature')

    # at this point, CCD chip should be at operating temperature

    # disable tracking, and point the telescope straight up
    status = telescope.disable_tracking()
    status = status and telescope.goto_point(ha=SOMETHING, dec=SOMETHING)

    # move the dome so we can see out, and keep it open
    status = status and telescope.move_dome(SOMETHING)
    telescope.keep_open(600)

    # check if any of the above commands failed
    if not status:
        telescope.log.error('There was an error setting up the telescope for sky flats. Quitting...')
        return False;

    




