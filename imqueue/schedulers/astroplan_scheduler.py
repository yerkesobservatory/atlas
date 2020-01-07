import re
import pymongo

import numpy as np
import imqueue.database as database
from config import config
from typing import List, Dict
from routines import pinpoint, lookup
import telescope.ssh_telescope as Telescope

import datetime
import astropy
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, Angle, get_sun
from astropy.utils.iers import conf
from astropy.table import Table
conf.auto_max_age = None

import astroplan
from astroplan.scheduling import Transitioner, SequentialScheduler, Schedule, PriorityScheduler
#import astroplan.scheduling as scheduling, Transitioner, SequentialScheduler, Schedule, PriorityScheduler
from astroplan.constraints import AtNightConstraint, AirmassConstraint, AltitudeConstraint, TimeConstraint
from astroplan import ObservingBlock, FixedTarget, Observer
from astroplan.plots import plot_airmass
from astroplan.plots import plot_parallactic
from astroplan.plots import plot_sky, plot_altitude
from astroplan import download_IERS_A

from pytz import timezone
#from astroplan.scheduling import Transitioner

download_IERS_A()

longitude = 237.49604 * u.deg
latitude = 38.288709 * u.deg
elevation = 63.924 * u.m
location = EarthLocation.from_geodetic(longitude, latitude, elevation)

seo = Observer(name='Stone Edge Observatory',
               location=location,
               #pressure=0.615 * u.bar,
               #relative_humidity=0.11,
               #temperature=0 * u.deg_C,
               timezone=timezone('US/Pacific'),
               description="Stone Edge Observatory in Sonoma, California")



def to_table(priority_schedule, show_transitions=True, show_unused=False):
    # TODO: allow different coordinate types
    target_names = []
    start_times = []
    end_times = []
    durations = []
    ra = []
    dec = []
    config = []
    for slot in priority_schedule.slots:
        if hasattr(slot.block, 'target'):
            start_times.append(slot.start.iso)
            end_times.append(slot.end.iso)
            durations.append(slot.duration.to(u.minute).value)
            target_names.append(slot.block.target.name)
            ra.append(slot.block.target.ra)
            dec.append(slot.block.target.dec)
            config.append(slot.block.configuration)
        elif show_transitions and slot.block:
            start_times.append(slot.start.iso)
            end_times.append(slot.end.iso)
            durations.append(slot.duration.to(u.minute).value)
            target_names.append('TransitionBlock')
            ra.append('-99.')
            dec.append('-99.')
            changes = list(slot.block.components.keys())
            if 'slew_time' in changes:
                changes.remove('slew_time')
            config.append(changes)
        elif slot.block is None and show_unused:
            start_times.append(slot.start.iso)
            end_times.append(slot.end.iso)
            durations.append(slot.duration.to(u.minute).value)
            target_names.append('Unused Time')
            ra.append('-99.')
            dec.append('-99.')
            config.append('')
    print (ra, dec)
    #ra = np.array(ra).astype(np.float)
    #dec = np.array(dec).astype(np.float)
    return Table([target_names, start_times, end_times, durations,
                  (ra), (dec), config],
                 names=('target', 'start time (UTC)', 'end time (UTC)',
                        'duration (minutes)', 'ra', 'dec', 'configuration'))

