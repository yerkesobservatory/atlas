import os
import re
import json
import time
import logging
import colorlog
import paramiko
import random
import datetime
import websocket as ws
import config.telescope as telescope
import paho.mqtt.client as mqtt
from routines import pinpoint, focus, flats, lookup
from config import config
from telescope.exception import *


class SSHTelescope(object):
    """ This class allows for a telescope to be remotely controlled
    via SSH using high-level python functions.

    All methods of this class can be used to control and alter the
    state of the telescope. Requires that the user have a SSH key
    on the control server.
    """

    # logger for class
    log = None

    def __init__(self):
        """ Create a new SSHTelescope object by connecting to the telescope server
        via SSH and initializing the logging system.
        """

        # initialize logging system if not already done
        if not SSHTelescope.log:
            SSHTelescope.__init_log()

        # SSH connection to telescope server
        self.ssh: paramiko.SSHClient = None

        # connect to telescope
        self.connect()

        # check whether MQTT publication is enabled
        if config.mqtt.enabled:

            # create MQTT client
            self.client = mqtt.Client()

            # MQTT topic
            topic = '/'.join(['', config.mqtt.root, 'telescope'])

            # broker info
            host = config.mqtt.host or 'localhost'
            port = config.mqtt.port or 1883

            # connect to message broker
            try:
                self.client.connect(host, port, 60)
                self.log.info(f'Successfully connected to MQTT broker')

                # create publish function
                self.publish = lambda msg: client.publish(topic, json.dumps(msg))
            except Exception as e:
                self.log.warning(f'Unable to connect to MQTT broker: {e}')
                self.publish = lambda msg: True

    def connect(self) -> bool:
        """ Create a SSH connection to the telescope control server.

        Will raise ConnectionException if there is any error in connection to the telescope.
        """
        self.ssh: paramiko.SSHClient = self.__connect()

        return True

    @staticmethod
    def __connect() -> paramiko.SSHClient:
        """ Create a SSH connection to the telescope control server.

        Will raise ConnectionException if there is any error in connection to the telescope.
        """
        ssh: paramiko.SSHClient = paramiko.SSHClient()

        # load host keys for verified connection
        ssh.load_system_host_keys()

        # insert keys - this needs to be removed ASAP - should manually add server key
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # connect!
        try:
            ssh.connect(config.telescope.host, username=config.telescope.username)
            SSHTelescope.log.info('Successfully connected to the telescope control server')
        except paramiko.AuthenticationException:  # unable to authenticate
            SSHTelescope.log.critical('Unable to authenticate connection to telescope control server. Please check that your SSH key has been setup correctly.')
            raise ConnectionException
        except Exception as e:
            SSHTelescope.log.critical(f'SSHTelescope has encountered an unknown error in '
                                      f'connecting to the control server. \n Error: "{e}"')
            raise ConnectionException

        return ssh

    def disconnect(self) -> bool:
        """ Disconnect the Telescope from the TelescopeServer.
        """
        self.ssh.close()
        self.ssh = None

        return True

    def is_alive(self) -> bool:
        """ Check whether connection to telescope server is alive/working, and whether
        we still have permission to execute commands.
        """
        try:
            self.run_command('echo its alive')
            return True
        except Exception as e:
            self.log.warning(f'{e}')
            return False

    def open_dome(self) -> bool:
        """ Checks that the weather is acceptable using `weather_ok`,
        and if the dome is not already open. opens the dome.

        Returns True if the dome was opened, False otherwise.
        """
        # check if dome is already open
        if self.dome_open():
            return True

        # check that weather is OK to open
        if self.weather_ok():
            result = self.run_command(telescope.open_dome)

            if re.search(telescope.open_dome_re, result):
                self.publish({'EVENT': 'OPENUP',
                              'TIME': datetime.datetime.now().isoformat()})
                return True

        # in any other scenario, return False
        return False

    def dome_open(self) -> bool:
        """ Checks whether the telescope slit is open or closed.

        Returns True if open, False if closed.
        """
        result = self.run_command(telescope.dome_open)
        slit = re.search(telescope.dome_open_re, result)

        # if open, return True
        if slit and slit.group(0) == 'open':
            return True

        # in any other scenario, return False
        return False

    def close_dome(self) -> bool:
        """ Closes the dome, but leaves the session connected. Returns
        True if successful in closing down, False otherwise.
        """
        result = self.run_command(telescope.close_dome)

        if re.search(telescope.close_dome_re, result):
            self.publish({'EVENT': 'CLOSEDOWN',
                          'TIME': datetime.datetime.now().isoformat()})
            return True
        else:
            return False

    def close_down(self) -> bool:
        """ Closes the dome and unlocks the telescope. Call
        this at end of every control session.
        """
        closed = self.close_dome()
        unlocked = self.unlock()
        return closed and unlocked

    def lamps_on(self) -> bool:
        """ Turn on any dome lamps.
        """
        # TODO
        return True

    def lamps_off(self) -> bool:
        """ Turn on any dome lamps.
        """
        # TODO
        return True

    def chip_temp(self, chip: str) -> bool:
        """ Return temperature (in C) of the chip with identifier
        'chip'
        """
        # TODO
        return True

    #mcn
    def chip_temp_ok(self) -> bool:
        """ Compare current chip temperature to the set temperature.
        If the same, return True; else, return False
        """
        result = self.run_command(telescope.get_ccd_status)
    
        # search for chip and setpoint temperatures
        tchip = re.search(telescope.tchip_ccd_re, result)
        setpoint = re.search(telescope.setpoint_ccd_re, result)

        # extract group and return
        if tchip and setpoint:  
          return float(tchip.group(0))-float(setpoint.group(0)) < 1 #within 1 degree is good enough
        #else:
        #    self.log.warning(f'Unable to parse get_ccd_status: \"{result}\"')
        #    return False  # return the safest value        

        return False

    #mcn
    def cool_ccd(self) -> bool:
        """ Cool the CCD
        """
        result = self.run_command(telescope.cool_ccd)        

        return True

    def lock(self, user: str, comment: str = 'observing') -> bool:
        """ Lock the telescope with the given username.
        """
        # try and substitute the user and comment values
        try:
            command = telescope.lock.format(user=user, comment=comment)
        except Exception as e:
            command = telescope.lock

        result = self.run_command(telescope.lock.format(user=user, comment=comment))

        # check that we were successful
        if re.search(telescope.lock_re, result):
            self.publish({'EVENT': 'LOCK',
                          'TIME': datetime.datetime.now().isoformat()})
            return True
        return False

    def unlock(self) -> bool:
        """ Unlock the telescope if you have the lock.
        """
        result = self.run_command(telescope.unlock)

        if re.search(telescope.unlock_re, result):
            self.publish({'EVENT': 'UNLOCK',
                          'TIME': datetime.datetime.now().isoformat()})
            return True
        return False

    def locked(self) -> (bool, str):
        """ Check whether the telescope is locked. If it is,
        return the username of the lock holder.
        """
        result = self.run_command(telescope.check_lock)

        if result == 'done lock':
            return False, ''

        if re.search(telescope.check_lock_re, result):
            return True, 'unknown'

        return False, ''

    def keep_open(self, time: int) -> bool:
        """ Keep the telescope dome open for {time} seconds.
        Returns True if it was successful.
        """
        if self.dome_open() is False:
            self.log.warn('Slit must be opened before calling keep_open()')
            return False

        result = self.run_command(telescope.keep_open.format(time=time))

        # TODO: Parse output to extract username and lock status
        return True

    def get_cloud(self) -> float:
        """ Get the current cloud coverage.
        """
        # run the command
        result = self.run_command(telescope.get_cloud)

        # run regex
        cloud = re.search(telescope.get_cloud_re, result)

        # extract group and return
        if cloud:
            return float(cloud.group(0))
        else:
            self.log.warning(f'Unable to parse get_cloud: \"{result}\"')
            return 1.0  # return the safest value

    def get_dew(self) -> float:
        """ Get the current dew value.
        """
        # run the command
        result = self.run_command(telescope.get_dew)

        # run regex
        dew = re.search(telescope.get_dew_re, result)

        # extract group and return
        if dew:
            return float(dew.group(0))
        else:
            self.log.warning(f'Unable to parse get_dew: \"{result}\"')
            return 10.0  # return the safest value

    def get_rain(self) -> float:
        """ Get the current rain value.
        """
        # run the command
        result = self.run_command(telescope.get_rain)

        # run regex
        rain = re.search(telescope.get_rain_re, result)

        # extract group and return
        if rain:
            return float(rain.group(0))
        else:
            self.log.warning(f'Unable to parse get_rain: \"{result}\"')
            return 1.0  # return the safest value

    def get_sun_alt(self) -> float:
        """ Get the current altitude of the sun.
        """
        # run the command
        result = self.run_command(telescope.get_sun_alt)

        # run regex
        alt = re.search(telescope.get_sun_alt_re, result)

        # extract group and return
        if alt:
            return float(alt.group(0))
        else:
            self.log.warning(f'Unable to parse get_sun_alt: \"{result}\"')
            return 90.0  # return the safest altitude we can

    def get_moon_alt(self) -> float:
        """ Get the current altitude of the moon.
        """
        # run the command
        result = self.run_command(telescope.get_moon_alt)

        # run regex
        alt = re.search(telescope.get_moon_alt_re, result)

        # extract group and return
        if alt:
            return float(alt.group(0))
        else:
            self.log.warning(f'Unable to parse get_moon_alt: \"{result}\"')
            return 90.0

    # TODO - make one 'tx taux' call instead of 5
    def get_weather(self) -> dict:
        """ Extract all the values for the current weather
        and return it as a python dictionary.
        """
        weather = {'rain': self.get_rain(),
                   'cloud': self.get_cloud(),
                   'dew': self.get_dew(),
                   'sun': self.get_sun_alt(),
                   'moon': self.get_moon_alt()}
        return weather

    def weather_ok(self, sun: float = None) -> bool:
        """ Checks whether the sun has set, there is no rain (rain=0) and that
        it is less than 30% cloudy. Returns true if the weather is OK to open up,
        false otherwise.
        """
        # get the current weather
        weather = self.get_weather()
        self.publish({'EVENT': 'WEATHER',
                      'SUN': weather.get('sun'),
                      'MOON': weather.get('moon'),
                      'CLOUD': weather.get('cloud'),
                      'RAIN': weather.get('rain'),
                      'DEW': weather.get('dew'),
                      'TIME': datetime.datetime.now().isoformat()})

        # check sun is at proper altitude
        desired_sun_alt = sun or config.telescope.max_sun_alt
        if weather.get('sun') > desired_sun_alt:
            if self.dome_open():
                self.close_dome()
            return False

        # check that it isn't raining
        if weather.get('rain') != 0:
            if self.dome_open():
                self.close_dome()
            return False

        # check cloud cover is below 35%
        if weather.get('cloud') >= config.telescope.max_cloud:
            if self.dome_open():
                self.close_dome()
            return False

        # weather is good!
        return True

    def goto_target(self, target: str) -> (bool, float, float):
        """ Point the telescope at a target.

        Point the telescope at the target given
        by the catalog name {target} using the pinpoint
        algorithm to ensure pointing accuracy. Valid
        target names include 'M1', 'm1', 'NGC6946', etc.

        Parameters
        ----------
        target: str
            The name of the target that you want to observe

        Returns
        -------
        success: bool
            Whether pinpointing was a success
        dra: float
            The final offset error in right-ascension
        ddec: float
            The final offset error in declination
        """

        # check that the object is visible
        if lookup.target_visible(target) and self.target_visible(target):

            # do a rough pointing of the telescope
            if self.run_command(telescope.goto_target.format(target=target)):

                # convert name to ra/dec
                ra, dec = lookup.lookup(target)

                if pinpoint.pinpoint(ra, dec, self):
                    self.publish({'EVENT': 'SLEW',
                                  'LOCATION': ra+' '+dec,
                                  'TIME': datetime.datetime.now().isoformat()})
                    return True

        return False

    def goto_point_for_flats(self) -> bool:
        """ Point the telescope east of zenith with a bit of wiggle.
        """

        #point scope east of zenith
        ha = config.telescope.ha_east #eastward
        dec = config.general.latitude #zenith

        #randomize
        dHa = 0.5*random.random()
        dDec = 0.5*random.random()
        ha += dHa
        dec += dDec

        self.run_command(telescope.goto_for_flats.format(ha=ra, dec=dec))


    def goto_point(self, ra: str, dec: str) -> (bool, float, float):
        """ Point the telescope at a given RA/Dec.

        Point the telescope at the given RA/Dec using the pinpoint
        algorithm to ensure good pointing accuracy. Format
        for RA/Dec is hh:mm:ss, dd:mm:ss

        Parameters
        ----------
        ra: float
            The right-ascension of the desired target
        dec: float
            The declination of the desired target

        Returns
        -------
        success: bool
            Whether pinpointing was a success
        dra: float
            The final offset error in right-ascension
        ddec: float
            The final offset error in declination
        """

        # check that the target is visible
        if lookup.point_visible(ra, dec) and self.point_visible(ra, dec):

            # Do basic pointing
            if self.run_command(telescope.goto.format(ra=ra, dec=dec)):

                # Run pinpoint algorithm - check status of pointing
                if pinpoint.point(ra, dec, self):
                    self.publish({'EVENT': 'SLEW',
                                  'LOCATION': ra+' '+dec,
                                  'TIME': datetime.datetime.now().isoformat()})
                    return True

        return False, -1, -1

    def target_visible(self, target: str) -> bool:
        """ Check whether a target is visible using
        the telescope controller commands.
        """

        result = self.run_command(telescope.altaz_target.format(target=target))

        alt = re.search(telescope.alt_target_re, result)

        if alt and (float(alt.group(0)) >= config.telescope.min_alt):
            return True

        return False

    def point_visible(self, ra: str, dec: str) -> bool:
        """ Check whether a given RA/Dec pair is visible.
        """
        result = self.run_command(telescope.altaz.format(ra=ra, dec=dec))

        alt = re.search(telescope.alt_re, result)

        if alt and (float(alt.group(0)) >= config.telescope.min_alt):
            return True

        return False

    def target_altaz(self, target: str) -> (float, float):
        """ Return a (alt, az) pair containing floats indicating
        the altitude and azimuth of a target - i.e 'M31', 'NGC4779'
        """
        # run the command
        result = self.run_command(telescope.altaz_target.format(target))

        # search for altitude and azimuth
        alt = re.search(telescope.alt_target_re, result)
        az = re.search(telescope.az_target_re, result)

        # check the search was successful and return
        if alt and alt.group(0):
            if az and az.group(0):
                return alt, az

        # else we return 0
        return 0, 0

    def point_altaz(self, ra: str, dec: str) -> (float, float):
        """ Return a (alt, az) pair containing floats indicating
        the altitude and azimuth of a given RA/Dec'
        """
        # run the command
        result = self.run_command(telescope.altaz.format(target=target))

        # search for altitude and azimuth
        alt = re.search(telescope.alt_re, result)
        az = re.search(telescope.az_re, result)

        # check the search was successful and return
        if alt and alt.group(0):
            if az and az.group(0):
                return alt, az

        # else we return 0
        return 0, 0

    def offset(self, dra: float, ddec: float) -> bool:
        """ Offset the pointing of the telescope by a given
        dRa and dDec
        """
        result = self.run_command(telescope.offset.format(ra=dra, dec=ddec))

        return (re.search(telescope.offset_re, result) and True) or False

    def enable_tracking(self) -> bool:
        """ Enable the tracking motor for the telescope.
        """
        result = self.run_command(telescope.enable_tracking)

        return (re.search(telescope.enable_tracking_re, result) and True) or False

    def disable_tracking(self) -> bool:
        """ Disable the tracking motor for the telescope.
        """
        result = self.run_command(telescope.disable_tracking)

        return (re.search(telescope.disable_tracking_re, result) and True) or False

    def move_dome(self, daz: float) -> bool:
        """ Move the dome to az=daz
        """
        result = self.run_command(telescope.move_dome.format(az=daz))

        return (re.search(telescope.move_dome_re, result) and True) or False

    def home_dome(self) -> bool:
        """ Calibrate the dome motor
        """        
        result = self.run_command(telescope.home_dome)

        return (re.search(telescope.home_dome_re, result) and True) or False        

    def home_ha(self) -> bool:
        """ Calibrate the HA motor
        """  
        result = self.run_command(telescope.home_ha)

        return (re.search(telescope.home_ha_re, result) and True) or False   

    def home_dec(self) -> bool:
        """ Calibrate the DEC motor
        """          
        result = self.run_command(telescope.home_dec)

        return (re.search(telescope.home_dec_re, result) and True) or False   

    def calibrate_motors(self) -> bool:
        """ Run the motor calibration routine.
        """
        if not self.home_dome():
            return False

        if not self.home_ha():
            return False

        if not self.home_dec():
            return False                        

        return True

    # TODO
    def get_focus(self) -> float:
        """ Return the current focus value of the
        telescope.
        """
        result = self.run_command(telescope.get_focus)

        # TODO: Parse output to extract focus value

        return 0

    def set_focus(self, focus: float) -> bool:
        """ Set the focus value of the telescope to
        `focus`.
        """
        result = self.run_command(telescope.set_focus.format(focus=focus))

        return (re.search(telescope.set_focus_re, result) and True) or False

    def auto_focus(self) -> (bool, int):
        """ Automatically focus the telescope
        using the focus routine.
        """
        return focus.focus(self)

    def current_filter(self) -> str:
        """ Return the string name of the current filter.
        """
        result = self.run_command(telescope.current_filter)

        return result

    def change_filter(self, name: str) -> bool:
        """ Change the current filter specified by {filtname}.
        """
        result = self.run_command(telescope.change_filter.format(name=name))

        # get new filter
        current_filter = self.current_filter()

        if (current_filter == name):
            self.publish({'EVENT': 'FILTER',
                          'FILTER': current_filter,
                          'TIME': datetime.datetime.now().isoformat()})
        return False

    def make_dir(self, dirname: str) -> bool:
        """ Make a directory on the telescope control server.
        """
        return self.run_command('mkdir -p {dirname}'.format(dirname=dirname))

    def take_flats(self) -> bool:
        """ Wait until the weather is good for flats, and then take a series of
        flats before returning.
        """
        return flats.take_flats(self)

    def wait(self, wait: int) -> None:
        """ Sleep the telescope for 'wait' seconds.

        If the time is over telescope.wait_time, shutdown the telescope
        while we wait, and then reopen before returning.
        """

        # return immediately if we don't need to wait
        if wait <= 0:
            return

        self.log.info(f'Sleeping for {wait} seconds...')
        # if the wait time is long enough, close down the telescope in the meantime
        if wait >= 60 * config.telescope.wait_time:

            # if the dome is open, close it
            if self.dome_open():
                self.log.info('Closing down the telescope while we sleep...')
                self.close_down()

            # sleep
            time.sleep(wait)

            # reconnect to telescope and open up
            self.open_dome()

        # we aren't going to sleep while we wait
        else:
            time.sleep(wait)

        return

    def wait_until_good(self, sun: float = None) -> bool:
        """ Wait until the weather is good for observing.

        Waits config.wait_time minutes between each trial. Cancels execution
        if weather is bad for max_wait_time hours.
        """

        # maximum time to wait for good weather - in hours
        max_wait: int = config.telescope.max_wait_time

        # time to sleep between trying the weather - in minutes
        time_to_sleep: int = 60 * config.telescope.wait_time

        # total time counter
        elapsed_time: int = 0  # total elapsed wait time

        # get weather from telescope
        weather: bool = self.weather_ok(sun)
        while not weather:

            self.log.info('Waiting until weather is good...')

            # sleep for specified wait time
            self.wait(time_to_sleep) # TODO: Should this be changed to avoid repeatedly opening the dome?
            elapsed_time += time_to_sleep

            # shut down after max_time hours of continuous waiting
            if elapsed_time >= 60 * 60 * max_wait:
                self.log.warning(f'Bad weather for {max_wait} hours. Shutting down the queue...', color='magenta')
                raise WeatherException

            # update weather
            weather: bool = self.weather_ok(sun)

        self.log.info('Weather is currently good.')
        return True

    def take_exposure(self, filename: str, exposure_time: int,
                      count: int = 1, binning: int = 2, filt: str = 'clear') -> bool:
        """ Take count exposures, each of length exp_time, with binning, using the filter
        filt, and save it in the file built from basename.
        """
        # change to that filter
        self.log.info(f'Switching to {filt} filter')
        self.change_filter(filt)

        # take exposure_count exposures
        i: int = 0
        while i < count:

            # create filename
            if count == 1: #don't add count if just one exposure
                fname = filename + f'.fits'
            else:
               fname = filename + f'_{i}.fits'                

            self.log.info(f'Taking exposure {i+1}/{count} with name: {fname}')

            # take exposure
            self.run_command(telescope.take_exposure.format(time=exposure_time, binning=binning,
                                                            filename=fname))

            # if the telescope has randomly closed, open up and repeat the exposure
            if not self.dome_open():
                self.log.warning('Slit closed during exposure - repeating previous exposure!')
                self.wait_until_good()
                self.open_dome()
                continue
            else:  # this was a successful exposure - take the next one
                i += 1 # increment counter
                # notify (or not) the MQTT broker
                self.publish({'EVENT': 'EXPOSURE',
                              'TYPE': 'SCIENCE',
                              'TIME': exposure_time,
                              'FILTER': filt,
                              'BINNING': binning,
                              'REMOTE': config.telescope.host,
                              'PATH': fname,
                              'TIME': datetime.datetime.now().isoformat()})

        return True

    def take_dark(self, filename: str, exposure_time: int, count: int = 1, binning: int = 2) -> bool:
        """ Take a full set of dark frames for a given session. Takes exposure_count
        dark frames.
        """
        for n in range(0, count):

            # create filename
            fname = filename + f'_dark_{n}.fits'

            self.log.info(f'Taking dark {n+1}/{count} with name: {fname}')

            self.run_command(telescope.take_dark.format(time=exposure_time, binning=binning,
                                                        filename=fname))
            # publish to MQTT
            self.publish({'EVENT': 'EXPOSURE',
                          'TYPE': 'DARK',
                          'TIME': exposure_time,
                          'BINNING': binning,
                          'REMOTE': config.telescope.host,
                          'PATH': fname,
                          'TIME': datetime.datetime.now().isoformat()})

        return True

    def take_bias(self, filename: str, count: int = 1, binning: int = 2) -> bool:
        """ Take the full set of biases for a given session.
        This takes exposure_count*numbias biases
        """

        # create file name for biases
        self.log.info(f'Taking {count} biases with name: {filename}_N.fits')

        # take biases
        for n in range(0, count):

            # create filename
            fname = filename + f'_bias_{n}.fits'

            self.run_command(telescope.take_dark.format(time=0.1, binning=binning,
                                                        filename=fname))
            # publish to MQTT (or not)
            self.publish({'EVENT': 'EXPOSURE',
                          'TYPE': 'BIAS',
                          'TIME': 0.1,
                          'BINNING': binning,
                          'REMOTE': config.telescope.host,
                          'PATH': fname,
                          'TIME': datetime.datetime.now().isoformat()})

        return True

    def copy_remote_to_local(self, remotepath: str, localpath: str = '') -> bool:
        """ Copy a file at `remotepath` on the telescope control server to `localpath`
        on localhost.
        """
        # create sftp context
        sftp = paramiko.SFTPClient.from_transport(self.ssh.get_transport())

        try:
            # get file from remote and then close connection
            sftp.get(remotepath, localpath)
            sftp.close
            self.log.info('File successfully copied.')
            return True
        except Exception as e:
            self.log.info(f'Error occured while copying file: {e}')
            return False

    def copy_local_to_remote(self, localpath: str, remotepath: str = '') -> bool:
        """ Copy a file at `localpath` on localhost to `remotepath`
        on the telescope control server.
        """
        # create sftp context
        sftp = paramiko.SFTPClient.from_transport(self.ssh.get_transport())

        try:
            # get file from remote and then close connection
            sftp.put(localpath, remotepath)
            sftp.close
            self.log.info('File successfully copied.')
            return True
        except Exception as e:
            self.log.info(f'Error occured while copying file: {e}')
            return False

    def run_command(self, command: str) -> str:
        """ Run a command on the telescope server.

        This remotely executes the string command in a shell on
        the telescope server via SSH.

        Parameters
        ----------
        command: str
            The command to be run

        """
        if self.ssh == None:
            self.log.warn('SSH is not connected. Please reconnect to the telescope server.')
            return None

        self.log.info(f'Executing: {command}')

        # make sure the connection hasn't timed out due to sleep
        # if it has, reconnect
        try:
            self.ssh.exec_command('echo its alive')
        except Exception as e:
            self.ssh = self.connect()

        # try and execute command 5 times if it fails
        numtries = 0; exit_code = 1
        while numtries < 5 and exit_code != 0:
            try:
                stdin, stdout, stderr = self.ssh.exec_command(command)
                numtries += 1
                result = stdout.readlines()

                # check exit code
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    if command[0:8] == 'keepopen':
                        return None
                    self.log.warn(f'Command returned {exit_code}. Retrying in 3 seconds...')
                    time.sleep(3)
                    continue

                if result:
                    # valid result received
                    if len(result) > 0:
                        result = ' '.join(result).strip()
                        self.log.info(f'Result: {result}')
                        return result

            except Exception as e:
                self.log.critical(f'run_command: {e}')
                self.log.critical(f'Failed while executing {command}')
                self.log.critical('Please manually close the dome by running'
                                  ' `closedown` and `logout`.')

                raise UnknownErrorException

        return None

    @classmethod
    def __init_log(cls) -> bool:
        """ Initialize the logging system for this module and set
        a ColoredFormatter.
        """
        # create format string for this module
        format_str = config.logging.fmt.replace('[name]', 'TELESCOPE')
        formatter = colorlog.ColoredFormatter(format_str, datefmt=config.logging.datefmt)

        # create stream
        stream = logging.StreamHandler()
        stream.setLevel(logging.DEBUG)
        stream.setFormatter(formatter)

        # assign log method and set handler
        cls.log = logging.getLogger('telescope')
        cls.log.setLevel(logging.DEBUG)
        cls.log.addHandler(stream)

        return True

    
