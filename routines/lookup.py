# This function provides utilities to convert a target name to a given RA/Dec at the telescope location
from config import config
from astroquery.simbad import Simbad
import astropy.units as units
import astropy.time as time
import astropy.coordinates as coordinates
import datetime

def lookup(target: str) -> (str, str):
    """ Convert a target name 'M31', 'NGC6946', to a RA/Dec pair using the location
    of the observatory. 

    Given a string representing a target ('M 31', 'NGC 4584', 'Horsehead Nebula')
    return an (RA, DEC) string tuple of the form ('hh:mm:sss', 'dd:mm:ss')


    Parameters
    ----------
    target: str
        A string representing the target name

    Returns
    -------
    ra: str
        String representation of right-ascension; 'hh:mm:ss'
    dec: str
        String representation of declination, 'dd:mm:ss'

    Notes
    -----
    Author: rprechelt
    """
    # location of observatory
    obs_location = coordinates.EarthLocation(lat=config.general.latitude*units.deg,
                                             lon=config.general.longitude*units.deg,
                                             height=config.general.altitude*units.m)
    
    obs_time = time.Time(datetime.datetime.utcnow(), scale='utc')
    #obs_time = time.Time.now()
    frame = coordinates.AltAz(obstime=obs_time, location=obs_location)

    # planetary bodies - TODO: Add moons
    solar_system = ['mercury','venus','moon','mars','jupiter','saturn','uranus','neptune','pluto']
    coordinates.solar_system_ephemeris.set('de432s')

    # convert it all to lowercase
    target = target.lower()
    
    # we have a planetary body
    if target in solar_system:
        celestial_body = coordinates.get_body(target, obs_time, obs_location)
        return (celestial_body.ra.to_string(unit=units.hour, sep=':'),
                celestial_body.dec.to_string(unit=units.degree,sep=':'))
    else: # stellar body
        try:
            target_coordinates = coordinates.SkyCoord.from_name(target)
            return (target_coordinates.ra.to_string(unit=units.hour,sep=':'),
                    target_coordinates.dec.to_string(unit=units.degree,sep=':'))
        except Exception as e:
            return None, None


def target_visible(target: str) -> bool:
    """ Check whether an object is visible.

    An object is defined as visible if its altitude is above the 
    altitude minimum given in the telescope config file.

    Parameters
    ----------
    target: str
        A string representing the target name

    Returns
    -------
    visible: bool
        A boolean indicating whether the target is visible or not

    Notes
    -----
    Author: rprechelt
    """
    ra, dec = lookup(target)
    return point_visible(ra, dec)

def point_visible(ra: str, dec: str) -> bool:
    """ Check whether an object is visible.

    An object is defined as visible if its altitude is above the 
    altitude minimum given in the telescope config file.

    Parameters
    ----------
    ra: str
        String representation of right-ascension; 'hh:mm:ss'
    dec: str
        String representation of declination, 'dd:mm:ss'

    Returns
    -------
    visible: bool
        A boolean indicating whether the target is visible or not

    Notes
    -----
    Author: rprechelt
    """

    # location of observatory
    obs_location = coordinates.EarthLocation(lat=config.general.latitude*units.deg,
                                             lon=config.general.longitude*units.deg,
                                             height=config.general.altitude*units.m)
    obs_time = time.Time.now()
    frame = coordinates.AltAz(obstime=obs_time, location=obs_location)

    # convert from (ra, dec) to (alt, az)
    print(ra, dec)
    point = coordinates.SkyCoord(ra, dec, unit=(units.hourangle, units.degree))
    altaz = point.transform_to(frame)

    # extract values
    alt = altaz.alt; az = altaz.az
    print(f"ALT: {alt}")

    # check that the altitude is above the minimum
    if alt >= config.telescope.min_alt*units.degree:
        return True

    return False