def lookup(obs):
    # location of observatory
    target = obs['target']
    obs_location = location

    obs_time = Time(datetime.datetime.utcnow(), scale='utc')
    frame = astropy.coordinates.AltAz(obstime=obs_time, location=obs_location)

    # planetary bodies - TODO: Add moons
    solar_system = ['mercury','venus','moon','mars','jupiter','saturn','uranus','neptune','pluto']
    astropy.coordinates.solar_system_ephemeris.set('de432s')

    # convert it all to lowercase
    target = target.lower()

    # we have a planetary body
    if target in solar_system:
        celestial_body = astropy.coordinates.get_body(target, obs_time, obs_location)
        return (celestial_body.ra.to_string(unit=u.hour, sep=':'),
                celestial_body.dec.to_string(unit=u.degree,sep=':'))
    else: # stellar body
        try:
            target_coordinates = astropy.coordinates.SkyCoord.from_name(target)
            return FixedTarget(coord=target_coordinates,name=target+" "+obs['_id'])

        except Exception as e:
            print(e)
            return None, None

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
    Authors: apagul
    """
    f = open('/live/production/atlas/imqueue/schedulers/log_scheduler.txt', 'w')
    ############## Set up observatory ###############

#    longitude = 237.49604 * u.deg
#    latitude = 38.288709 * u.deg
#    elevation = 63.924 * u.m
#    location = EarthLocation.from_geodetic(longitude, latitude, elevation)

#    seo = Observer(name='Stone Edge Observatory',
#                location=location,
#                timezone=timezone('US/Pacific'),
#                description="Stone Edge Observatory in Sonoma, California")

    # create the list of constraints that all targets must satisfy
    time = Time.now()
    sunset_tonight = seo.sun_set_time(time, which='nearest')
    sunrise_tomorrow = seo.sun_rise_time(time, which=u'next')

    global_constraints = [AltitudeConstraint(30*u.deg),
                        AtNightConstraint.twilight_astronomical(),
                        TimeConstraint(sunset_tonight, sunrise_tomorrow)]

    # Define the read-out time, exposure duration and number of exposures
    read_out = 1
    blocks = []

    time = Time.now()
    sunset_tonight = seo.sun_set_time(time, which='nearest')
    sunrise_tomorrow = seo.sun_rise_time(time, which=u'next')

    #night = TimeConstraint(sunset_tonight, sunrise_tomorrow)
    night = TimeConstraint(sunset_tonight, sunrise_tomorrow)
    obstime_constraint = TimeConstraint(time, sunrise_tomorrow)
    # Create ObservingBlocks for each filter and target with our time
    # constraint, and durations determined by the exposures needed
    for j,obs in enumerate(observations):

        input_obs = lookup(obs)
        ra = input_obs.ra.to_string(unit=u.hour, sep=':')
        dec = input_obs.dec.to_string(unit=u.degree,sep=':')
        #print(ra,dec)
        obs['RA'] = ra
        obs['Dec'] = dec
        #print input_obs, obs['exposure_time']*u.second, obs['exposure_count'],read_out*u.second
        if not ra or not dec:
            print(f'Unable to compute RA/Dec for {observation.get("target")}.')
            if database.Database.is_connected:
                database.Database.observations.update({'_id': observation['_id']},
                                                      {'$set':
                                                       {'error': 'lookup'}})
            continue

        if database.Database.is_connected:
            database.Database.observations.update({'_id': observation['_id']},
                                                  {'$set':
                                                   {'RA': ra, 'DEC': dec}})



        for i,filt in enumerate(obs['filters']):
            #print filt
            #print obs['exposure_count'] * (obs['exposure_time']*u.second + read_out*u.second)
            if len(obs['options']['priority']):
                bpriority = float(obs['options']['priority'])
            else:
                bpriority = 10.

            if obs['exposure_time']<30:
                aux = 30
            else:
                aux = obs['exposure_time']


            # list to store local constraints
            local_constraints = []

            
            # if specified, restrict airmass, otherwise no airmass restriction
            if observation['options'].get('airmass'):
                local_constraints.append(constraints.AirmassConstraint(max=float(observation['options'].get('airmass')),
                                                                       boolean_constraint=False))

            # if specified, restrict maximum moon illumination, otherwise no restriction
            if observation['options'].get('moon_illumination'):
                local_constraints.append(constraints.MoonIlluminationConstraint(
                    max=float(observation['options'].get('moon_illumination'))))

            # if specified, use observations moon separation, otherwise use 2 degrees
            if observation['options'].get('moon'):
                moon_sep = float(observation['options'].get('moon'))
            else:
                moon_sep = config.queue.moon_separation
            local_constraints.append(
                constraints.MoonSeparationConstraint(min=moon_sep*units.deg))


            b = ObservingBlock.from_exposures(input_obs,bpriority,
                                            aux*u.second,
                                            obs['exposure_count'],
                                            read_out*u.second,
                                            configuration = {'filter': filt},
                                            constraints = [obstime_constraint, local_constraints])
            blocks.append(b)


    # Initialize a transitioner object with the slew rate and/or the
    # duration of other transitions (e.g. filter changes)
    slew_rate = 1*u.deg/u.second
    transitioner = Transitioner(slew_rate,
                                {'filter':{('h-alpha','[OIII]','[SII]','g-band','r-band','i-band','clear'): 0.16*u.second,
                                            'default': 0.1*u.second}})



    # Initialize the sequential scheduler with the constraints and transitioner
    print("starting sequential scheduler")
    seq_scheduler = SequentialScheduler(constraints = global_constraints,
                                        observer = seo,
                                        transitioner = transitioner)
    print("initializing a schedule object")
    # Initialize a Schedule object, to contain the new schedule
    sequential_schedule = Schedule(sunset_tonight, sunrise_tomorrow)

    print("schedule the blocks")
    # Call the schedule with the observing blocks and schedule to schedule the blocks
    seq_scheduler(blocks, sequential_schedule)


    # Initialize the priority scheduler with the constraints and transitioner
    prior_scheduler = PriorityScheduler(constraints = global_constraints,
                                        observer = seo,
                                        transitioner = transitioner)
    # Initialize a Schedule object, to contain the new schedule
    priority_schedule = Schedule(sunset_tonight, sunrise_tomorrow)

    print(priority_schedule)
    # Call the schedule with the observing blocks and schedule to schedule the blocks
    prior_scheduler(blocks, priority_schedule)

    tab = to_table(sequential_schedule, show_transitions=True)
    print(tab)
    idval = tab['target'][0].split(" ")[-1]
    #print("idval:", idval)
    #print(observations)
    #print("database connected?:", database.Database.is_connected)
    #print("database observations:", database.Database.observations.find({'_id': idval}))

    #if database.Database.is_connected:

    #nextobs = database.Database.observations.find({'_id': idval})
    for obs in observations:
        if obs['_id']==idval:
            nextobs = obs
        else:
            continue
        #nextobs_index = observations['_id'].index(idval)
        #nextobs = observations[nextobs_index]
    print(nextobs)

    wait = ((Time(tab['start time (UTC)'][0])-Time.now()).to(u.second)).value

    print("wait:", wait)

    return nextobs, wait

def execute(observation: Dict, program: Dict, telescope, db) -> bool:
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
    solar_system = ['mercury', 'venus', 'moon', 'mars',
                    'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']
    too_bright = False

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

    if re.search(r'\d{1,2}:\d{2}:\d{1,2}.\d{1,2} [+-]\d{1,2}:\d{2}:\d{1,2}.\d{1,2}',
                 observation.get('target')):
        split_name = observation.get('target').replace(':', '').split(' ')
        ra = split_name[0].replace(':', 'h', 1).replace(':', 'm', 1)+'s'
        dec = split_name[0].replace(':', 'd', 1).replace(':', 'm', 1)+'s'
        target_str = f'{ra}_{dec}'
    else:
        target_str = observation['target'].replace(' ', '_').replace("'", '')

    fname = '_'.join([target_str, '{filter}', str(observation.get('exposure_time'))+'s',
                      'bin'+str(observation.get('binning')
                                ), str(datetime.date.today()),
                      'seo', observation['email'].split('@')[0]])
    rawdirname = '/'.join([observation['email'].split('@')
                           [0], fname.replace('{filter}_', '')]).strip('/')
    dirname = '/'.join(['', 'home', config.telescope.username,
                        'data', rawdirname])

    # create directories
    telescope.log.info(
        'Making directory to store observations on telescope server...')
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
    # now we pinpoint
    telescope.log.info('Starting telescope pinpointing...')

    if observation.get('target').lower() in solar_system:
        too_bright = True

    pinpointed = False
    if too_bright:
        pinpointed = True  # free pass for bright objects, good luck
        telescope.log.warn('Skipping pinpoint for solar system object.')
    else:
        pinpointed = pinpoint.point(
            observation['RA'], observation['Dec'], telescope, False)

    if not pinpointed:
        telescope.log.error('Pinpoint failed. Aborting observation...')
        #
        # we need to update the database status here
        #
        return False

    # extract variables
    exposure_time = observation['exposure_time']
    exposure_count = observation['exposure_count']
    binning = observation['binning']

    # do we want to take darks
    take_darks = 'dark' in observation['filters']
    filters = []
    for filt in observation['filters']:
        if filt != 'dark':
            filters.append(filt)
    # for each filter
    for filt in filters:
        telescope.log.info("looking at filters")
        # check weather - wait until weather is good
        telescope.wait_until_good()

        # if the telescope has randomly closed, open up
        telescope.open_dome()

        # check our pointing with pinpoint again
        # if pinpointable:
        #    telescope.log.debug('Re-pinpointing telescope...')
        #    pinpointable = pinpoint.point(observation['RA'], observation['Dec'], telescope)
        # else:
        #    telescope.log.debug('Doing a basic re-point...')
        #    telescope.goto_point(observation['RA'], observation['Dec'], rough=True)

        # reenable tracking
        telescope.log.debug('Enabling tracking...')
        telescope.enable_tracking()

        # keep open for filter duration - 60 seconds for pintpoint per exposure
        telescope.keep_open(exposure_time*exposure_count + 300)
        if filt == "\"[OIII]\"":
            filt_name = "OIII"
        elif filt == "\"[SII]\"":
            filt_name = "SII"
        else:
            filt_name = filt
        # take exposures!
        telescope.take_exposure(basename_science.replace(
            '{filter}', filt_name), exposure_time, exposure_count, binning, filt)
        database.Database.observations.update({'_id': observation['_id']}, {
                                              '$push': {'filenames': basename_science.replace('{filter}', filt_name)}})

    # reset filter back to clear
    telescope.log.info('Switching back to clear filter')
    telescope.change_filter('clear')

    # we are done taking science frames, let's take some bias frames to clear the CCD of any residual charge
    telescope.take_bias('/tmp/clear.fits', 10, binning)

    # take exposure_count darks
    if take_darks:
        telescope.take_dark(basename_dark, exposure_time,
                            exposure_count, binning)

    # take numbias*exposure_count biases
    telescope.take_bias(basename_bias, 10*exposure_count, binning)

    # we set the directory for the observations
   # database.Database.observations.update({'_id': observation['_id']}, {'$set': {'directory': f'{rawdirname}','starspath': f'{stars_path}'}})

    # we have finished the observation, let's update record
    # with execDate and mark it completed
    # TODO: we have to get rid of stars.uchicago.edu reference here
    database.Database.observations.update({'_id': observation['_id']},
                                          {'$set':
                                           {'completed': True,
                                            'execDate': datetime.datetime.now()}})
    user_path = observation['email'].split('@')[0].capitalize()
    observation_path = '_'.join([target_str, str(observation.get('exposure_time'))+'s',
                                 'bin'+str(observation.get('binning')),
                                 str(observation.get('execDate')), 'seo',
                                 str(observation['email'].split('@')[0])])
    stars_path = '/'.join([user_path,
                           fname.replace('{filter}_', '')]).strip('/')
    # we set the directory for the observations
    database.Database.observations.update({'_id': observation['_id']},
                                          {'$set': {'directory': f'{rawdirname}',
                                                    'starspath': f'{stars_path}'}})

    return True
