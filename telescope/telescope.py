import re
import time
import logging
import colorlog
import websocket as ws
import config.telescope as telescope
import routines.pinpoint as pinpoint
from config import config
from telescope.exception import *


class Telescope(object):
    def __init__(self):
        """ Create a new Telescope object by connectiong to the TelescopeServer
        and initializing the logging system. 
        """

        # initialize logging system
        self.__init_log()

        # connect to telescope server
        self.websocket: ws.WebSocket = self.connect()

    def connect(self) -> ws.WebSocket:
        try:
            # try and connect to telescope server
            connect_str = f'ws://localhost:{config.telescope.wsport}'
            websocket = ws.create_connection(connect_str)
            self.log.info('Successfully created connect to TelescopeServer')
        except Exception as e:
            self.log.critical(f'Error occurred in connecting to TelescopeServer: {e}')
            raise ConnectionException(f'Unable to connect to TelescopeServer: {e}')

        return websocket

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

    def disconnect(self) -> bool:
        """ Disconnect the Telescope from the TelescopeServer. 
        """
        self.websocket.close()

        return True

    def open_dome(self) -> bool:
        """ Checks that the weather is acceptable using `weather_ok`, 
        and if the dome is not already open. opens the dome. 

        Returns True if the dome was opened, False otherwise.
        """
        # check if dome is already open
        if self.dome_open:
            return True

        # check that weather is OK to open
        if self.weather_ok():
            result = self.run_command(telescope.open_dome)
            # TODO: Parse output to make sure that the dome is open
            # opened successfully - use telescope.open_dome_re
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

        # TODO: Parse output to make sure dome closed successfully
        return True

    def lock(self, user: str, comment: str = 'observing') -> bool:
        """ Lock the telescope with the given username. 
        """
        # TODO: Insert user and str into lock command
        result = self.run_command(telescope.lock)

        # TODO: Parse output to make sure telescope is
        # not already locked by someone else

        return True

    def unlock(self) -> bool:
        """ Unlock the telescope if you have the lock. 
        """
        result = self.run_command(telescope.unlock)

        # TODO: Parse output to make sure telescope is unlocked

        return True

    def locked(self) -> (bool, str):
        """ Check whether the telescope is locked. If it is, 
        return the username of the lock holder. 
        """
        result = self.run_command(telescope.check_lock)

        # TODO: Parse output to extract username and lock status

        return True, 'unknown'

    def keep_open(self, time: int) -> bool:
        """ Keep the telescope dome open for {time} seconds. 
        Returns True if it was successful. 
        """
        result = self.run_command(telescope.keep_open.format(time))

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
            self.log.warning(f'Unable to parse get_cloud: {result}')
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
            self.log.warning(f'Unable to parse get_dew: {result}')
            return 3.0  # return the safest value

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
            self.log.warning(f'Unable to parse get_rain: {result}')
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
            self.log.warning(f'Unable to parse get_sun_alt: {result}')
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
            self.log.warning(f'Unable to parse get_moon_alt: {result}')
            return 90.0

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

    def weather_ok(self) -> bool:
        """ Checks whether the sun has set, there is no rain (rain=0) and that
        it is less than 30% cloudy. Returns true if the weather is OK to open up,
        false otherwise.
        """
        # check sun has set
        if self.get_sun_alt() > config.telescope.max_sun_alt:
            if self.dome_open():
                self.close_dome()
            return False

        # check that it isn't raining
        if self.get_rain() != 0:
            if self.dome_open():
                self.close_dome()
            return False

        # check cloud cover is below 35%
        if self.get_cloud() >= config.telescope.max_cloud:
            if self.dome_open():
                self.close_dome()
            return False

        # weather is good!
        return True

    def goto_target(self, target: str) -> bool:
        """ Point the telescope at a target.
        
        Point the telescope at the target given
        by the catalog name {target} using the pinpoint
        algorithm to ensure pointing accuracy. Valid 
        target names include 'M1', 'm1', 'NGC6946', etc.
        """
        result = self.run_command(telescope.goto_target.format(target))

        # TODO: Run pinpoint algorithm

        # TODO: Parse results to make sure pointing is correct
        return True

    def goto_point(self, ra: str, dec: str) -> bool:
        """ Point the telescope at a given RA/Dec. 
        
        Point the telescope at the given RA/Dec using the pinpoint
        algorithm to ensure good pointing accuracy. Format
        for RA/Dec is hh:mm:ss, dd:mm:ss"""

        # Do basic pointing
        result = self.run_command(telescope.goto.format(ra, dec))

        # TODO: Parse output to check for failures

        # Run pinpoint algorithm - check status of pointing
        status = pinpoint.point(ra, dec, self)

        return status

    def target_visible(self, target: str) -> bool:
        """ Check whether a target is visible using
        the telescope controller commands. 
        """
        result = self.run_command(telescope.altaz_target.format(target))

        alt = re.search(telescope.alt_target_re, result)

        if alt and alt.group(0) >= config.telescope.min_alt:
            return True

        return False

    def point_visible(self, ra: str, dec: str) -> bool:
        """ Check whether a given RA/Dec pair is visible. 
        """
        pass

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

        # else we return -1
        return -1.0, -1.0

    def point_altaz(self, ra: str, dec: str) -> (float, float):
        pass

    def offset(self, dra: float, ddec: float) -> bool:
        """ Offset the pointing of the telescope by a given
        dRa and dDec
        """
        result = self.run_command(telescope.offset.format(dra, ddec))

        # TODO: Regex output to make sure offset was sucessful

        return True

    def enable_tracking(self) -> bool:
        """ Enable the tracking motor for the telescope.
        """
        result = self.run_command(telescope.enable_tracking)

        # TODO: Regex output to verify tracking

        return True

    def get_focus(self, focus: float) -> float:
        """ Return the current focus value of the
        telescope.
        """
        pass

    def set_focus(self, focus: float) -> bool:
        """ Set the focus value of the telescope to
        {focus}. 
        """
        pass

    def auto_focus(self) -> bool:
        """ Automatically focus the telescope
        using the focus routine. 
        """
        pass

    def current_filter(self) -> str:
        """ Return the string name of the current filter. 
        """
        result = self.run_command(telescope.current_filter)

        return result

    def change_filter(self, filtname: str) -> bool:
        """ Change the current filter specified by {filtname}.
        """
        result = self.run_command(telescope.change_filter.format(filtname))

        # get new filter
        current_filter = self.current_filter()

        # TODO: Verify current filter is requested filter

        return True

    def make_dir(self, dirname: str) -> bool:
        pass

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

    def wait_until_good(self) -> bool:
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
        weather: bool = self.weather_ok()
        while not weather:

            self.log.info('Waiting until weather is good...')

            # sleep for specified wait time
            self.wait(time_to_sleep)
            elapsed_time += time_to_sleep

            # shut down after max_time hours of continuous waiting
            if elapsed_time >= 60 * 60 * max_wait:
                self.log.warning(f'Bad weather for {max_wait} hours. Shutting down the queue...', color='magenta')
                raise WeatherException

            # update weather
            weather: bool = self.weather_ok()

        self.log('Weather is currently good.')
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

            self.log.info(f'Taking exposure {i+1}/{count} with name: {filename}')

            # take exposure
            # TODO: Send message to telescope - parse output

            # if the telescope has randomly closed, open up and repeat the exposure
            if not self.dome_open():
                self.log.warning('Slit closed during exposure - repeating previous exposure!')
                self.wait_until_good()
                self.open_dome()
                continue
            else:  # this was a successful exposure - take the next one
                i += 1

        return True

    def take_dark(self, filename: str, exposure_time: int, count: int = 1, binning: int = 2) -> bool:
        """ Take a full set of dark frames for a given session. Takes exposure_count
        dark frames.
        """
        for n in range(0, count):
            self.log.info(f'Taking dark {n+1}/{count} with name: {filename}')

            # TODO: Send command to telescope and take dark

        return True

    def take_bias(self, filename: str, count: int = 1, binning: int = 2) -> bool:
        """ Take the full set of biases for a given session.
        This takes exposure_count*numbias biases
        """

        # create file name for biases
        self.log.info('Taking {count} biases with names: {filename}')

        # take numbias*exposure_count biases
        for n in range(0, count):
            pass
            # TODO: Send command to telescope and parse output

        return True

    def run_command(self, command: str) -> str:
        """ Run a command on the telescope server. 
        
        This is done by sending message via websocket to
        the TelescopeServer, that then executes the command
        via SSH, and returns the string via WebSocket.
         
        Parameters
        ----------
        command: str
            The command to be run
        
        """

        # send message on websocket
        self.websocket.send(command)

        # receive result of command
        result = self.websocket.recv()

        # TODO: Check that command was not denied
        # TODO: by TelescopeServer

        # print result
        self.log.info(result)

        # return it for processing by other methods
        return result

    def __init_log(self) -> bool:
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
        self.log = logging.getLogger('telescope')
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(stream)

        return True
