""" This function uses a connected telescope object to take a sequence of images for lightcurve studies.
"""
from astropy.io import fits
from config import config
import datetime
import time
import os
import json
import urllib.request
import re
from astroplan import Observer
import astropy.units as u
from astropy.time import Time
from . import ch
import numpy as np
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun, Angle

# lazy global logger linked to the telescope.log in get_lightcurve
logger = None

#
# the observatory
#

class Observatory():

    code = None
    latitude = 0.0  # in decimal degrees
    longitude = 0.0  # in decimal degrees
    altitude = 0.0  # in meters
    timzeone = None

    # init
    def __init__(self, code, latitude, longitude, altitude, timezone):
        self.code = code
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.timezone = timezone

    def toString(self):
        observatory_string = 'observatory: code=%s, lat=%f, lon=%f, alt=%f' % (
            self.code, self.latitude, self.longitude, self.altitude)
        return observatory_string

#
# an astronomical observation
#


class Observation():

    sequence = None  # image sequence
    target = None  # target
    observatory = None  # observatory
    observer = None  # who's observing?
    min_obs_alt = None  # min alt to start observations in deg

    # used by the Scheduler and others
    obs_start_time = None  # when will target best be observable?
    min_obs_time = None  # when is the target first observable?
    max_obs_time = None  # when is the target last observable?
    max_alt_time = None  # when is the
    active = True  # is this observation (still) active?
    id = -1  # id

    # init
    def __init__(self, observatory, target, sequence, min_obs_alt, observer):
        self.observatory = observatory
        self.target = target
        self.sequence = sequence
        self.min_obs_alt = min_obs_alt
        self.observer = observer
        # self.getTimes()

    def toString(self):
        return '%s\n%s\n%smin_alt=%f deg\nobs_time=%s\nid=%d\nactive=%d\nmin_obs_time=%s\nmax_obs_time=%s\nmax_alt_time=%s\nuser=%s' % (self.observatory.toString(), self.target.toString(), self.sequence.toString(), self.min_obs_alt, self.obs_start_time, self.id, self.active, self.min_obs_time, self.max_obs_time, self.max_alt_time, self.observer)

    # for this observation, get min/max observable times and max alt time
    def getTimes(self):
        # temp var to hold obs info
        obs = {'time': [], 'id': []}

        # init observatory location
        observatory_location = EarthLocation(
            lat=self.observatory.latitude*u.deg, lon=self.observatory.longitude*u.deg, height=self.observatory.altitude*u.m)
        # get next sunrise and nearest sunset times
        observatory_location_obsplan = Observer(longitude=self.observatory.longitude*u.deg, latitude=self.observatory.latitude *
                                                u.deg, elevation=self.observatory.altitude*u.m, name=self.observatory.code, timezone=self.observatory.timezone)
        sunset_time = observatory_location_obsplan.twilight_evening_nautical(
            Time.now(), which="nearest")
        sunrise_time = observatory_location_obsplan.twilight_morning_nautical(
            Time.now(), which="next")
        logger.debug('The nearest sunset is %s. The next sunrise is %s.' %
                     (sunset_time.iso, sunrise_time.iso))

        # build alt-az coordinate frame for observatory over next ? hours (e.g., nearest sunset to next sunrise)
        # start time is sunset or current time, if later...
        now = Time.now()
        if (now > sunset_time):
            obs_time = Time.now()
        else:
            obs_time = sunset_time
        delta_obs_time = np.linspace(
            0, (sunrise_time-obs_time).sec/3600., 1000)*u.hour
        # array of times between sunset and sunrise
        times = obs_time + delta_obs_time
        # celestial frame for this observatory over times
        frame = AltAz(obstime=times, location=observatory_location)

        # build target altaz relative to observatory
        target_ra = self.target.getRa()
        target_dec = self.target.getDec()
        input_coordinates = target_ra + " " + target_dec
        try:
            target_coordinates = SkyCoord(
                input_coordinates, unit=(u.hourangle, u.deg))
        except:
            pass
        target_altaz = target_coordinates.transform_to(frame)

        # when is target highest *and* above minimum altitude?
        # when is it above min_obs_alt?
        valid_alt_times = times[np.where(
            target_altaz.alt >= self.min_obs_alt*u.degree)]
        # when does the max alt occur?
        if len(valid_alt_times) > 0:
            self.min_obs_time = Time(
                np.min(times[np.where(target_altaz.alt > self.min_obs_alt*u.degree)]))
            self.max_obs_time = Time(
                np.max(times[np.where(target_altaz.alt > self.min_obs_alt*u.degree)]))
            self.max_alt_time = Time(
                times[np.argmax(target_altaz.alt)])
        else:
            logger.error('Target (%s) is not observable.' %
                         self.target.getName())


