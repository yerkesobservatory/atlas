import re
import time
import json
import string
import random
import uvloop
import pymongo
import logging
import bcrypt
import datetime
import colorlog
import asyncio
import websockets
import paramiko
import imqueue.database as database
from config import config
from telescope.ssh_telescope import SSHTelescope
from telescope.exception import *


class TelescopeServer(object):

    # whether we have a client connected
    connected: bool = False

    # logger
    log = None

    def __init__(self, authentication=True):
        """ Establishes a long term SSH connection to the telescope
        control server; this does not start the processing of websocket handlers
        on the specified ports. start() must be explicitly called.
        """

        # initialize logging system
        if not TelescopeServer.log:
            TelescopeServer.__init_log()

        # whether we should authenticate
        self.authentication = authentication

        # websocket for current connection
        websocket: websockets.WebSocketServerProtocol = None

        # the last time that a command was executed for client used to compute timeouts
        last_exec_time: datetime.datetime = datetime.datetime(1, 1, 1)

        # do not connect to database if authentication is disabled
        if authentication:
            self.db = database.Database()
        else:
            self.db = None
            self.log.warning('AUTHENTICATION DISABLED!! INSECURE!!')

        # telescope to execute commands
        try:
            self.telescope = SSHTelescope()
        except Exception as e:
            self.telescope = None
            self.log.critical(f'TelescopeServer unable to connect to telescope controller. Reason: {e}')
            raise(ConnectionError(e))

        # get list of telescope methods
        self.telescope_methods = [func for func in dir(SSHTelescope) if callable(getattr(SSHTelescope, func))
                                  and not func.startswith("_")]

        # set asyncio event loop to use libuv
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        # event loop to execute commands asynchronously
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

    def __del__(self):
        """ Disconnect the telescope upon garbage collection.

        NB: This isn't **always** called (see documentation about
        Python garbage collector). It is best to call disconnect()
        in all programs using the server.
        """
        if self.telescope:
            self.telescope.disconnect()

    def start(self):
        """ Start the event loop listening for websocket
        connections.
        """

        # create a server listening for websocket connections
        start_server = websockets.serve(lambda w, p: self.process(w, p),
                                        'localhost', config.telescope.wsport)

        # start the server running in aysncio/libuv
        self.log.info('Started websocket server...')
        self.loop.run_until_complete(start_server)
        self.loop.run_forever()

    def command_authorized(self, user: dict, command: str):
        """ Check that 'user' is authorized to run 'command'.

        Returns True if OK, False if NOT AUTHORIZED.
        """

        # if authentication is disabled, every command is OK
        if not self.authentication:
            self.log.warning('AUTHENTICATION DISABLED!! Allowing any command...')
            return True

        # find cli-* roles for current user
        regex = re.compile('cli-*')
        roles = list(filter(regex.search, user['roles']))

        # check error
        if not roles:
            self.log.debug('No command-line roles found.')
            return False

        # check commands that any cli-* role can run
        if command in ['is_alive', 'disconnect', 'get_cloud', 'get_dew', 'get_rain',
                       'get_sun_alt', 'get_moon_alt', 'get_weather', 'connect', 'locked',
                       'point_altaz', 'target_altaz', 'target_visible', 'point_visible']:
            return True

        # check command for roles
        if 'cli-imaging' in roles:
            return command in ['lock', 'unlock', 'keep_open', 'goto_target',
                               'goto_point', 'enable_tracking', 'wait_until_good',
                               'current_filter', 'change_filter', 'wait',
                               'take_exposure', 'take_dark', 'take_bias']
        elif 'cli-full' in roles:
            return True
        else:
            # this is an unknown role, default to no exec rights
            self.log.warning(f'UNKNOWN cli-role: {roles}. Denying authorization...')
            return False

        # if something weird happens, deny rights
        self.log.warning('Command DENIED for UNKNOWN reason.')
        return False

    async def send_message(self, websocket, **kwargs):
        # send reply saying that are closing connection
        await websocket.send(json.dumps(kwargs))
        return

    async def process(self, websocket, path):
        """ This is the handler for new websocket
        connections. This exists for the lifetime of
        the connection by a Telescope class.
        """
        try:
            self.log.info('Connection request received. Awaiting authentication...')

            # we attempt to authenticate using the username and password
            msg = await websocket.recv()
            msg = json.loads(msg)
            action = msg.get('action')
            email = msg.get('email')
            password = msg.get('password')

            # if the client requested something other than connect
            if action is not 'connect':
                console.log.debug('Received unknown action message')
                return

            # connect essage did not contain an email and password
            if not email or not password:
                self.log.info('Connection request does not contain authentication info. Disconnecting...')
                await self.send_message(websocket, connected=False, result='INVALID AUTHENTICATION MESSAGE')
                return

            self.log.info(f'Attempting to authenticate {email}')

            if self.authentication:
                # check username and password against DB
                try:
                    user = self.users.find_one({'emails.address': email.strip()})
                    if user:
                        # meteor hashes password with sha256 before passing to bcrypt
                        # passwords sent to us are already sha256 encrypted by Telescope
                        stored_password = user['services']['password'].get('bcrypt')
                        if bcrypt.checkpw(password.encode('utf8'), stored_password.encode('utf8')):
                            self.log.info('User successfully authenticated.')
                        else:
                            self.log.info('Invalid password. Disconnecting...')
                            await self.send_message(websocket, connected=False, result='INVALID PASSWORD')
                            return
                    else:
                        self.log.warning('User not found. Disconnecting...')
                        await self.send_message(websocket, connected=False, result='USERNAME NOT FOUND')
                        return
                except Exception as e:
                    self.log.error('An error occured in authenticating the user. Disconnecting...')
                    self.log.error(e)
                    await self.send_message(websocket, connected=False, result='AN UNEXPECTED ERROR OCCURED')
                    return

            # we have now authenticated the user

            # check whether we are connected to someone else
            if TelescopeServer.connected:

                # check that we haven't timed out
                delta = datetime.datetime.now() - self.last_exec_time
                if delta.seconds >= 60*config.telescope.timeout:
                    self.log.info('Current user has timed out. Accepting new connection...')

                    # inform user of time out
                    await self.send_message(self.websocket, connected=False, result='SESSION TIMED OUT')

                    # close existing connection
                    self.websocket.close()
                else:
                    self.log.info('Telescope is in use. Denying new connection...')
                    await self.send_message(websocket, connected=False, result='TELESCOPE IN USE')
                    return

            # set our state as connected
            self.connect_client(websocket)
            self.log.info(f'Client connected.')

            # # generate a token
            # token = ''.join(random.choices(string.ascii_uppercase+string.ascii_lowercase+string.digits,
            #                                k=32))

            # send token
            await self.send_message(websocket, connected=True, result='CONNECTED')

            if self.authentication:
                # explicity save user
                user = self.users.find_one({'emails.address': email})
            else:
                user = None

            # keep processing messages until client disconnects
            while True:
                # wait for arrival of a message
                msg = await websocket.recv()
                self.log.info(f'Received message: {msg}')

                # convert message to dictionary
                msg = json.loads(msg)

                # extract some values
                command = msg.get('command') or ''

                # check for empty
                if command == '':
                    self.log.warning(f'Received empty command message. Skipping...')
                    continue

                # check if command is authorized
                if not self.command_authorized(user, command):
                    self.log.warning(f'User attempted to execute {command} for which they are not authorized.')
                    await self.send_message(websocket, success=False, command=command, result='NOT AUTHORIZED')

                # set last exec time
                self.last_exec_time = datetime.datetime.now()

                # extract arguments
                args = dict(msg) # copy msg dict
                del args['command'] # remove command from args

                # see if method exists
                if command in self.telescope_methods:

                    # run command on the telescope
                    result = self.run_command(command, **args)
                    await self.send_message(websocket, success=True, command=command, result=result)

                # command does not exist
                else:
                    self.log.warning(f'Command does not exist: {command}')
                    await self.send_message(websocket, success=False, command=command, result='COMMAND DOES NOT EXIST')

        # if the connection was closed
        except websockets.exceptions.ConnectionClosed as _:
            pass
        finally:
            self.log.info(f'Client disconnected')

            # make sure we set the global state as disconnected
            self.disconnect_client()

    def connect_client(self, websocket: websockets.WebSocketServerProtocol):
        """ Set the TelescopeServer class to the connected state. """
        TelescopeServer.connected = True
        self.websocket = websocket
        self.last_exec_time = datetime.datetime.now()

    def disconnect_client(self):
        """ Set the TelescopeServer class to the connected state. """
        TelescopeServer.connected = False
        try:
            self.websocket.close()
        except:
            pass
        self.websocket = None
        self.last_exec_time = datetime.datetime.now()

    def run_command(self, command: str, *_, **kwargs) -> str:
        """ Executes a telescope shell command either locally, or remotely via ssh.
        Returns the byte string representing the captured STDOUT
        """
        result = getattr(SSHTelescope, command)(self.telescope, **kwargs)

        return result

    @classmethod
    def __init_log(cls) -> bool:
        """ Initialize the logging system for this module and set
        a ColoredFormatter.
        """
        # create format string for this module
        format_str = config.logging.fmt.replace('[name]', 'TELESCOPE SERVER')
        formatter = colorlog.ColoredFormatter(format_str, datefmt=config.logging.datefmt)

        # create stream
        stream = logging.StreamHandler()
        stream.setLevel(logging.DEBUG)
        stream.setFormatter(formatter)

        # assign log method and set handler
        cls.log = logging.getLogger('telescope_server')
        cls.log.setLevel(logging.DEBUG)
        cls.log.addHandler(stream)

        return True
