from typing import List
from routines import pinpoint
from telescope.telescope import Telescope
from db.observation import Observation
from db.session import Session

def schedule(observations: List[Observation], session: Session) -> List[Observation]:
        """ Return the next object to be imaged according to this algorithm, and the
    time that the executor must wait before imaging this observation. 

    Parameters
    ----------
    observations: List[Observation]
        The observations to be observed as part of this session
    session: Session
        The Session object containing parameters for the observing session

    Returns
    -------
    obs: Observation
        The next observation that should be executed. 
    wait: int
        The number of seconds to wait before imaging this observation
    """
        
    max_altitude_time = {'target':[], 'altitude':[], 'time':[], 'wait':[]}   
     
    seo = EarthLocation(lat=38.2886*u.deg, lon=-122.50400*u.deg, height=60*u.m)    
    
    obs_time = Time.now()
    delta_obs_time = np.linspace(0, 15, 1000)*u.hour
    times = obs_time+delta_obs_time
    frame = AltAz(obstime=times, location=seo)
    
    start_time = str(Time.now())[:10]+" 00:00:00"
    fixed_start = Time(start_time, scale="utc")
    delta_fixed_start = np.linspace(0,15,1000)*u.hour
    fixed = fixed_start+delta_fixed_start
    altazframe = AltAz(obstime=fixed, location=seo)  
    sun_altaz = get_sun(fixed).transform_to(altazframe)
    
    sundown_time = fixed[np.where((sun_altaz.alt < -12*u.deg) == True)[0][0]]
    sunup_time = fixed[np.where((sun_altaz.alt < -12*u.deg) == True)[0][-1]]
    
    for i,target in enumerate(target_list):
        
        target_ra = target[1]
        target_dec = target[2]
        input_coordinates = target_ra+" "+target_dec
        
        max_altitude_time['target'].append(target[0])

        try:
            target_coordinates = SkyCoord(input_coordinates, unit=(u.hourangle, u.deg))
        except:
            continue
        
        target_altaz = target_coordinates.transform_to(frame)
        if (np.max(target_altaz.alt)) > 40*u.degree:
            max_altitude_time['altitude'].append(np.max(target_altaz.alt))
        else:
            max_altitude_time['altitude'].append(0*u.degree)
        
        aux_time = times[np.argmax(target_altaz.alt)]
        max_altitude_time['time'].append(aux_time)
        
        aux_delta_time = delta_obs_time[np.argmax(target_altaz.alt)]
    
        if (max_altitude_time['altitude'][i]>0*u.degree) & (times[np.argmax(target_altaz.alt)] > sundown_time)\
        & (times[np.argmax(target_altaz.alt)] < sunup_time) & (times[np.argmax(target_altaz.alt)] < Time(endtime,scale='utc')):
            max_altitude_time['wait'].append(aux_delta_time.to(u.second))
        else:
            max_altitude_time['wait'].append(-1*u.s)
            
    max_altitude_time['time']=np.array(max_altitude_time['time'])
    good_object = np.array([max_altitude_time['wait'][itgt]>-1*u.s for itgt in range(len(max_altitude_time['wait']))])
    
    if np.count_nonzero(good_object)>0:
        if np.count_nonzero(good_object)>1:
            aux_id = np.argmin(Time(max_altitude_time['time'][good_object])-Time.now())
            primary_target_id = np.where(good_object)[0][aux_id]
            primary_target = np.array(max_altitude_time['target'])[primary_target_id]
        else:
            primary_target_id = np.where(good_object)[0][0] 
            primary_target = np.array(max_altitude_time['target'])[primary_target_id]
    else:
        self.log("Scheduler couldn't pick an object")
        return (-1, -1, -1), -1
    
    return target, int(max_altitude_time['wait'][primary_target_id].value)


def execute(observation: Observation, telescope: Telescope, session: Session) -> bool:
    """ Observe the requested observation and save the data according to session. 

    This function is provided a connected Telescope() object that should be used
    to execute (observe) the target specified by Observation. The Session object 
    that includes this observation is also provided. 

    Parameters
    ----------
    observation: Observation
        The observation to be observed as part of this session
    telescope: Telescope
        A connected telescope object to be used to execute the observation.
    session: Session
        The Session object containing parameters for the observing session

    Returns
    -------
    success: bool
        Return True if successfuly, False otherwise. 
    """
    # point telescope at target
    telescop.log.info('Slewing to {}'.format(session.target))
    if telescope.goto(ra, dec) is False:
        telescope.log.warn('Object is not currently visible. Skipping...')
        return False

    # create directory
    telescope.log.info('Making directory to store observations on telescope server...')
    telescope.make_dir(dirname)

    # create basename for observations
    basename = dirname+'/'+'_'.join([date, username, session.target])

    # we should be pointing roughly at the right place
    # now we pinpoint
    telescope.log.info('Starting telescope pinpointing...')
    good_pointing = pinpoint.point(ra, dec, telescope)

    # let's check that pinpoint did not fail
    if good_pointing is False:
        telescope.log.warn('Pinpoint failed!')

    # extract variables
    exposure_time = observation.exposure_time
    exposure_count = observation.exposure_count
    binning = observation.binning

    # for each filter
    for filt in observation.filters:

        # check weather - wait until weather is good
        telescope.wait_until_good()

        # if the telescope has randomly closed, open up
        if telescopee.telescope.dome_open is False:
            telescope.open_dome()

        # check our pointing with pinpoint again
        telescope.log.info('Re-pinpointing telescope...')
        pinpoint.point(ra, dec, self.telescope)

        # reenable tracking
        telescope.enable_tracking()

        # take exposures!
        take_exposures(basename, exposure_time, exposure_count, binning, filt)

    # reset filter back to clear
    telescope.log.info('Switching back to clear filter')
    telescope.change_filter('clear')

    # take exposure_count darks
    telescop.take_darks(basename, exposure_time, exposure_count, binning)

    # take numbias*exposure_count biases
    telescope.take_biases(basename, exposure_time, exposure_count, binning, 3)

    return True
