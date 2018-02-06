""" This file provides functions to WCS pinpoint a connected telescope
object to a given RA/Dec.
"""

import re
import typing
import astropy.coordinates as coordinates
import astropy.units as units
from config import config

def point(ra: str, dec: str, telescope: 'Telescope') -> bool:
    """ Pinpoint the telescope to a given RA and Dec.

    Given string representations of RA and Dec, and a connected
    Telescope object, repeatedly image the location, and solve the
    WCS field to get the offsets between actual and current pointings
    and apply these offsets to the telescope. This is repeated until
    the required pointing accuracy is achieved.

    Parameters
    ----------
    ra: str
        A string representation of right-ascension; 'hh:mm:ss'
    dec: str
        A string representation of declination; 'dd:mm:ss'
    telescope: Telescope
        A connected Telescope object

    Returns
    -------
    res: bool
        True if pointing was successful, False if otherwise

    Notes
    ------
    Author: mcnowinski
    Author: rprechelt

    """

    # we try and parse RA and DEC
    try:
        # convert arguments to astropy angle objects
        ra_target = coordinates.Angle(ra, unit=units.hourangle).degree
        dec_target = coordinates.Angle(dec, unit=units.deg).degree
    except Exception as e:
        telescope.log.warning('point: Unable to parse ra/dec.')
        return False

    # location of solve-field binary of astrometry
    solve_field = config.astrometry.bin_dir+'/solve-field'

    # static config parameters for astrometry
    downsample = config.astrometry.downsample
    scale_low = config.astrometry.scale_low
    scale_high = config.astrometry.scale_high
    radius = config.astrometry.radius
    cpu_limit = config.astrometry.cpu_limit
    min_ra_offset = config.astrometry.min_ra_offset
    min_dec_offset = config.astrometry.min_dec_offset
    max_ra_offset = config.astrometry.max_ra_offset
    max_dec_offset = config.astrometry.max_dec_offset
    max_tries = config.astrometry.max_tries

    # parameters for image command
    time = config.astrometry.exposure_time
    binning = config.astrometry.binning
    fits_fname = '/tmp/pointing'

    # setup loop variables at maximum values
    iteration = 0
    ra_offset = max_ra_offset
    dec_offset = max_dec_offset

    # set the telescope to the clear filter just in case it is not already
    telescope.change_filter('clear')

    # open the dome if it is closed
    if telescope.dome_open() is False:
        telescope.open_dome()
        telescope.keep_open(300)

    telescope.log.info('Beginning pinpoint iterations...')
    # we iterate taking images in each iteration and running astrometry
    while ((abs(ra_offset) > min_ra_offset or
            abs(dec_offset) > min_dec_offset) and
           iteration < max_tries ):

        # take the first image
        telescope.take_exposure(fits_fname, time, count = 1, binning = binning)

        # build the astrometry solve-field command
        astro_cmd = solve_field+(' --no-verify --overwrite --no-remove-lines --no-plots '
                                 '--downsample {} --cpulimit {} --dir /tmp/ '
                                 '--ra {} --dec {} --scale-unit arcsecperpix '
                                 '--scale-low {} --scale-high {} --radius {} '
                                 '--index-xyls none --axy none --temp-axy --solved none --match none '
                                 '--rdls none --corr none --pnm none --wcs none {}.fits '
                                 ''.format(downsample, cpu_limit, ra_target, dec_target,
                                           scale_low, scale_high, radius, fits_fname+'_0'))

        # run astrometry!
        output = telescope.run_command(astro_cmd)

        #look for field center in solve-field output
        match = re.search('RA,Dec \= \(([0-9\-\.\s]+)\,([0-9\-\.\s]+)\)', output)
        if match:
            # extract RA/DEC from image
            RA_image = match.group(1).strip()
            DEC_image = match.group(2).strip()
        else:
            telescope.log.warning('Field center RA/DEC not found in solve-field output!')
            return False

        # compute offsets in ra and dec between pointing and image
        dec_offset = float(dec_target) - float(DEC_image)
        ra_offset = float(ra_target) - float(RA_image)
        if ra_offset > 350:
            ra_offset -= 360.0

        # if they are valid offsets, apply them to the scope
        if abs(ra_offset) <= max_ra_offset and abs(dec_offset) <=max_dec_offset:
            telescope.log.info('dRA={} deg dDEC={} deg'.format(ra_offset, dec_offset))
            telescope.offset(ra_offset, dec_offset)
        else:
            telescope.log.warning('Calculated offsets too large '
                                  '(tx offset ra={} dec={})'.format(ra_offset, dec_offset))

        # everything worked - let's repeat
        iteration += 1

        # end while

    # if pinpoint was successful
    if (iteration < max_tries):
        telescope.log.info('Pinpoint was successful!')
        return True

    # pinpointing was unsuccessful
    telescope.log.warn('Pinpoint reached maximum tries and was not successful.')
    return False
