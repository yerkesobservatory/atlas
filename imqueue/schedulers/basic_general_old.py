import pymongo
import datetime
import numpy as np
import astropy.units as units
import imqueue.database as database
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun
from typing import List, Dict
from config import config
from routines import pinpoint, lookup
from astropy.coordinates import Angle
from astroplan import FixedTarget
import re

#from telescope import Telescope

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
    Authors: apagul, rprechelt
    """
    f = open('/live/production/atlas/imqueue/schedulers/log_scheduler.txt', 'w')
    # build aray to hold temporary values
    max_altitude_time = {'target': [], 'altitude': [], 'time': [], 'wait': []}

    # location of observatory
    #observatory = EarthLocation(lat=38.2886*units.deg, lon=-122.50400*units.deg, height=75*units.m)
    observatory = EarthLocation(lat=config.general.latitude*units.deg,
                                lon=config.general.longitude*units.deg,
                                height=config.general.altitude*units.m)

    # compute necessary time variables
    start_time = str(Time.now())[:10]+" 00:00:00"
    fixed_start = Time(start_time, scale="utc")
    delta_fixed_start = np.linspace(0,15,50000)*units.hour
    fixed = fixed_start+delta_fixed_start
    altazframe = AltAz(obstime=fixed, location=observatory)
    sun_altaz = get_sun(fixed).transform_to(altazframe)

    # get times for sunset and sunrise
    sunset_time = fixed[np.where((sun_altaz.alt < -18*units.deg) == True)[0][0]]
    sunrise_time = fixed[np.where((sun_altaz.alt < -18*units.deg) == True)[0][-1]]

    # compute time and coordinates
    delta_obs_time = np.linspace(0, 15, 50000)*units.hour
    times = Time.now()+delta_obs_time
    print(Time.now(), file=f)
    times = times[np.where((times > sunset_time) & (times < sunrise_time))]
    frame = AltAz(obstime=times, location=observatory)

    # iterate over all the observations
    for i,observation in enumerate(observations):
        if not observation.get('RA') or not observation.get('Dec'):

            # if the target name is a RA/Dec string
            if re.search(r'\d{1,2}:\d{2}:\d{1,2}.\d{1,2}\s[+-]\d{1,2}:\d{2}:\d{1,2}.\d{1,2}',
                         observation.get('target')):
                ra, dec = observation.get('target').strip().split(' ')
                observation['RA'] = ra; observation['Dec'] = dec;
            else: # try and lookup by name
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
        #target = FixedTarget(coord=coord, name=observation['target'])

        # extract values
        target = observation['target']
        target_coordinates = center
        #input_coordinates = observation['RA']+" "+observation['Dec']
        #endtime = session['end']

        max_altitude_time['target'].append(target)

        #try:
        #    target_coordinates = SkyCoord(input_coordinates, unit=(units.hourangle, units.deg))
        #except:
        #    continue

        target_altaz = target_coordinates.transform_to(frame)
        if (np.max(target_altaz.alt)) > 40*units.degree:
            max_altitude_time['altitude'].append(np.max(target_altaz.alt))
            #logme('debuggingggggg...', max_altitude_time['target'])
        else:
            max_altitude_time['altitude'].append(0*units.degree)
            #logme('Not visible :(', max_altitude_time['target'])

        aux_time = times[np.argmax(target_altaz.alt)]
        max_altitude_time['time'].append(aux_time)

        aux_delta_time = delta_obs_time[np.argmax(target_altaz.alt)]

        if (max_altitude_time['altitude'][i]>0*units.degree) and (times[np.argmax(target_altaz.alt)] > sunset_time)\
           and (times[np.argmax(target_altaz.alt)] < sunrise_time): #and (times[np.argmax(target_altaz.alt)] < Time(endtime)):
            max_altitude_time['wait'].append(aux_delta_time.to(units.second))
        else:
            max_altitude_time['wait'].append(-1*units.s)

    max_altitude_time['time']=np.array(max_altitude_time['time'])
    good_object = np.array([max_altitude_time['wait'][itgt]>-1*units.s for itgt in range(len(max_altitude_time['wait']))])

    if np.count_nonzero(good_object)>0:
        if np.count_nonzero(good_object)>1:
            aux_id = np.argmin(Time(max_altitude_time['time'][good_object], scale='utc')-Time.now())
            print(Time.now(), file=f)
            print(Time(max_altitude_time['time'][good_object], scale='utc'), file=f)
            primary_target_id = np.where(good_object)[0][aux_id]
            primary_target = np.array(max_altitude_time['target'])[primary_target_id]
        else:
            primary_target_id = np.where(good_object)[0][0]
            primary_target = np.array(max_altitude_time['target'])[primary_target_id]
    else:
        return None, -1
    f.close()
    return observations[primary_target_id], int(max_altitude_time['wait'][primary_target_id].value),int(max_altitude_time['altitude'][primary_target_id].value)

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
    solar_system = ['mercury','venus','moon','mars','jupiter','saturn','uranus','neptune','pluto']
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
                      'bin'+str(observation.get('binning')), str(datetime.date.today()),
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
    # now we pinpoint
    telescope.log.info('Starting telescope pinpointing...')

    if observation.get('target').lower() in solar_system:
        too_bright = True

    if too_bright:
        pinpointable = False
        telescope.log.warn('Can\'t pinpoint to solar system object!')
    else:
        pinpointable = pinpoint.point(observation['RA'], observation['Dec'], telescope)
        telescope.log.info({pinpointable})
        # let's check that pinpoint did not fail
    if not pinpointable:
        telescope.log.warn('Pinpoint failed! Disabling pinpointing for this observation...')

    # extract variables
    exposure_time = observation['exposure_time']
    exposure_count = observation['exposure_count']
    binning = observation['binning']

    # do we want to take darks
    take_darks = 'dark' in observation['filters']
    filters=[]
    for filt in observation['filters']:
        if filt!='dark':
            filters.append(filt)
    # for each filter
    for filt in filters:
        telescope.log.info("looking at filters")
        # check weather - wait until weather is good
        telescope.wait_until_good()

        # if the telescope has randomly closed, open up
        telescope.open_dome()

        # check our pointing with pinpoint again
        #if pinpointable:
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
        if filt=="\"[OIII]\"":
            filt_name = "OIII"
        elif filt=="\"[SII]\"":
            filt_name = "SII"
        else:
            filt_name = filt
        # take exposures!
        telescope.take_exposure(basename_science.replace('{filter}', filt_name), exposure_time, exposure_count, binning, filt)
        database.Database.observations.update({'_id': observation['_id']}, {'$push': {'filenames': basename_science.replace('{filter}', filt_name)}})

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
                                 str(observation.get('execDate')),'seo',
                                 str(observation['email'].split('@')[0])])
    stars_path = '/'.join([user_path, fname.replace('{filter}_', '')]).strip('/')
    # we set the directory for the observations
    database.Database.observations.update({'_id': observation['_id']},
                                          {'$set': {'directory': f'{rawdirname}',
                                                    'starspath': f'{stars_path}'}})

    return True
