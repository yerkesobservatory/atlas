import os
import json
import time
import logging
import colorlog
import getpass
import websocket as ws
from telescope.exception import *


class RemoteTelescope(object):

    # logger for class
    log = None

    def __init__(self, username: str, host: str):
        """ Create a new RemoteTelescope object by connecting to the TelescopeServer, 
        authenticating a new control session, and initializing the logging system. 
        """

        # initialize logging system if not already done
        if not RemoteTelescope.log:
            RemoteTelescope.__init_log()

        # initialize unconnected websocket
        self.websocket = None

        # connect to telescope server
        self.connect(username, host)

    def connect(self, username: str, host: str) -> bool:
        """ Try and connect to the TelescopeServer 
        """
        # try and create connection
        websocket: ws.WebSocket = self.__connect(username, host)

        # if valid connection
        if websocket:
            self.websocket = websocket
            return True

        # otherwise we failed
        return False

    @staticmethod
    def __connect(username: str, host: str) -> ws.WebSocket:
        """ Try and create a connection to the TelescopeServer and
        return the connected websocket. 
        """
        try:
            # get port spec
            port = int(os.environ.get('ATLAS_WS_PORT')) or 27404
            
            # try and connect to telescope server
            uri = f'ws://{host}:{port}'
            websocket = ws.create_connection(uri)

            # send username and password
            msg = {'email': username,
                   'password': getpass.getpass('Atlas Password: ')}
            websocket.send(json.dumps(msg))

            # wait for connection message
            reply = json.loads(websocket.recv())

            if reply.get('connected'):
                RemoteTelescope.log.info('Successfully connected to TelescopeServer')
            else:
                reason = reply.get('result') or 'unknown'
                RemoteTelescope.log.warning(f'Telescope is currently unavailable: {reason}')
        except Exception as e:
            RemoteTelescope.log.critical(f'Error occurred in connecting to TelescopeServer: {e}')
            raise ConnectionException(f'Unable to connect to TelescopeServer: {e}')

        return websocket

    def is_alive(self) -> bool:
        """ Check whether connection to telescope server is alive/working, and whether
        we still have permission to execute commands. 
        """
        try:
            self.run_command('is_alive')
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
        return self.run_command('open_dome')

    def dome_open(self) -> bool:
        """ Checks whether the telescope slit is open or closed. 

        Returns True if open, False if closed. 
        """
        return self.run_command('dome_open')

    def close_dome(self) -> bool:
        """ Closes the dome, but leaves the session connected. Returns
        True if successful in closing down, False otherwise.
        """
        return self.run_command('close_dome')

    def close_down(self) -> bool:
        """ Closes the dome and unlocks the telescope. Call
        this at end of every control session. 
        """
        return self.run_command('close_down')

    def lock(self, user: str, comment: str = 'observing') -> bool:
        """ Lock the telescope with the given username. 
        """
        return self.run_command('lock', user = user, comment = comment)

    def unlock(self) -> bool:
        """ Unlock the telescope if you have the lock. 
        """
        return self.run_command('unlock')

    def locked(self) -> (bool, str):
        """ Check whether the telescope is locked. If it is, 
        return the username of the lock holder. 
        """
        return self.run_command('locked')

    def keep_open(self, time: int) -> bool:
        """ Keep the telescope dome open for {time} seconds. 
        Returns True if it was successful. 
        """
        return self.run_command('keep_open', time = time)

    def get_cloud(self) -> float:
        """ Get the current cloud coverage.
        """
        return self.run_command('get_cloud')

    def get_dew(self) -> float:
        """ Get the current dew value.
        """
        return self.run_command('get_dew')

    def get_rain(self) -> float:
        """ Get the current rain value.
        """
        return self.run_command('get_rain')

    def get_sun_alt(self) -> float:
        """ Get the current altitude of the sun. 
        """
        return self.run_command('get_sun_alt')

    def get_moon_alt(self) -> float:
        """ Get the current altitude of the moon. 
        """
        return self.run_command('get_moon_alt')

    def get_weather(self) -> dict:
        """ Extract all the values for the current weather 
        and return it as a python dictionary. 
        """
        return self.run_command('get_weather')

    def weather_ok(self) -> bool:
        """ Checks whether the sun has set, there is no rain (rain=0) and that
        it is less than 30% cloudy. Returns true if the weather is OK to open up,
        false otherwise.
        """
        return self.run_command('weather_ok')

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
        return self.run_command('goto_target', target=target)

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
        return self.run_command('goto_point', ra=ra, dec=dec)

    def target_visible(self, target: str) -> bool:
        """ Check whether a target is visible using
        the telescope controller commands. 
        """
        return self.run_command('target_visible', target=target)

    def point_visible(self, ra: str, dec: str) -> bool:
        """ Check whether a given RA/Dec pair is visible. 
        """
        return self.run_command('point_visible', ra=ra, dec=dec)

    def target_altaz(self, target: str) -> (float, float):
        """ Return a (alt, az) pair containing floats indicating
        the altitude and azimuth of a target - i.e 'M31', 'NGC4779'
        """
        return self.run_command('target_altaz', target=target)

    def point_altaz(self, ra: str, dec: str) -> (float, float):
        return self.run_command('point_altaz', ra=ra, dec=dec)

    def offset(self, dra: float, ddec: float) -> bool:
        """ Offset the pointing of the telescope by a given
        dRa and dDec
        """
        return self.run_command('offset', ra=ra, dec=dec)

    def enable_tracking(self) -> bool:
        """ Enable the tracking motor for the telescope.
        """
        return self.run_command('enable_tracking')

    def calibrate_motors(self) -> bool:
        """ Run the motor calibration routine. 
        """
        return self.run_command('calibrate_motors')

    def get_focus(self) -> float:
        """ Return the current focus value of the
        telescope.
        """
        return self.run_command('get_focus')

    def set_focus(self, focus: float) -> bool:
        """ Set the focus value of the telescope to
        {focus}. 
        """
        return self.run_command('set_focus', focus=focus)

    def auto_focus(self) -> bool:
        """ Automatically focus the telescope
        using the focus routine. 
        """
        return self.run_command('auto_focus')

    def current_filter(self) -> str:
        """ Return the string name of the current filter. 
        """
        return self.run_command('current_filter')

    def change_filter(self, name: str) -> bool:
        """ Change the current filter specified by {filtname}.
        """
        return self.run_command('change_filter', name=name)

    def make_dir(self, dirname: str) -> bool:
        """ Make a directory on the telescope control server. 
        """
        return self.run_command('make_dir', dirname=dirname)

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
        return self.run_command('wait', wait=wait)
        
    def wait_until_good(self) -> bool:
        """ Wait until the weather is good for observing.
        """
        return self.run_command('wait_until_good')
            
    def take_exposure(self, filename: str, exposure_time: int, count: int = 1, binning: int = 2) -> bool:
        """ Take a full set of dark frames for a given session. Takes exposure_count
        dark frames.
        """
        return self.run_command('take_exposure', filename=filename, exposure_time=exposure_time,
                                count=count, binning=binning)
    
    def take_dark(self, filename: str, exposure_time: int, count: int = 1, binning: int = 2) -> bool:
        """ Take a full set of dark frames for a given session. Takes exposure_count
        dark frames.
        """
        return self.run_command('take_dark', filename=filename, exposure_time=exposure_time,
                                count=count, binning=binning)

    def take_bias(self, filename: str, count: int = 1, binning: int = 2) -> bool:
        """ Take the full set of biases for a given session.
        This takes exposure_count*numbias biases
        """
        return self.run_command('take_bias', filename=filename, count=count, binning=binning)

    def run_command(self, command: str, *_, **kwargs):
        """ Run a command on the telescope server. 
        
        This is done by sending message via websocket to
        the TelescopeServer, that then executes the command
        via SSH, and returns the string via WebSocket.
         
        Parameters
        ----------
        command: str
            The command to be run
        
        """

        # build message
        msg = {'command': command, **kwargs}

        # send message on websocket
        self.websocket.send(json.dumps(msg))

        # receive result of command
        reply = json.loads(self.websocket.recv())

        if not reply.get('success'):
            reason = reply.get('result') or 'unknown reason'
            self.log.warning(f'Unable to execute command: {reason}')
            return None

        # print result
        self.log.info(reply.get('result'))

        # return it for processing by other methods
        return reply.get('result')

    @classmethod
    def __init_log(cls) -> bool:
        """ Initialize the logging system for this module and set
        a ColoredFormatter. 
        """
        # create format string for this module
        fmt = '%(log_color)s%(asctime)s [%(levelname)s] [name]: %(message)s%(reset)s'
        datefmt = '%Y-%m-%d %H:%M:%S'
        format_str = fmt.replace('[name]', 'TELESCOPE')
        formatter = colorlog.ColoredFormatter(format_str, datefmt=datefmt)

        # create stream
        stream = logging.StreamHandler()
        stream.setLevel(logging.DEBUG)
        stream.setFormatter(formatter)

        # assign log method and set handler
        cls.log = logging.getLogger('telescope')
        cls.log.setLevel(logging.DEBUG)
        cls.log.addHandler(stream)

        return True