#
# a target
#


class Target():

    # init
    def __init__(self, name, ra, dec):
        self.name = name
        self.ra = ra  # hour:min:sec
        self.dec = dec  # deg:min:sec

    # init with name and type only
    @classmethod
    def from_name(cls, keyword, observatory, type):
        objects = Target.findObjects(keyword, observatory, type)
        if len(objects) == 0:
            logger.error('Could not find matching object for %s.' % keyword)
            sys.exit(1)
        else:
            if len(objects) > 1:
                logger.warn('Found multiple matching objects for %s. Using first object (%s).' % (
                    name, objects[0]['name']))
        target = cls(objects[0]['name'], objects[0]['ra'], objects[0]['dec'])
        return target

    # name
    def getName(self):
        return self.name

    def setName(self, name):
        self.name = name

    # ra = right ascension
    def getRa(self):
        return self.ra

    def setRa(self, ra):
        self.ra = ra

    # dec = declination
    def getDec(self):
        return self.dec

    def setDec(self, dec):
        self.dec = dec

    def toString(self):
        return 'target: name=%s, ra=%s, dec=%s' % (self.name, self.ra, self.dec)

    @staticmethod
    def findObjects(keyword, observatory, type):
        type = type.lower()
        if (type == 'asteroid' or type == 'planet' or type == 'solar system'):
            return Target.findSolarSystemObjects(keyword, observatory)
        elif (type == 'star' or type == 'celestial' or type == 'galaxy'):
            return Target.findCelestialObjects(keyword)
        else:
            logger.error("Unknown type (%s) in Target.findObjects." % type)
            return []

    @staticmethod
    def findCelestialObjects(keyword):
        results = Simbad.query_object(keyword)
        if results == None:
            return []
        objects = []
        for result in results:
            objects.append({'type': 'Celestial', 'id': result['MAIN_ID'], 'name': result['MAIN_ID'].replace(' ', ''),
                            'ra': result['RA'], 'dec': result['DEC']})
        return objects

    # search solar system small bodies using JPL HORIZONS
    @staticmethod
    def findSolarSystemObjects(keyword, observatory):
        # ch constants
        # max airmass
        max_airmass = 2.0  # 30 deg elevation
        objects = []
        # list of matches
        object_names = []
        # set to * to make the searches wider by default
        suffix = ''
        # two passes, one for major (and maybe small) and one for (only) small bodies
        lookups = [keyword + suffix, keyword + suffix + ';']
        for repeat in range(0, 2):
            # user JPL Horizons batch to find matches
            f = urllib.request.urlopen('https://ssd.jpl.nasa.gov/horizons_batch.cgi?batch=l&COMMAND="%s"' %
                                urllib.request.quote(lookups[repeat].upper()))
            output = f.read().decode('utf-8')  # the whole enchilada
            # print output
            lines = output.splitlines()  # line by line
            # no matches? go home
            if re.search('No matches found', output):
                logger.debug('No matches found in JPL Horizons for %s.' %
                             lookups[repeat].upper())
            elif re.search('Target body name:', output):
                logger.debug('Single match found in JPL Horizons for %s.' %
                             lookups[repeat].upper().replace(suffix, ''))
                # just one match?
                # if major body search (repeat = 0), ignore small body results
                # if major body search, grab integer id
                if repeat == 0:
                    if re.search('Small-body perts:', output):
                        continue
                    match = re.search(
                        'Target body name:\\s[a-zA-Z]+\\s\\((\\d+)\\)', output)
                    if match:
                        object_names.append(match.group(1))
                    else:
                        logger.error('Error. Could not parse id for single match major body (%s).' %
                                     lookups[repeat].upper().replace(suffix, ''))
                else:
                    # user search term is unique, so use it!
                    object_names.append(
                        lookups[repeat].upper().replace(suffix, ''))
            elif repeat == 1 and re.search('Matching small-bodies', output):
                logger.info('Multiple small bodies found in JPL Horizons for %s.' %
                            lookups[repeat].upper())
                # Matching small-bodies:
                #
                #    Record #  Epoch-yr  Primary Desig  >MATCH NAME<
                #    --------  --------  -------------  -------------------------
                #          4             (undefined)     Vesta
                #      34366             2000 RP36       Rosavestal
                match_count = 0
                for line in lines:
                    search_string = line.strip()
                    # look for small body list
                    match = re.search('^-?\\d+', search_string)
                    # parse out the small body parameters
                    if match:
                        match_count += 1
                        record_number = line[0:12].strip()
                        epoch_yr = line[12:22].strip()
                        primary_desig = line[22:37].strip()
                        match_name = line[37:len(line)].strip()
                        # print record_number, epoch_yr, primary_desig, match_name
                        # add semicolon for small body lookups
                        object_names.append(record_number + ';')
                # check our parse job
                match = re.search('(\\d+) matches\\.', output)
                if match:
                    if int(match.group(1)) != match_count:
                        logger.error('Multiple JPL small body parsing error!')
                    else:
                        logger.info(
                            'Multiple JPL small body parsing successful!')
            elif repeat == 0 and re.search('Multiple major-bodies', output):
                logger.info('Multiple major bodies found in JPL Horizons for %s.' %
                            lookups[repeat].upper())
                # Multiple major-bodies match string "50*"
                #
                #  ID#      Name                               Designation  IAU/aliases/other
                #  -------  ---------------------------------- -----------  -------------------
                #      501  Io                                              JI
                #      502  Europa                                          JII
                match_count = 0
                for line in lines:
                    search_string = line.strip()
                    # look for major body list
                    match = re.search('^-?\\d+', search_string)
                    # parse out the major body parameters
                    if match:
                        match_count += 1
                        record_number = line[0:9].strip()
                        # negative major bodies are spacecraft,etc. Skip those!
                        if int(record_number) >= 0:
                            name = line[9:45].strip()
                            designation = line[45:57].strip()
                            other = line[57:len(line)].strip()
                            # print record_number, name, designation, other
                            # NO semicolon for major body lookups
                            object_names.append(record_number)
                # check our parse job
                match = re.search('Number of matches =([\\s\\d]+).', output)
                if match:
                    if int(match.group(1)) != match_count:
                        logger.error('Multiple JPL major body parsing error!')
                    else:
                        logger.info(
                            'Multiple JPL major body parsing successful!')
        # get *nearest* sunset and *next* sunrise times
        # still not a big fan of this!
        observatory_location_obsplan = Observer(longitude=observatory.longitude*u.deg, latitude=observatory.latitude *
                                                u.deg, elevation=observatory.altitude*u.m, name=observatory.code, timezone=observatory.timezone)
        start = observatory_location_obsplan.twilight_evening_nautical(
            Time.now(), which="nearest")
        end = observatory_location_obsplan.twilight_morning_nautical(
            Time.now(), which="next")
        logger.debug('The nearest sunset is %s. The next sunrise is %s.' %
                     (start.iso, end.iso))
        logger.info('Found %d solar system match(es) for "%s".' %
                    (len(object_names), keyword))
        count = 0
        for object_name in object_names:
            count += 1
            # get ephemerides for target in JPL Horizons from start to end times
            result = ch.query(object_name.upper(), smallbody=True)
            result.set_epochrange(start.iso, end.iso, '15m')
            result.get_ephemerides(observatory.code)
            # return transit RA/DEC if available times exist
            logger.debug(result)
            if result and len(result['EL']):
                imax = np.argmax(result['EL'])
                ra = Angle(float(result['RA'][imax]) *
                           u.deg).to_string(unit=u.hour, sep=':')
                dec = Angle(float(result['DEC'][imax]) *
                            u.deg).to_string(unit=u.degree, sep=':')
                objects.append({'type': 'Solar System', 'id': object_name.upper(
                ), 'name': result['targetname'][0], 'ra': ra, 'dec': dec})
            else:
                logger.debug('The object ('+object_name+') is not observable.')
        return objects

