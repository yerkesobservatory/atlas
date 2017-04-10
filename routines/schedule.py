import numpy as np
import typing
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun

def schedule(target_list: [str], endtime):
    """
    This function receives a list of target coordinates and outputs a primary
    observable target
    
    Inputs:
    -------
    target_list :str: :list: List containing the names of the targets (i.e. [(id, ra, dec), (id, ra, dec), ...]).
    endtime: :list: 'obj' datetime (i.e. datetime(year, month, day, hour, minute, second))
    
    Outputs:
    --------
    primary_target :str: (id, ra, dec) of the highest priority target
    wait :astropy.Time: Wait time in seconds until optimal observation.
    It takes the value -1 when the object(s) is not observable.
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
