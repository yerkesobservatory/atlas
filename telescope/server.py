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
        control server and starts the processing of websocket handlers
        on the specified ports. 
        """

        # initialize logging system
        if not TelescopeServer.log:
            TelescopeServer.__init_log()

        # do not connect to database if authentication is disabled
        if authentication:
            # create connection to database - get users collection
            try:
                self.db_client = pymongo.MongoClient(host='localhost', port=27017)
                self.users = self.db_client.seo.users
            except:
                errmsg = 'Unable to connect or authenticate to database. Exiting...'
                self.log.critical(errmsg)
                raise ConnectionException(errmsg)

        # whether we should authenticate
        self.authentication = authentication
        
        # websocket for current connection
        websocket: websockets.WebSocketServerProtocol = None

        # the last time that a command was executed for client used to compute timeouts
        last_exec_time: datetime.datetime = datetime.datetime(1, 1, 1)
        
        # telescope to execute commands
        try:
            self.telescope = SSHTelescope()
        except Exception as e:
            self.telescope = None
            self.log.critical(f'TelescopeServer unable to connect to telescope controller. Reason: {e}')
            return

        # get list of telescope methods
        self.telescope_methods = [func for func in dir(SSHTelescope) if callable(getattr(SSHTelescope, func))
                   and not func.startswith("_")]


        # set asyncio event loop to use libuv
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        # event loop to execute commands asynchronously
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        # start the event loop
        self.start()

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
        self.log.info('Starting websocket server...')
        self.loop.run_until_complete(start_server)
        self.loop.run_forever()

    def command_authorized(self, user: dict, command: str):
        """ Check that 'user' is authorized to run 'command'. 
        
        Returns True if OK, False if NOT AUTHORIZED. 
        """

        # if authentication is disabled, every command is OK
        if not self.authentication:
            return True

        # get the roles of the current user
        roles = user['roles']
        role = ""

        # find cli-* role; TODO: This could be made nicer
        for r in roles:
            if r[0:4] == 'cli-':
                role = r 

        # check error
        if role == "":
            self.log.debug('No command-line roles found.')
            return False

        # check commands that anyone can run
        if command in ['is_alive', 'disconnect', 'get_cloud', 'get_dew', 'get_rain',
                       'get_sun_alt', 'get_moon_alt', 'get_weather', 'connect']:
            return True

        # check command for roles
        if role == 'cli-imaging':
            return command in ['lock', 'unlock', 'locked', 'keep_open', 'goto_target',
                               'goto_point', 'target_visible', 'point_visible',
                               'target_altaz', 'point_altaz', 'enable_tracking',
                               'current_filter', 'change_filter', 'wait', 'wait_until_good',
                               'take_exposure', 'take_dark', 'take_bias']
        elif role == 'cli-full':
            return True
        else:
            # this is an unknown role, default to no exec rights
            return False

    async def process(self, websocket, path):
        """ This is the handler for new websocket
        connections. This exists for the lifetime of 
        the connection by a Telescope class. 
        """
        try:
            self.log.info('Connection request received. Awaiting authentication...')

            # we authenticate the username and password
            msg = await websocket.recv()
            msg = json.loads(msg)
            email = msg.get('email')
            password = msg.get('password')

            if not email or not password:
                self.log.info('Connection request does not contain authentication info. Disconnecting...')
                return

            self.log.info(f'Attempting to authenticate {email}')

            if authentication:
                # check username and password against DB
                try:
                    user = self.users.find_one({'emails.address': email})
                    if user:
                        # meteor hashes password with sha256 before passing to bcrypt
                        # passwords sent to us are already sha256 encrypted by Telescope
                        stored_password = user['services']['password'].get('bcrypt')
                        if bcrypt.checkpw(password.encode('utf8'), stored_password.encode('utf8')):
                            self.log.info('User successfully authenticated.')
                        else:
                            self.log.info('Invalid password. Disconnecting...')
                            return
                    else:
                        self.log.warning('User not found. Disconnecting...')
                        return
                except Exception as e:
                    self.log.error('An error occured in authenticating the user. Disconnecting...')
                    self.log.error(e)
                    return

            # we have now authenticated the user
            
            # check whether we are connected to someone else
            if TelescopeServer.connected:

                # check that we haven't timed out
                delta = datetime.datetime.now() - self.last_exec_time
                if delta.seconds >= 60*config.telescope.timeout:
                    self.log.info('Current user has timed out. Accepting new connection...')

                    # close existing connection
                    self.websocket.close()
                else:
                    self.log.info('Telescope is in use. Denying new connection...')

                    # build reply message
                    reply = {'connected': False,
                             'result': 'TELESCOPE IN USE'}

                    # send reply saying that are closing connection
                    await websocket.send(json.dumps(reply))

                    # we return to close connection
                    return

            # set our state as connected
            self.connect_client(websocket)
            self.log.info(f'Client connected.')

            # generate a token
            token = ''.join(random.choices(string.ascii_uppercase+string.ascii_lowercase+string.digits,
                                           k=32))

            # notify client that they are successfully connected
            reply = {'connected': True,
                     'result': 'CONNECTED',
                     'token': token}
            await websocket.send(json.dumps(reply))

            if authentication:
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
                    reply = {'success': False,
                             'command': command,
                             'result': 'NOT AUTHORIZED'}
                    await websocket.send(json.dumps(reply))

                print("Yay!")

                # set last exec time
                self.last_exec_time = datetime.datetime.now()

                # extract arguments
                args = dict(msg) # copy msg dict
                del args['command'] # remove command from args

                # see if method exists
                if command in self.telescope_methods:

                    # run command on the telescope
                    result = self.run_command(command, **args)
                    reply = {'success': True,
                         'command': command,
                         'result': result}

                # send result back on websocket
                await websocket.send(json.dumps(reply))

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
        """ Executes a shell command either locally, or remotely via ssh.
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