#
# settings for a single set of astronomical images
#


class Stack():

    exposure = 10  # exposure time in seconds
    filter = 'clear'  # filter, e.g., clear, h-alpha, u-band, g-band, r-band, i-band, z-band
    binning = 1  # binning, e.g. 1 or 2
    count = 1  # number of images in this stack
    do_pinpoint = True  # refine pointing in between images

    # init
    def __init__(self, exposure, filter, binning, count, do_pinpoint=True):
        self.exposure = exposure
        self.filter = filter
        self.binning = binning
        self.count = count
        self.do_pinpoint = do_pinpoint

    def toString(self):
        return 'image stack: exposure=%f, filter=%s, binning=%d, count=%d, do_pinpoint=%s' % (self.exposure, self.filter, self.binning, self.count, self.do_pinpoint)


#
# sequence of astronomical image stacks
#
class Sequence():

    stacks = []  # list of image stacks
    repeat = None  # number of times to repeat this sequence
    do_pinpoint = True  # refine pointing in between stacks

    # repeat as much as possible
    CONTINUOUS = -1

    # init
    def __init__(self, stacks, repeat, do_pinpoint=True):
        self.stacks = stacks
        self.repeat = repeat
        self.do_pinpoint = do_pinpoint

    def addStack(self, stack):
        self.stacks.append(stack)

    def toString(self):
        sequence_string = 'sequence: repeat=%d, do_pinpoint=%s\n' % (
            self.repeat, self.do_pinpoint)
        for stack in self.stacks:
            sequence_string += '  %s\n' % stack.toString()
        return sequence_string

    # estimate the total duration in seconds of the observing sequence
    def getDuration(self):
        if self.repeat == -1:
            logger.warn('Sequence getDuration called on continuous sequence.')
            return -1
        sequenceTime = 0
        for stack in self.stacks:
            sequenceTime += stack.exposure
        sequenceTime *= self.repeat
        logger.debug('Sequence duration is %f seconds.' % sequenceTime)
        return sequenceTime


