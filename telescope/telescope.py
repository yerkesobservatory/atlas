import re
import time
import logging
import colorlog
import websocket as ws
import config.telescope as telescope
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
            return websocket
        except Exception as e:
            self.log.critical(f'Error occurred in connecting to TelescopeServer: {e}')
            raise ConnectionException(f'Unable to connect to TelescopeServer: {e}')

    def is_alive(self) -> bool:
        pass

    def disconnect(self) -> bool:
        pass

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
        if slit is not None and slit.group(0) == 'open':
            return True

        # in any other scenario, return False
        return False

    def close_dome(self) -> bool:
        """ Closes the dome, but leaves the session connected. Returns
        True if successful in closing down, False otherwise.
        """
        result = self.run_command(telescope.close_dome)

        # TODO: Parse output to make sure dome closed successfully
        # use telescope.close_dome_re
        return True

    def close_down(self) -> bool:
        return True

    def lock(self, user: str) -> bool:
        """ Lock the telescope with the given username. 
        """
        pass

    def unlock(self) -> bool:
        """ Unlock the telescope if you have the lock. 
        """
        pass

    def locked(self) -> (bool, str):
        """ Check whether the telescope is locked. If it is, 
        return the username of the lock holder. 
        """
        pass

    def keep_open(self, time: int) -> bool:
        pass

    def get_cloud(self) -> float:
        pass

    def get_dew(self) -> float:
        pass

    def get_rain(self) -> bool:
        pass

    def get_sun_alt(self) -> float:
        pass

    def get_moon_alt(self) -> float:
        pass

    def get_weather(self) -> dict:
        pass

    def weather_ok(self) -> bool:
        pass

    def goto_target(self, target: str) -> bool:
        pass

    def goto_point(self, ra: str, dec: str) -> bool:
        pass

    def target_visible(self, target: str) -> bool:
        pass

    def point_visible(self, ra: str, dec: str) -> bool:
        pass

    def target_altaz(self, target: str) -> (float, float):
        pass

    def point_altaz(self, ra: str, dec: str) -> (float, float):
        pass

    def offset(self, ra: float, dec: float) -> bool:
        pass

    def enable_tracking(self) -> bool:
        pass

    def get_focus(self, focus: float) -> bool:
        pass

    def set_focus(self, focus: float) -> bool:
        pass

    def auto_focus(self) -> bool:
        pass

    def current_filter(self) -> str:
        pass

    def change_filter(self, filter: str) -> bool:
        pass

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
            if self.dome_open() is True:
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
                self.log.warn(f'Bad weather for {max_wait} hours. Shutting down the queue...', color='magenta')
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
                self.log.warn('Slit closed during exposure - repeating previous exposure!')
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

        # send message on websocket
        self.websocket.send(command)

        # receive result of command
        result = self.websocket.recv()

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