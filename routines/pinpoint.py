import re
import os
import subprocess
import typing

import astropy.coordinates as coordinates
import astropy.units as units

def point(ra: str, dec: str, telescope: 'Telescope') -> bool:
    """ Pinpoint the telescope to a given RA and DEC. 

    Given representations of RA and DEC, and a connected Telescope
    object, repeatedly image the location, and solve the WCS field 
    to get the offsets between actual and current pointings and 
    apply these offsets to the telescope. This is repeated until
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

    """

    # we try and parse RA and DEC
    try:
        # convert arguments to astropy angle objects
        ra_target = coordinates.Angle(ra, unit=units.hour).degree
        dec_target = coordinates.Angle(dec, unit=units.deg).degree
    except Exception as e:
        telescope.log('point: Unable to parse ra/dec.', color='red')
        return False
        
    # astrometry is stored in seo/astrometry/bin directory
    seo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    astrometry_dir = '/'.join((seo_dir, 'astrometry', 'install', 'bin', ''))
    solve_field = astrometry_dir+'solve-field'
    solve_field = '/home/mcnowinski/astrometry/bin/solve-field'

    # static parameters for astrometry
    # TODO: these should be drawn from the global config file
    downsample = 2
    scale_low = 0.55; scale_high = 2.00
    radius = 20.0
    cpu_limit = 50
    min_ra_offset = 0.05; min_dec_offset = 0.05
    max_ra_offset = 20.0; max_dec_offset = 20.0
    max_tries = 20

    # parameters for image command on aster
    time = 10; binning = 2
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
        telescope.keep_open(900)

    telescope.log('Beginning pinpoint iterations...')
    # we iterate taking images in each iteration and running astrometry
    while ((abs(ra_offset) > min_ra_offset or
            abs(dec_offset) > min_dec_offset) and
            iteration < max_tries ):

        # take the first image
        telescope.take_exposure(fits_fname, time, binning)

        # build the astrometry solve-field command
        astro_cmd = solve_field+(' --no-verify --overwrite --no-remove-lines --no-plots '
                                 '--downsample {} --cpulimit {} --dir /tmp/ '
                                 '--ra {} --dec {} --scale-unit arcsecperpix '
                                 '--scale-low {} --scale-high {} --radius {} '
                                 '--index-xyls none --axy none --temp-axy --solved none --match none '
                                 '--rdls none --corr none --pnm none --wcs none {}.fits '
                                 ''.format(downsample, cpu_limit, ra_target, dec_target,
                                           scale_low, scale_high, radius, fits_fname))

        # run astrometry!
        output = telescope.run_command(astro_cmd)

        #look for field center in solve-field output
        match = re.search('RA,Dec \= \(([0-9\-\.\s]+)\,([0-9\-\.\s]+)\)', output)
        if match:
            # extract RA/DEC from image
            RA_image = match.group(1).strip()
            DEC_image = match.group(2).strip()		
        else:
            telescope.log('Field center RA/DEC not found in solve-field output!', color='red')
            return False

        # compute offsets in ra and dec between pointing and image
        dec_offset = float(dec_target) - float(DEC_image)
        ra_offset = float(ra_target) - float(RA_image)
        if ra_offset > 350:
            ra_offset -= 360.0

        # if they are valid offsets, apply them to the scope
        if abs(ra_offset) <= max_ra_offset and abs(dec_offset) <=max_dec_offset:
            telescope.offset(ra_offset, dec_offset)
            telescope.log('dRA={} deg dDEC={} deg'.format(ra_offset, dec_offset))
        else:
            telescope.log('Calculated offsets too large '
                          '(tx offset ra={} dec={})'.format(ra_offset, dec_offset))
            
        # everything worked - let's repeat
        iteration += 1

        # end while

    # if pinpoint was successful
    if (iteration < max_tries):
        return True

    # pinpointing was unsuccessful
    return False