def get_lightcurve(telescope: 'Telescope') -> bool:
    """ Take a sequence of images for lightcurve studies

    MORE DETAIL HERE

    Parameters
    ----------
    telescope: Telescope
        A connected and locked telescope object

    Returns
    -------
    res: bool
        True if image sequence was successful, False if otherwise
    """

    #lazy logger hack
    global logger
    logger = telescope.log

    #for now, read in image target, sequence, etc. from json file
    cfg_path = '/'.join(['', 'home', config.telescope.username,
                        'lightcurve.json'])
    if not os.path.isfile(cfg_path):
        logger.error(
            'Lightcurve configuration file (%s) not found.' % cfg_path)
        return False

    # load target and comparison observations
    with open(cfg_path) as f:
        cfg = json.load(f)

    # user, hardcode for now
    user = cfg['user']

    # min obs altitude
    min_obs_alt = float(cfg['min_obs_alt'])

    # seo
    observatory = Observatory(cfg['observatory']['code'], cfg['observatory']['latitude'], cfg['observatory']
                            ['longitude'], cfg['observatory']['altitude'], cfg['observatory']['timezone'])

    # pause time while waiting for object to become available
    delay_time = cfg['delay_time']

    # build main asteroid observation
    observation_json = cfg['observations']
    target_json = observation_json['target']
    sequence_json = observation_json['sequences']['main']
    stacks_json = sequence_json['stacks']
    # build target
    target = Target.from_name(
        target_json['name'], observatory, target_json['type'])
    logger.debug(target.toString().replace('\n', '; '))
    # build image stacks
    stacks = []
    for stack_json in stacks_json:
        stack = Stack(float(stack_json['exposure']), stack_json['filters'], int(
            stack_json['binning']), int(stack_json['count']), stack_json['do_pinpoint'] if 'do_pinpoint' in stack_json else True)
        logger.debug(stack.toString().replace('\n', '; '))
        stacks.append(stack)
    # build sequence
    sequence = Sequence(stacks, int(sequence_json['repeat']), sequence_json['do_pinpoint'] if 'do_pinpoint' in sequence_json else True)
    logger.debug(sequence.toString().replace('\n', '; '))
    # build main observations
    asteroid_main_observation = Observation(
        observatory, target, sequence, min_obs_alt, user)
    # get min, max, and max alt obs times
    asteroid_main_observation.getTimes()
    logger.debug(asteroid_main_observation.toString().replace('\n', '; '))

    # build calibration asteroid/star observations
    sequence_json = observation_json['sequences']['calibration']
    stacks_json = sequence_json['stacks']
    # build image stacks
    stacks = []
    for stack_json in stacks_json:
        stack = Stack(float(stack_json['exposure']), stack_json['filters'], int(
            stack_json['binning']), int(stack_json['count']), stack_json['do_pinpoint'] if 'do_pinpoint' in stack_json else True)
        logger.debug(stack.toString().replace('\n', '; '))
        stacks.append(stack)
    # build sequence
    sequence = Sequence(stacks, int(sequence_json['repeat']), sequence_json['do_pinpoint'] if 'do_pinpoint' in sequence_json else True)
    logger.debug(sequence.toString().replace('\n', '; '))
    # build calibration observations
    asteroid_calibration_observation = Observation(
        observatory, target, sequence, min_obs_alt, user)
    asteroid_calibration_observation_duration_s = sequence.getDuration()
    logger.debug(asteroid_calibration_observation.toString().replace('\n', '; '))

