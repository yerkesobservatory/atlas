import pymongo
import datetime
import astroplan
import numpy as np
import astropy.units as units
import astroplan.constraints as constraints
import astroplan.scheduling as scheduling
from astroplan import ObservingBlock, FixedTarget
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun
from typing import List, Dict
from config import config
from routines import pinpoint, lookup
from telescope import Telescope

def schedule(observations: List[Dict], session: Dict, program: Dict) -> (Dict, int):
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
                                     name="Atlas", timezone="UTC")

    # build default constraints
    global_constraints = [constraints.AltitudeConstraint(min=40*units.deg), # set minimum altitude
                   constraints.AtNightConstraint.twilight_astronomical(), # sun below -18
                   constraints.MoonSeparationConstraint(min=25*units.deg), # 25 degrees from moon
                   constraints.AirmassConstraint(max=5, boolean_constraint = False)] # rank by airmass

    # list to store observing blocks
    blocks = []
    
    # create targets
    for observation in observations:
        # target coordinates
        coord = SkyCoord(observation['RA']+' '+observation['Dec'], unit=(units.hourangle, units.deg))

        # create astroplan traget
        target = FixedTarget(coord=coord, name=observation['target'])

        # create time constraint
        ltc = constraints.LocalTimeConstraint(min=datetime.datetime.now().time(),
                                              max=session['end'].time())

        # priority - currently constant for all observations
        # TODO: enable user to set user-by-user priority
        priority = 1

        # create observing block for this target
        blocks.append(ObservingBlock.from_exposures(target, priority, observation['exposure_time']*units.second,
                                                    observation['exposure_count']*len(observation['filters']),
                                                    1*units.second,
                                                    configuration = {'filters': observation['filters']}, 
                                                    constraints = [ltc]))

    # we need to create a transitioner to go between blocks
    transitioner = astroplan.Transitioner(0.8*units.deg/units.second,
                                          {'filter': {'default': 3*units.second}})

    # create priority scheduler
    priority_scheduler = scheduling.PriorityScheduler(constraints = global_constraints,
                                                      observer = observatory,
                                                      transitioner = transitioner)

    # initialize the schedule
    schedule = scheduling.Schedule(Time(session['start']), Time(session['end']))

    # schedule!
    schedule = priority_scheduler(blocks, schedule)

    # print(schedule.to_table())
    print(f'observing_blocks: {schedule.observing_blocks}')
    print(f'open_slots: {schedule.open_slots}')
    print(f'scheduled_blocks: {schedule.scheduled_blocks}')
    
    exit()

def execute(observation: Dict, program: Dict, telescope: Telescope, db) -> bool:
    """ Observe the request observation and save the data according to the parameters of the program. 

    This function is provided a connected Telescope() object that should be used to execute
    the observation, and a connected MongoDB client to allow for temporary changes to be stored 
    in the observation for next time. 

    Parameters
    ----------
    observation: Dict
        The observation to be observed
    program: Dict
        The observing program that this observation belongs to
    telescope: Telescope
        A connected Telescope object
    db_client: pymongo.MongoClient
        A MongoClient connected to the database to allow for updating info

    Returns
    -------
    success: bool
        Returns True if successfully executed, False otherwise

    Authors: rprechelt
    """
    # point telescope at target
    telescope.log.info(f"Slewing to {observation['target']}")

    # we must enable tracking before we start slewing
    telescope.enable_tracking()

    # try and point object roughly
    if telescope.goto_point(observation['RA'], observation['Dec']) is False:
        telescope.log.warn('Object is not currently visible. Skipping...')
        return False

    # create basename for observations
    # TODO: support observations which only have RA/Dec
    # TODO: replace _id[0:3] with number from program
    dirname = '/home/rprechelt/data'+'/'+'_'.join([str(datetime.date.today()),
                                                    observation['email'].split('@')[0],
                                                    observation['target'],
                                                    observation['_id'][0:3]])

    # create directory
    telescope.log.info('Making directory to store observations on telescope server...')
    telescope.make_dir(dirname)

    # generate basename
    basename = dirname+'/'+'_'.join([str(datetime.date.today()),
                                                    observation['email'].split('@')[0],
                                                    observation['target']])

    # we should be pointing roughly at the right place
    # now we pinpoint
    telescope.log.info('Starting telescope pinpointing...')
    good_pointing = telescope.goto_point(observation['RA'], observation['Dec'])

    # let's check that pinpoint did not fail
    if good_pointing is False:
        telescope.log.warn('Pinpoint failed!')

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

        # keep open for filter duration - 60 seconds for pintpoint per exposure
        telescope.keep_open(exposure_time*exposure_count + 60)

        # check our pointing with pinpoint again
        telescope.log.info('Re-pinpointing telescope...')
        telescope.goto_point(observation['RA'], observation['Dec'])

        # reenable tracking
        telescope.enable_tracking()

        # take exposures!
        telescope.take_exposure(basename, exposure_time, exposure_count, binning, filt)

    # reset filter back to clear
    telescope.log.info('Switching back to clear filter')
    telescope.change_filter('clear')

    # take exposure_count darks
    telescope.take_dark(basename, exposure_time, exposure_count, binning)

    # take numbias*exposure_count biases
    telescope.take_bias(basename, exposure_count, binning)

    # we have finished the observation, let's update record
    # with execDate and mark it completed
    db.observations.update({'_id': observation['_id']},
                                  {'$set':
                                   {'completed': True,
                                    'execDate': datetime.date.today()}})

    return True
