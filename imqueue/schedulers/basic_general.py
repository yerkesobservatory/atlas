import sys
import numpy as np
import astropy.units as u
from astropy.time import Time
from astroplan import Observer
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun
import matplotlib.pyplot as plt
import datetime

#
#an astronomical observation
#
class Observation():

    sequence = None #image sequence
    target = None #target
    observatory = None #observatory

    #init
    def __init__(self, observatory, target, sequence):
        self.observatory = observatory
        self.target = target
        self.sequence = sequence

    def toString(self):
        return '%s\n%s\n%s'%(self.observatory.toString(), self.target.toString(), self.sequence.toString())

#
#the astronomical target
#
class Target():

    #init
    def __init__(self, name, ra, dec):
        self.name = name
        self.ra = ra #hour:min:sec
        self.dec = dec #deg:min:sec

    #name
    def getName(self):
        return self.name

    def setName(self, name):
        self.name = name

    #ra = right ascension
    #eventually expand to allow current coord lookup based on name?
    def getRa(self):
        return self.ra

    def setRa(self, ra):
        self.ra = ra

    #dec = declination
    #eventually expand to allow current coord lookup based on name?
    def getDec(self):
        return self.dec

    def setDec(self, dec):
        self.dec = dec

    def toString(self):
        return 'target: name=%s, ra=%s, dec=%s'%(self.name, self.ra, self.dec)

#
#settings for a single set of astronomical images
#
class Stack():

    exposure = 10 #exposure time in seconds
    filter = 'clear' #filter, e.g., clear, h-alpha, u-band, g-band, r-band, i-band, z-band
    binning = 1 #binning, e.g. 1 or 2
    count = 1 #number of images in this stack

    #init
    def __init__(self, exposure, filter, binning, count):
        self.exposure = exposure
        self.filter = filter
        self.binning = binning
        self.count = count

    def toString(self):
        return 'image stack: exposure=%d, filter=%s, binning=%d, count=%d'%(self.exposure, self.filter, self.binning, self.count)

#
#sequence of astronomical image stacks
#
class Sequence():

    stacks = [] #list of image stacks
    repeat = 1 #number of times to repeat this sequence

    #init
    def __init__(self, stacks, repeat):
        self.stacks = stacks
        self.repeat = repeat

    def addStack(self, stack):
        self.stacks.append(stack)

    def toString(self):
        sequence_string = 'sequence: repeat=%d\n'%(self.repeat)
        for stack in self.stacks:
            sequence_string += '  %s\n'%stack.toString()
        return sequence_string

class Observatory():

    code = None
    latitude = 0.0 #in decimal degrees
    longitude = 0.0 #in decimal degrees
    altitude = 0.0 #in meters
    timzeone = None

    #init
    def __init__(self, code, latitude, longitude, altitude, timezone):
        self.code = code
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.timezone = timezone

    def toString(self):
        observatory_string = 'observatory: code=%s, lat=%f, lon=%f, alt=%f'%(self.code, self.latitude, self.longitude, self.altitude)
        return observatory_string

