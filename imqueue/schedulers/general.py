import pymongo
import datetime
import numpy as np
import astropy.units as units
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

    Authors: apagul, rprechelt
    """
    
    # build aray to hold temporary values
    max_altitude_time = {'target': [], 'altitude': [], 'time': [], 'wait': []}

    # location of observatory
    observatory = EarthLocation(lat=config.general.latitude*units.deg,
                                lon=-config.general.longitude*units.deg,
                                height=config.general.altitude*units.m)    

    # compute necessary time variables
    start_time = str(Time.now())[:10]+" 00:00:00"
    fixed_start = Time(start_time, scale="utc")
    delta_fixed_start = np.linspace(0,15,1000)*units.hour
    fixed = fixed_start+delta_fixed_start
    altazframe = AltAz(obstime=fixed, location=observatory)  
    sun_altaz = get_sun(fixed).transform_to(altazframe)
    
    # get times for sunset and sunrise
    sunset_time = fixed[np.where((sun_altaz.alt < -12*units.deg) == True)[0][0]]
    sunrise_time = fixed[np.where((sun_altaz.alt < -12*units.deg) == True)[0][-1]]

    # compute time and coordinates
    delta_obs_time = np.linspace(0, 15, 1000)*units.hour
    times = Time.now()+delta_obs_time
    times = times[np.where((times > sunset_time) & (times < sunrise_time))]
    frame = AltAz(obstime=times, location=observatory)

    # iterate over all the observations
    for i,observation in enumerate(observations):

        # extract values
        target = observation['target']
        input_coordinates = observation['RA']+" "+observation['Dec']
        endtime = session['end']
        
        max_altitude_time['target'].append(target[0])

        try:
            target_coordinates = SkyCoord(input_coordinates, unit=(units.hourangle, units.deg))
        except:
            continue
        
        target_altaz = target_coordinates.transform_to(frame)
        if (np.max(target_altaz.alt)) > 40*units.degree:
            max_altitude_time['altitude'].append(np.max(target_altaz.alt))
        else:
            max_altitude_time['altitude'].append(0*units.degree)
            
        aux_time = times[np.argmax(target_altaz.alt)]
        max_altitude_time['time'].append(aux_time)
        
        aux_delta_time = delta_obs_time[np.argmax(target_altaz.alt)]

        if (max_altitude_time['altitude'][i]>0*units.degree) and (times[np.argmax(target_altaz.alt)] > sunset_time)\
           and (times[np.argmax(target_altaz.alt)] < sunrise_time) and (times[np.argmax(target_altaz.alt)] < Time(endtime)):
            max_altitude_time['wait'].append(aux_delta_time.to(units.second))
        else:
            max_altitude_time['wait'].append(-1*units.s)
            
    max_altitude_time['time']=np.array(max_altitude_time['time'])
    good_object = np.array([max_altitude_time['wait'][itgt]>-1*units.s for itgt in range(len(max_altitude_time['wait']))])
    
    if np.count_nonzero(good_object)>0:
        if np.count_nonzero(good_object)>1:
            aux_id = np.argmin(Time(max_altitude_time['time'][good_object])-Time.now())
            primary_target_id = np.where(good_object)[0][aux_id]
            primary_target = np.array(max_altitude_time['target'])[primary_target_id]
        else:
            primary_target_id = np.where(good_object)[0][0] 
            primary_target = np.array(max_altitude_time['target'])[primary_target_id]
    else:
        return None, -1
    
    return observations[primary_target_id], int(max_altitude_time['wait'][primary_target_id].value)

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
