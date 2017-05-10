import time
import socket
import logging
import colorlog
import asyncio
import websockets
import paramiko
import uvloop
from config import config


class TelescopeServer(object):

    # this class attribute is used to store all the clients
    # connected to the telescope server
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
        except paramiko.AuthenticationException: # unable to authenticate
            self.log.critical('Unable to authenticate connection to telescope control server')
            exit(1)
            # TODO: Email admin
        except Exception as e:
            self.log.critical(f'TelescopeServer has encountered an unknown error in '
                              f'connecting to the control server {e}')
            exit(1)

        return ssh

    def start(self):
        """ Start the event loop listening for websocket
        connections. 
        """

        process = lambda w, p: self.process(w, p)
        start_server = websockets.serve(process, 'localhost',
                                        config.telescope.wsport)

        self.log.info('Starting websocket server')
        self.loop.run_until_complete(start_server)
        self.loop.run_forever()

    def command_valid(self, command: str) -> bool:
        """ Check whether a message is valid and safe for execution. 
        
        Returns True if it should be executed, False otherwise. 
        """
        # a list of banned keywords that shouldn't be executed
        # under any circum
        banned = ['sudo', 'su ', '&&', '||', 'sh ', 'bash ', 'zsh ',
                  'ssh ', 'cd ', 'systemctl ', 'logout', 'exit ',
                  'rm ', 'root ', 'wget ', 'curl ', 'python ', 'pip p']

        # check whether any banned words are in command
        for string in banned:
            if string in command:
                return False

        return True

    async def process(self, websocket, path):
        """ This is the handler for new websocket
        connections. This exists for the lifetime of 
        the connection by a Telescope class. 
        """
        try:
            self.log(f'Client connected.')
            # set our state as connected
            self.connected = True

            # keep processing messages until client disconnects
            while True:
                # wait for arrival of a message
                msg = await websocket.recv()
                self.log.info(f'Received message: {msg}')

                # check that command is valid
                if self.command_valid(msg):
                    # run command on the telescope
                    result = self.run_command(msg)
                else:
                    result = 'INVALID'
                    self.log.warn(f'Invalid command: {msg}')
                    
                # send result back on websocket
                await websocket.send(result)

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
            self.ssh = self.connect()

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
                    self.log.warn(f'Command returned {exit_code}. Retrying in 3 seconds...')
                    time.sleep(3)
                    continue

                # valid result received
                if len(result) > 0:
                    result = ' '.join(result)
                    self.log.info(f'Command Result: {result}')
                    return result

            except Exception as e:
                self.log.critical(f'Failed while executing {command}')
                self.log.critical(f'run_command: {e}')
                self.log.critical('Please manually close the dome by running'
                         ' `closedown` and `logout`.')

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
