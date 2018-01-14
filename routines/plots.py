""" This function provides functions to make various astronomical plots. """
import io
import astropy
import datetime
import matplotlib
import numpy as np
import astropy.units as units
import astropy.time as time
import matplotlib.pyplot as plt
import astropy.coordinates as coordinates
from config import config
from routines import lookup

def visibility_curve(target: str) -> matplotlib.figure.Figure:
    """ Generate the visibility curve of a target object for the next
    24 hours.

    parameters
    ----------
    target: str
        The name of the target.
        Will be converted to RA/Dec using the code in /lookup.

    authors
    -------
        @mcnowinski
        @rprechelt
    """

    # convert target name to RA/Dec and make SkyCoord object
    try:
        ra, dec = lookup.lookup(target)
        target_coord = coordinates.SkyCoord(ra, dec, unit='deg')
    except Exception as e:
        print('An error occured locating the object')
        return None

    # create observer location
    observer = coordinates.EarthLocation(lat=config.general.latitude*units.deg,
                                             lon=config.general.longitude*units.deg,
                                             height=config.general.altitude*units.m)

    # compute the times at which we sample objects visibility
    now = time.Time(datetime.datetime.utcnow(), scale='utc')
    delta_times = np.linspace(0, 24, 12*24)*units.hour
    sample_times = now + delta_times

    # compute altaz for object and sun at sample times
    sample_frames = coordinates.AltAz(obstime=sample_times, location=observer)
    object_altaz = target_coord.transform_to(sample_frames)
    sun_altaz = coordinates.get_sun(sample_times).transform_to(sample_frames)

    # sidereal angle at sample times
    sample_sidereal = now.sidereal_time('mean', config.general.longitude*units.deg) + \
                      np.linspace(0, 24, 12*24)*units.hourangle

    # process hour angles so that they are always less than 18
    hour_angles = np.zeros(len(sample_sidereal))
    # TODO: I feel like this could be made cleanere?
    for i, angle in enumerate((sample_sidereal - target_coord.ra).hour):
        if angle >= 18:
            hour_angles[i] = angle-24
        elif angle <= -18:
            hour_angles[i] = angle+24
        else:
            hour_angles[i] = angle

    # create the fig
    fig, ax = plt.subplots()

    # plot object altitude
    scatter = ax.scatter(delta_times, object_altaz.alt, c=object_altaz.az, cmap='viridis', label=target)

    # fill background depending upon sun
    ax.fill_between(delta_times.to('hr').value, 0, 90, sun_altaz.alt < -0*units.deg,
                    color='0.5', zorder=0)
    ax.fill_between(delta_times.to('hr').value, 0, 90, sun_altaz.alt < -18*units.deg,
                    color='k', zorder=0)

    # fill hour angle <= 5.3
    ax.fill_between(delta_times.to('hr').value, 0, 90, np.abs(hour_angles) <= 5.3,
                    color='LightBlue', alpha=0.4, zorder=0)

    # add colorbar
    fig.colorbar(scatter).set_label('Azimuth [deg]')

    # configure x-axis
    ax.set_xlim([0, 24])
    ax.set_xticks(np.arange(13)*2)
    ax.set_xlabel('Hours [from now]')

    # configure y-axis
    ax.set_ylim([0, 90])
    ax.set_ylabel('Altitude [deg]')

    return fig
