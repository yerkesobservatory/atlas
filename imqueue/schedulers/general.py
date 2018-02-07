import pymongo
import datetime
import astroplan
import numpy as np
import astropy.units as units
import imqueue.database as database
import astroplan.constraints as constraints
import astroplan.scheduling as scheduling
from astroplan import ObservingBlock, FixedTarget
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, Angle, get_sun
from typing import List, Dict
from config import config
from routines import pinpoint, lookup


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
    global_constraints = [constraints.AltitudeConstraint(min=config.telescope.min_alt*units.deg), # set minimum altitude
                          constraints.AtNightConstraint.twilight_nautical(),
                          constraints.LocalTimeConstraint(min=datetime.datetime.now().time(),
                                                          max=session['end'].time())]

    # list to store observing blocks
    blocks = []

    # create targets
    for observation in observations:
        # target coordinates
        center = SkyCoord(observation['RA']+' '+observation['Dec'], unit=(units.hourangle, units.deg))

        # create and apply offset
        ra_offset = Angle(observation['options'].get('ra_offset') or 0, unit=units.arcsec)
        dec_offset = Angle(observation['options'].get('dec_offset') or 0, unit=units.arcsec)

        # offset coordinates
        coord = SkyCoord(center.ra + ra_offset, center.dec + dec_offset)

        # create astroplan traget
        target = FixedTarget(coord=coord, name=observation['target'])

        # priority - if the observation has a priority, otherwise 1
        priority = observation['options'].get('priority') or 1

        # if specified, restrict airmass, otherwise no airmass restriction
        max_airmass = observation['options'].get('airmass') or 38
        airmass = constraints.AirmassConstraint(max=max_airmass, boolean_constraint = False)  # rank by airmass

        # if specified, use observations moon separation, otherwise use 2 degrees
        moon_sep = (observation['options'].get('moon') or config.queue.moon_separation)*units.deg
        moon = constraints.MoonSeparationConstraint(min=moon_sep)

        # time, airmass, moon, + altitude, and at night
        local_constraints = [airmass, moon]

        # create observing block for this target
        blocks.append(ObservingBlock.from_exposures(target, priority, observation['exposure_time']*units.second,
                                                    observation['exposure_count']*(len(observation['filters'])+1),
                                                    config.telescope.readout_time*units.second,
                                                    configuration = observation,
                                                    constraints = local_constraints))

    # we need to create a transitioner to go between blocks
    transitioner = astroplan.Transitioner(1*units.deg/units.second,
                                          {'filter': {'default': 4*units.second}})

    # create priority scheduler
    priority_scheduler = scheduling.PriorityScheduler(constraints = global_constraints,
                                                      observer = observatory,
                                                      transitioner = transitioner)

    # initialize the schedule
    schedule = scheduling.Schedule(Time(session['start']), Time(session['end']))

    # schedule!
    schedule = priority_scheduler(blocks, schedule)

    # print(schedule.to_table())
    # print(f'observing_blocks: {schedule.observing_blocks}')
    # print(f'open_slots: {schedule.open_slots}')
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
    # TODO: support observations which only have RA/Dec
    # TODO: replace _id[0:3] with number from program
    fname = '_'.join([str(datetime.date.today()),
                      observation['email'].split('@')[0], observation['target'].replace(' ', '_'),
                      observation['_id'][0:3]])
    dirname = '/'.join(['', 'home', config.telescope.username, 'data',
                        observation['email'].split('@')[0], fname])

    # create directories
    telescope.log.info('Making directory to store observations on telescope server...')
    telescope.make_dir(dirname+'/raw/science')
    telescope.make_dir(dirname+'/raw/dark')
    telescope.make_dir(dirname+'/raw/bias')
    telescope.make_dir(dirname+'/processed')

    # generate basename
    filebase = '_'.join([str(datetime.date.today()),
                                               observation['email'].split('@')[0],
                                               observation['target'].replace(' ', '_')])
    basename_science = f'{dirname}/raw/science/'+filebase
    basename_bias = f'{dirname}/raw/bias/'+filebase
    basename_dark = f'{dirname}/raw/dark/'+filebase

    # we should be pointing roughly at the right place
    telescope.log.info('Performing a basic point...')
    good_pointing = telescope.goto_point(observation['RA'], observation['Dec'], rough=True)

    # now we pinpoint
    telescope.log.info('Starting telescope pinpointing...')
    pinpointable = pinpoint.point(observation['RA'], observation['Dec'], telescope)

    # let's check that pinpoint did not fail
    if not pinpointable:
        telescope.log.warn('Pinpoint failed! Disabling pinpointing for this observation...')

    # extract variables
    exposure_time = observation['exposure_time']
    exposure_count = observation['exposure_count']
    binning = observation['binning']

    # for each filter
    for filt in observation['filters']:

        # check weather - wait until weather is good
        telescope.wait_until_good()

        # if the telescope has randomly closed, open up
        telescope.open_dome()

        # check our pointing with pinpoint again
        telescope.log.info('Re-pinpointing telescope...')
        if pinpointable:
            pinpointable = pinpoint.point(observation['RA'], observation['Dec'], telescope)
        else:
            telescope.goto_point(observation['RA'], observation['Dec'], rough=True)

        # reenable tracking
        telescope.enable_tracking()

        # keep open for filter duration - 60 seconds for pintpoint per exposure
        telescope.keep_open(exposure_time*exposure_count + 300)

        # take exposures!
        telescope.take_exposure(basename_science+f'_{filt}', exposure_time, exposure_count, binning, filt)

    # reset filter back to clear
    telescope.log.info('Switching back to clear filter')
    telescope.change_filter('clear')

    # take exposure_count darks
    telescope.take_dark(basename_dark, exposure_time, exposure_count, binning)

    # take numbias*exposure_count biases
    telescope.take_bias(basename_bias, 10*exposure_count, binning)

    # we have finished the observation, let's update record
    # with execDate and mark it completed
    # TODO: we have to get rid of stars.uchicago.edu reference here
    database.Database.observations.update({'_id': observation['_id']},
                                          {'$set':
                                           {'completed': True,
                                            'execDate': datetime.datetime.now()}})


    return True