#based on Amanda Pagul's schedule function for the SEO queue
# This function receives a list of target coordinates and outputs a primary
# observable target
# Inputs:
# -------
# target_list :str: :list: List containing the names of the targets (i.e. [(id, ra, dec), (id, ra, dec), ...]).
# endtime: :list: 'obj' datetime (i.e. datetime(year, month, day, hour, minute, second))
# Outputs:
# --------
# primary_target :str: (id, ra, dec) of the highest priority target
# wait :astropy.Time: Wait time in seconds until optimal observation.
# It takes the value -1 when the object(s) is not observable.
class Scheduler():

    observatory = None #an Observatory
    observations = None #list of Observations

    max_sun_alt = -12 #what defines dark? (deg)
    min_target_alt = 30 #how low can you go? (deg)

    def __init__(self, observatory, observations):
        self.observatory = observatory
        self.observations = observations

    def whatsNext(self):
        max_altitude_time = {'target':[], 'altitude':[], 'time':[], 'wait':[]}

        observatory_location = EarthLocation(lat=self.observatory.latitude*u.deg, lon=self.observatory.longitude*u.deg, height=self.observatory.altitude*u.m)

        #build alt-az coordinate frame for observatory over next 15 hours
        obs_time = Time.now()
        delta_obs_time = np.linspace(0, 15, 1000)*u.hour
        #the next 15 hours
        times = obs_time+delta_obs_time
        #build frame
        frame = AltAz(obstime=times, location=observatory_location)
        #print frame

        #get *nearest* sunset and *next* sunrise times
        #still not a big fan of this!
        observatory_location_obsplan = Observer(longitude=self.observatory.longitude*u.deg, latitude=self.observatory.latitude*u.deg, elevation=self.observatory.altitude*u.m, name=self.observatory.code, timezone=self.observatory.timezone)
        sundown_time = observatory_location_obsplan.sun_set_time(Time.now(), which="nearest")
        sunup_time = observatory_location_obsplan.sun_rise_time(Time.now(), which="next")
        #print 'sundown=%s'%sundown_time.iso
        #print 'sunup=%s'%sunup_time.iso

        # list solar system objects
        solar_system = ['mercury','venus','moon','mars','jupiter','saturn','uranus','neptune','pluto']
        too_bright = False

        #loop thru observations, suggest the next best target
        for i,observation in enumerate(self.observations):

            # the observation is missing RA/Dec
            if not observation.get('RA') or not observation.get('Dec'):

            # if the target name is a RA/Dec string
            if re.search(r'\d{1,2}:\d{2}:\d{1,2}.\d{1,2}\s[+-]\d{1,2}:\d{2}:\d{1,2}.\d{1,2}', observation.get('target')):
                ra, dec = observation.get('target').strip().split(' ')
                observation['RA'] = ra; observation['Dec'] = dec;
            else: # try and lookup by name
                if observation.get('target').lower() in solar_system:
                    too_bright = True
                    ra, dec = lookup.lookup(observation.get('target'))

                    if not ra or not dec:
                        print(f'Unable to compute RA/Dec for {observation.get("target")}.')
                        if database.Database.is_connected:
                            database.Database.observations.update_one({'_id': observation['_id']},
                                                                      {'$set':
                                                                       {'error': 'lookup'}})
                        continue

                    # save the RA/Dec
                    observation['RA'] = ra; observation['Dec'] = dec;
                    if database.Database.is_connected:
                        database.Database.observations.update_one({'_id': observation['_id']},
                                                                  {'$set':
                                                                   {'RA': ra,
                                                                    'Dec': dec}})

            # check whether observation has RA and Dec values
            if observation.get('RA') is None:
                continue
            if observation.get('Dec') is None:
                continue

            # target coordinates

            input_coordinates = ra+" "+dec

            max_altitude_time['target'].append(observation.target.getName())

            try:
                target_coordinates = SkyCoord(input_coordinates, unit=(u.hourangle, u.deg))
            except:
                continue

            target_altaz = target_coordinates.transform_to(frame)

            if (np.max(target_altaz.alt)) > self.min_target_alt*u.degree:
                max_altitude_time['altitude'].append(np.max(target_altaz.alt))
            else:
                max_altitude_time['altitude'].append(0*u.degree)

            aux_time = times[np.argmax(target_altaz.alt)]
            max_altitude_time['time'].append(aux_time)

            aux_delta_time = delta_obs_time[np.argmax(target_altaz.alt)]

            #print max_altitude_time['altitude'][i], times[np.argmax(target_altaz.alt)], sundown_time, sunup_time
            if (max_altitude_time['altitude'][i]>0*u.degree) & (times[np.argmax(target_altaz.alt)] > sundown_time) & (times[np.argmax(target_altaz.alt)] < sunup_time):
                max_altitude_time['wait'].append(aux_delta_time.to(u.second))
            else:
                max_altitude_time['wait'].append(-1*u.s)

        #print max_altitude_time['time']
        #print max_altitude_time['target']
        #print max_altitude_time['wait']

        max_altitude_time['time']=np.array(max_altitude_time['time'])
        good_object = np.array([max_altitude_time['wait'][itgt]>-1*u.s for itgt in range(len(max_altitude_time['wait']))])

        if np.count_nonzero(good_object)>0:
            if np.count_nonzero(good_object)>1:
                aux_id = np.argmin(Time(max_altitude_time['time'][good_object])-Time.now())
                primary_target_id = np.where(good_object)[0][aux_id]
                #print max_altitude_time['target'][primary_target_id]
                primary_target = np.array(max_altitude_time['target'])[primary_target_id]
                #print primary_target_id
            else:
                primary_target_id = np.where(good_object)[0][0]
                primary_target = np.array(max_altitude_time['target'])[primary_target_id]
        else:
            return None

        return self.observations[primary_target_id]
