## This file implements the execution of telescope queues; at the scheduled time,
## it loads in the queue file for tonight's imaging, converts them to Session objects,
## and executes them
import time
import paho.mqtt.client as mqtt
import telescope
import typing
import signal
import sys
import json
import yaml
from os.path import dirname, realpath

class Executor(object):
    """ This class is responsible for executing and scheduling a 
    list of imaging sessions stored in the queue constructed by
    the queue server.
    """

    def __init__(self, filename: str):
        """ This creates a new executor to execute a single nights
        list of sessions stored in the JSON file specified by filename. 
        """

        # filename to be read
        self.filename = filename

        # load queue from disk
        self.sessions = []
        self.load_queue(self.filename)

        # instantiate telescope object for control
        self.telescope = telescope.Telescope()

        # create a handler for SIGINT
        signal.signal(signal.SIGINT, self.handle_exit)

        
    def load_queue(self, filename: str) -> list:
        """ This loads a JSON queue file into a list of Python session
        objects that can then be executed. 
        """

        try:
            with open(self.filename) as queue:
                for line in queue:
                    self.sessions.append(json.loads(line))
        except:
            self.__log('Unable to open queue file. Please check that exists.',
                       'red')
            exit(-1)

    def execute_queue(self) -> bool:
        """ Executes the list of session objects for this queue. 
        """
        count = 1
        for session in self.sessions:
            # check whether every session executed correctly
            self.__log("Executing session {} for {}".format(count, session['user']), color="cyan")
            if not self.execute(session):
                return False
            count += 1

        return True


    def execute(self, session: dict) -> bool:
        """ Execute a single imaging session. 
        """
        pass

    
    def handle_exit(self, signal, frame):
        """ SIGINT handler to check for Ctrl+C for quitting the executor. 
        """
        self.log('Are you sure you would like to quit [y/n]?', 'cyan')
        choice = input().lower()
        if choice == "y":
            self.__log('Quitting executor and closing the dome...', 'cyan')
            self.telescope.close_down()
            sys.exit(0)

            
    def __log(self, msg: str, color: str = 'white') -> bool:
        """ Prints a log message to STDOUT. Returns True if successful, False
        otherwise.
        """
        colors = {'red':'31', 'green':'32', 'blue':'34', 'cyan':'36',
                  'white':'37', 'yellow':'33', 'magenta':'34'}
        logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        log = '\033[1;'+colors[color]+'m'+logtime+' SERVER: '+msg+'\033[0m'
        print(log)
        return True
