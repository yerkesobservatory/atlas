import typing
import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import solar_system_ephemeris, SkyCoord, EarthLocation, AltAz, get_body
#from astropy.coordinates import get_body_barycentric, get_moon, Angle

def find_target(target: str) -> (str, str):
    """
    Given a string representing a target ('M 31', 'NGC 4584', 'Horsehead Nebula')
    return an (RA, DEC) string tuple of the following form

    ('hh:mm:sss', 'dd:mm:ss')

    as this form is compatible with `tx point`. 
    """

    seo = EarthLocation(lat=38.2886*u.deg, lon=-122.50400*u.deg, height=60*u.m)
    obs_time = Time.now()
    frame = AltAz(obstime=obs_time, location=seo)
    
    solar_system = ['mercury','venus','moon','mars','jupiter','saturn','uranus','neptune','pluto']
    solar_system_ephemeris.set('builtin')
    
    target = target.lower()
    
    if target in solar_system:
        celestial_body=get_body(target, obs_time, seo)
        return (celestial_body.ra.to_string(unit=u.hour, sep=':'),celestial_body.dec.to_string(unit=u.degree,sep=':'))
    else:
        target_coordinates = SkyCoord.from_name(target)
        return (target_coordinates.ra.to_string(unit=u.hour,sep=':'),target_coordinates.dec.to_string(unit=u.degree,sep=':'))
    
    #return ('00:00:000', '00:00:00')
    
