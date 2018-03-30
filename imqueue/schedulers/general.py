import re
import pymongo
import datetime
import astroplan
import numpy as np
import astropy.units as units
import imqueue.database as database
import astroplan.constraints as constraints
import astroplan.scheduling as scheduling
from config import config
from typing import List, Dict
from astropy.time import Time
from routines import pinpoint, lookup
from astroplan import ObservingBlock, FixedTarget
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, Angle, get_sun



def schedule(observations: List[Dict], session: Dict, program: Dict) -> List[ObservingBlock]:
    """ Return the next object to be imaged according to the 'general' scheduling
    algorithm, and the time that the executor must wait before imaging this observation.

    Parameters
    ----------
    observations: List[Dict]
        A list of dictionaries representing the observations to be scheduled
    program: Dict
        The Program object containing the configuration of this observational program

    Returns
    -------
    obs: Dict
        The next observation to be executed
    wait: int
         The time (in seconds) to wait before imaging this observation.

    Authors: rprechelt
    """
    # create observer
    observatory = astroplan.Observer(latitude=config.general.latitude*units.deg,
                                     longitude=config.general.longitude*units.deg,
                                     elevation=config.general.altitude*units.m,
                                     name=config.general.name, timezone="UTC")

    # build default constraints
    global_constraints = [constraints.AltitudeConstraint(min=config.telescope.min_alt*units.deg, boolean_constraint=False), # rank objects by altitude
                          constraints.AtNightConstraint.twilight_astronomical(), # must be darker than astronomical
                          constraints.TimeConstraint(min=Time(datetime.datetime.now()), # and occur between now and the end of the session
                                                     max=Time(session['end']))]

    # list to store observing blocks
    blocks = []
    
    # list solar system objects
    solar_system = ['mercury','venus','moon','mars','jupiter','saturn','uranus','neptune','pluto']
    too_bright = False
    
    # create targets
    for observation in observations:

        # the observation is missing RA/Dec
        if not observation.get('RA') or not observation.get('Dec'):

            # if the target name is a RA/Dec string
            if re.search(r'\d{1,2}:\d{2}:\d{1,2}.\d{1,2}\s[+-]\d{1,2}:\d{2}:\d{1,2}.\d{1,2}',
                         observation.get('target')):
                ra, dec = observation.get('target').strip().split(' ')
                observation['RA'] = ra; observation['Dec'] = dec;
            else: # try and lookup by name
                if observation.get('target') in solar_system:
                    too_bright = True
                ra, dec = lookup.lookup(observation.get('target'))

                if not ra or not dec:
                    print(f'Unable to compute RA/Dec for {observation.get("target")}.')
                    if database.Database.is_connected:
                        database.Database.observations.update({'_id': observation['_id']},
                                                              {'$set':
                                                               {'error': 'lookup'}})
                    continue

                # save the RA/Dec
                observation['RA'] = ra; observation['Dec'] = dec;
                if database.Database.is_connected:
                    database.Database.observations.update({'_id': observation['_id']},
                                                          {'$set':
                                                           {'RA': ra,
                                                            'Dec': dec}})

        # check whether observation has RA and Dec values
        if observation.get('RA') is None:
            continue
        if observation.get('Dec') is None:
            continue

        # target coordinates
        center = SkyCoord(observation['RA']+' '+observation['Dec'], unit=(units.hourangle, units.deg))

        # create and apply offset
        ra_offset = Angle(observation['options'].get('ra_offset') or 0, unit=units.arcsec)
        dec_offset = Angle(observation['options'].get('dec_offset') or 0, unit=units.arcsec)

        # offset coordinates
        coord = SkyCoord(center.ra + ra_offset, center.dec + dec_offset)

        # create astroplan traget
        target = FixedTarget(coord=coord, name=observation['target'])

        # list to store local constraints
        local_constraints = []

        # priority - if the observation has a priority, otherwise 1
        if observation['options'].get('priority'):
            priority = float(observation['options'].get('priority'))
        else:
            priority = 1.

        # if specified, restrict airmass, otherwise no airmass restriction
        if observation['options'].get('airmass'):
            local_constraints.append(constraints.AirmassConstraint(max=float(observation['options'].get('airmass')),
                                                                   boolean_constraint = False))

        # if specified, restrict maximum moon illumination, otherwise no restriction
        if observation['options'].get('moon_illumination'):
            local_constraints.append(constraints.MoonIlluminationConstraint(max=float(observation['options'].get('moon_illumination'))))

        # if specified, use observations moon separation, otherwise use 2 degrees
        if observation['options'].get('moon'):
            moon_sep = float(observation['options'].get('moon'))
        else:
            moon_sep = config.queue.moon_separation
        local_constraints.append(constraints.MoonSeparationConstraint(min=moon_sep*units.deg))

        # create observing block for this target
        blocks.append(ObservingBlock.from_exposures(target, priority, observation['exposure_time']*units.second,
                                                    observation['exposure_count']*(len(observation['filters'])+1),
                                                    config.telescope.readout_time*units.second,
                                                    configuration = observation,
                                                    constraints = local_constraints))

    # check if we were able to make at least one block
    if len(blocks) < 1:
        return None # we were unable to schedule any blocks

    # we need to create a transitioner to go between blocks
    transitioner = astroplan.Transitioner(1*units.deg/units.second,
                                          {'filter': {'default': 4*units.second}})

    # create priority scheduler
    priority_scheduler = scheduling.PriorityScheduler(constraints = global_constraints,
                                                      observer = observatory,
                                                      transitioner = transitioner)

    # initialize the schedule
    schedule = scheduling.Schedule(Time.now(), Time(session['end']))

    # schedule!
    schedule = priority_scheduler(blocks, schedule)

    # print(schedule.to_table())
    # print(f'observing_blocks: {schedule.observing_blocks}')
    # print(f'open_slots: {schedule.open_slots}
    # print(f'scheduled_blocks: {schedule.scheduled_blocks}')

    # return the scheduled blocks
    return schedule

