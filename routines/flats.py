""" This function uses a connected telescope object to take a series of
flats.
"""
from astropy.io import fits
import datetime
import os

def take_flats(telescope: 'Telescope', config: 'Config') -> bool:
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

    #where should we put this?
    flats_image_sequence = [
    #   (bin,   filter,     count)
        (1,     'h-alpha',  5),
        (2,     'h-alpha',  5),   
        (1,     'z-band',  5),
        (1,     'r-band',  5),
        (1,     'i-band',  5),
        (1,     'g-band',  5), 
        (2,     'z-band',  5),
        (2,     'r-band',  5),                    
        (1,     'clear',   10),
        (2,     'i-band',  5),
        (2,     'g-band',  5),         
        (2,     'clear',   10)
    ]

    # wait until sun is at max_sun_alt_for_flats (e.g., -1 deg)
    telescope.wait_until_good(config.max_sun_alt_for_flats)

    # assume telescope is already locked by atlas?

    # turn any dome lamps off
    telescope.lamps_off()

    # open the observatory
    telescope.open_dome()

    # wait until chip cools down
    while not telescope.chip_temp_ok():
        count: int = 0

        if count == 0: #set cool command
            telescope.cool_ccd()
            #this can take a while - might want to call keep_open here too
        else: #wait for cooling
            telescope.keep_open(60)
            telescope.wait(60) # wait for 60 seconds so we can cool

        if count > 5:
            telescope.log.warning('Telescope CCD unable to reach temperature')

    # at this point, CCD chip should be at operating temperature

    # disable tracking
    status = telescope.disable_tracking()

    # point the telescope towards zenith and east; with a bit of wiggle included
    status = status and telescope.goto_point_for_flats()

    # move the dome so we can see out, and keep it open
    status = status and telescope.move_dome(config.telescope.dome_pos_for_flats)
    telescope.keep_open(1000)

    # check if any of the above commands failed
    if not status:
        telescope.log.error('There was an error setting up the telescope for sky flats. Quitting...')
        return False;

    # get the flats!
    for flat_image_set in flat_image_sequence:
        #set image parameters
        binning = flat_image_set[0]
        filter = flat_image_set[1]
        count = flat_image_set[2]
        filename = '_flat'
        #start exposure at default value, e.g. 1 s
        exposure = optimum_exposure = config.telescope.starting_exposure_for_flats
        #obtain count flats images
        for i in range(count):
            #take images until the exposure that gives the optimum count is greater than the min exposure allowed
            while optimum_exposure < config.telescope.min_exposure_for_flats:
                #change filter and take image
                if not telescope.take_exposure(filename, exposure, 1, binning, filter):
                    telescope.log.error('There was an error taking an image for sky flats. Quitting...')
                    return False #should we clean up?
                #get the mean count of the resulting fits file
                hdu_list = fits.open(filename+'.fits')
                image_data = hdu_list[0].data
                mean = np.mean(image_data)
                fits.close()
                #how close are we to the optimum count for flats?
                factor = float(config.telescope.optimum_count_for_flats)/float(mean)
                #calc new exposure time
                optimum_exposure = factor*config.telescope.exposure_scaling_fudge_for_flats*exposure
                if optimum_exposure > config.telescope.max_exposure_for_flats:
                    telescope.log.error('The exposure time (%f) is too long (> %f). Quitting...'%(optimum_exposure, config.telescope.max_exposure_for_flats))
                    return False #should we clean up?
                time.sleep(config.telescope.delay_between_test_flats)
            #we have our optimum exposure calculated. take a *real* flat
            exposure = optimum_exposure #update exposure
            flatname = 'flat_%s_%dsec_bin%d_%s_%s_num%d_seo.fits'%(filter, exposure, binning, config.telescope.username, datetime.datetime.utcnow().strftime('%Y%b%d_%Hh%Mm%Ss'), i)
            if not telescope.take_exposure(flatname, exposure, 1, binning, filter):
                telescope.log.error('There was an error taking an image for sky flats. Quitting...')
                return False #should we clean up?
            #get the mean count of the resulting fits file
            hdu_list = fits.open(flatname)
            image_data = hdu_list[0].data
            mean = np.mean(image_data)
            #how close are we to the optimum count for flats?
            factor = float(config.telescope.optimum_count_for_flats)/float(mean)
            #calc new exposure time
            optimum_exposure = factor*config.telescope.exposure_scaling_fudge_for_flats*exposure
            #shimmy the scope pointing
            telescope.goto_point_for_flats()       
                  








    




