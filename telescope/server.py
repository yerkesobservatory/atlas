import time
import json
import socket
import logging
import colorlog
import asyncio
import websockets
import paramiko
import uvloop
from config import config


class TelescopeServer(object):

    # this class attribute is used to store whether a client
    # is connected to the telescope server
    connected = False

    def __init__(self):
        """ Establishes a long term SSH connection to the telescope
        control server and starts the processing of websocket handlers
        on the specified ports. 
        """
        # initialize logging system
        self.__init_log()
        
        # create connection to telescope controller
        self.ssh: paramiko.SSHClient = self.connect()

        # set asyncio event loop to use libuv
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        # save the loop as an attribute
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        # start the event loop
        self.start()
        
    def connect(self) -> paramiko.SSHClient:
        """ Create a SSH connection to the telescope control server. 

        Will call exit(1) if there is any error in connection to the telescope.
        """
        ssh = paramiko.SSHClient()
        
        # load host keys for verified connection
        ssh.load_system_host_keys()

        # insert keys - this needs to be removed ASAP
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # connect!
        try:
            ssh.connect(config.telescope.host, username=config.telescope.username)
            self.log.info('Successfully connected to the telescope control server')
        except paramiko.AuthenticationException:  # unable to authenticate
            self.log.critical('Unable to authenticate connection to telescope control server')
            # TODO: Email admin
            exit(1)
        except Exception as e:
            self.log.critical(f'TelescopeServer has encountered an unknown error in '
                              f'connecting to the control server {e}')
            exit(1)

        return ssh

    def start(self):
        """ Start the event loop listening for websocket
        connections. 
        """

        # create a server listening for websocket connections
        start_server = websockets.serve(lambda w, p: self.process(w, p),
                                        'localhost', config.telescope.wsport)

        # start the server running in aysncio/libuv
        self.log.info('Starting websocket server')
        self.loop.run_until_complete(start_server)
        self.loop.run_forever()

    @staticmethod
    def command_valid(command: str) -> (bool, str):
        """ Check whether a message is valid and safe for execution. 
        
        Returns True if it should be executed, False otherwise. 
        """
        # a list of banned keywords that shouldn't be executed
        # under any circumstances
        banned = ['sudo', 'su ', '&&', '||', 'sh ', 'bash ', 'zsh ',
                  'ssh ', 'cd ', 'systemctl ', 'logout', 'exit ',
                  'rm ', 'root ', 'wget ', 'curl ', 'python ', 'pip p',
                  'telnet', 'chmod ', 'chown ']

        # check whether any banned words are in command
        for string in banned:
            if string in command:
                return False, f'Command cannot contain \"{string}\"'

        return True, ''

    async def process(self, websocket, path):
        """ This is the handler for new websocket
        connections. This exists for the lifetime of 
        the connection by a Telescope class. 
        """
        try:

            self.log.info('Connection request received...')
            # check whether we are connected to someone else
            if self.connected:

                self.log.info('Telescope is in use. Denying new connection')

                # build reply message
                reply = {'success': False,
                         'result': 'TELESCOPE IN USE',
                         'connected': False}

                # send reply saying that are closing connection
                await websocket.send(json.dumps(reply))

                # we return to close connection
                return

            # set our state as connected
            self.connected = True
            self.log.info(f'Client connected.')

            # notify client that they are successfully connected
            reply = {'success': False,
                     'result': 'CONNECTED',
                     'connected': True}
            await websocket.send(json.dumps(reply))

            # keep processing messages until client disconnects
            while True:
                # wait for arrival of a message
                msg = await websocket.recv()
                self.log.info(f'Received message: {msg}')

                # convert message to dictionary
                msg = json.loads(msg)

                # extract some values
                command = msg['command']

                # check that command is valid
                valid, errmsg = self.command_valid(command)
                if valid:
                    # run command on the telescope
                    result = self.run_command(command)
                    reply = {'success': True,
                             'command': command,
                             'result': result}
                else:
                    # this command isn't valid
                    reply = {'success': False,
                             'command': command,
                             'result': errmsg}
                    self.log.warning(errmsg)
                    
                # send result back on websocket
                await websocket.send(json.dumps(reply))

        except websockets.exceptions.ConnectionClosed as _:
            pass
        finally:
            self.log.info(f'Client disconnected')

            # make sure we set our state as disconnected
            TelescopeServer.connected = False

    def run_command(self, command: str) -> str:
        """ Executes a shell command either locally, or remotely via ssh.
        Returns the byte string representing the captured STDOUT
        """
        self.log.info(f'Executing: {command}')

        # make sure the connection hasn't timed out due to sleep
        # if it has, reconnect
        try:
            self.ssh.exec_command('who')
        except socket.error as e:

            # try and reconnect
            self.ssh = self.connect()

            # retry command
            self.ssh.exec_command('who')

        # try and execute command 5 times if it fails
        numtries = 0; exit_code = 1
        while numtries < 5 and exit_code != 0:
            try:

                # run command on server
                stdin, stdout, stderr = self.ssh.exec_command(command)
                result = stdout.readlines()

                # increment number of tries
                numtries += 1

                # check exit code
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    self.log.warning(f'Command returned {exit_code}. Retrying in 3 seconds...')
                    time.sleep(3)
                    continue

                # valid result received
                if len(result) > 0:
                    result = ' '.join(result)

                # strip trailing and leading whitespace
                result = result.strip()

                self.log.info(f'Command Result: {result}')
                return result

            except Exception as e:
                self.log.critical(f'Failed while executing {command}')
                self.log.critical(f'run_command: {e}')

        return ''

    def __init_log(self) -> bool:
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
        self.log = logging.getLogger('telescope_server')
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(stream)

        return True