def execute(observation: Dict[str, str], program: Dict[str, str], telescope) -> bool:
    """ Observe the request observation and save the data according to the parameters of the program.

    This function is provided a connected Telescope() object that should be used to execute
    the observation, and a connected MongoDB client to allow for temporary changes to be stored
    in the observation for next time.

    Parameters
    ----------
    observation: Dict[str, str]
        The observation to be observed
    program: Dict[str, str]
        The observing program that this observation belongs to
    telescope: Telescope
        A connected Telescope object

    Returns
    -------
    success: bool
        Returns True if successfully executed, False otherwise

    Authors: rprechelt
    """
    # point telescope at target
    telescope.log.info(f'Slewing to {observation["target"]}')

    # we must enable tracking before we start slewing
    telescope.enable_tracking()

    # try and point object roughly
    if telescope.goto_point(observation['RA'], observation['Dec'], rough=True) is False:
        telescope.log.warn('Object is not currently visible. Skipping...')
        return False

    # create basename for observations
    # TODO: replace _id[0:3] with number from program
    if re.search(r'\d{1,2}:\d{2}:\d{1,2}.\d{1,2} [+-]\d{1,2}:\d{2}:\d{1,2}.\d{1,2}',
                                 observation.get('target')):
        split_name = observation.get('target').replace(':', '').split(' ')
        ra = split_name[0].replace(':', 'h', 1).replace(':', 'm', 1)+'s'
        dec = split_name[0].replace(':', 'd', 1).replace(':', 'm', 1)+'s'
        target_str = f'{ra}_{dec}'
    else:
        target_str = observation['target'].replace(' ', '_').replace("'", '')

    fname = '_'.join([target_str, '{filter}', observation.get('exptime'), 's',
                      'bin', observation.get('binning'), str(datetime.date.today()),
                      'seo', observation['email'].split('@')[0]])
    rawdirname = '/'.join([observation['email'].split('@')[0], fname.replace('{filter}_', '')]).strip('/')
    dirname = '/'.join(['', 'home', config.telescope.username, 'data', rawdirname])


    # create directories
    telescope.log.info('Making directory to store observations on telescope server...')
    telescope.make_dir(dirname+'/raw/science')
    telescope.make_dir(dirname+'/raw/dark')
    telescope.make_dir(dirname+'/raw/bias')
    telescope.make_dir(dirname+'/processed')

    # generate basename
    filebase = '_'.join([str(datetime.date.today()),
                         observation['email'].split('@')[0],
                         target_str])
    basename_science = f'{dirname}/raw/science/'+fname
    basename_bias = f'{dirname}/raw/bias/'+fname.replace('{filter}', 'bias')
    basename_dark = f'{dirname}/raw/dark/'+fname.replace('{filter}', 'dark')

    # we should be pointing roughly at the right place
    telescope.log.info('Performing a basic point...')
    good_pointing = telescope.goto_point(observation['RA'], observation['Dec'], rough=True)

    # now we pinpoint
    telescope.log.info('Starting telescope pinpointing...')
    if too_bright:
        pinpointable = False
        telescope.log.warn('Can\'t pinpoint to solar system object!')
    else:
        pinpointable = pinpoint.point(observation['RA'], observation['Dec'], telescope)

    # let's check that pinpoint did not fail
    if not pinpointable:
        telescope.log.warn('Pinpoint failed! Disabling pinpointing for this observation...')

    # extract variables
    exposure_time = observation['exposure_time']
    exposure_count = observation['exposure_count']
    binning = observation['binning']

    # do we want to take darks
    take_darks = 'dark' in observation['filters']

    # for each filter
    for filt in observation['filters'].remove('dark'):

        # check weather - wait until weather is good
        telescope.wait_until_good()

        # if the telescope has randomly closed, open up
        telescope.open_dome()

        # check our pointing with pinpoint again
        if pinpointable:
            telescope.log.debug('Re-pinpointing telescope...')
            pinpointable = pinpoint.point(observation['RA'], observation['Dec'], telescope)
        else:
            telescope.log.debug('Doing a basic re-point...')
            telescope.goto_point(observation['RA'], observation['Dec'], rough=True)

        # reenable tracking
        telescope.log.debug('Enabling tracking...')
        telescope.enable_tracking()

        # keep open for filter duration - 60 seconds for pintpoint per exposure
        telescope.keep_open(exposure_time*exposure_count + 300)

        # take exposures!
        telescope.take_exposure(basename_science.replace('{filter}', filt), exposure_time, exposure_count, binning, filt)
        database.Database.observations.update({'_id': observation['_id']}, {'$push': {'filenames': basename_science.replace('{filter}', filt)}})

    # reset filter back to clear
    telescope.log.info('Switching back to clear filter')
    telescope.change_filter('clear')

    # we are done taking science frames, let's take some bias frames to clear the CCD of any residual charge
    telescope.take_bias('/tmp/clear.fits', 10, binning)

    # take exposure_count darks
    if take_darks:
        telescope.take_dark(basename_dark, exposure_time, exposure_count, binning)

    # take numbias*exposure_count biases
    telescope.take_bias(basename_bias, 10*exposure_count, binning)

    # we set the directory for the observations
    database.Database.observations.update({'_id': observation['_id']}, {'$set': {'directory': f'{rawdirname}'}})

    # we have finished the observation, let's update record
    # with execDate and mark it completed
    # TODO: we have to get rid of stars.uchicago.edu reference here
    database.Database.observations.update({'_id': observation['_id']},
                                          {'$set':
                                           {'completed': True,
                                            'execDate': datetime.datetime.now()}})


    return True
