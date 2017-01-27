## This file implements the execution of telescope queues; at the scheduled time,
## it loads in the queue file for tonight's imaging, converts them to Session objects,
## and executes them
import time
import paho.mqtt.client as mqtt
import typing
import telescope
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

    def __init__(self, filename: str, dryrun: bool = False):
        """ This creates a new executor to execute a single nights
        list of sessions stored in the JSON file specified by filename. 
        """

        # filename to be read
        self.filename = filename

        # load queue from disk
        self.sessions = []
        self.load_queue(self.filename)
        self.__log("Executor has successfully loaded queue")

        # instantiate telescope object for control
        self.telescope = telescope.Telescope(dryrun=True)

        # create a handler for SIGINT
        signal.signal(signal.SIGINT, self.handle_exit)

        # take numbias*exposure_count biases
        self.numbias = 3

        
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
            self.__log("Executing session {} for {}".format(count, session['user']), color="blue")
            if not self.execute(session):
                return False
            count += 1

        return True


    def execute(self, session: dict) -> bool:
        """ Execute a single imaging session. 
        """

        # calculate base file name
        date = time.strftime('%Y_%m_%d', time.gmtime())
        basename = date+'_'+session['user']
        
        try:
            # point telescope at target
            self.__log("Slewing to {}".format(session['target']))
            self.telescope.goto_target(session['target'])

            # extract variables
            exposure_time = session['exposure_time']
            exposure_count = session['exposure_count']
            binning = session['binning']

            # for each filter
            for filt in session['filters']:
                self.take_exposures(basename, exposure_time, exposure_count, binning, filt)

            # reset filter back to clear
            self.__log("Switching to clear filter")
            self.telescope.change_filter('clear')
        
            # take exposure_count darks
            self.take_darks(basename, exposure_time, exposure_count, binning)

            # take numbias*exposure_count biases
            self.take_biases(basename, exposure_time, exposure_count, binning, self.numbias)

        except:
            self.__log('The executor has encountered an error. Please manually'
                       'close down the telescope.', 'red')


    def take_exposures(self, basename: str, time: int, count: int, binning: int, filt: str):
        """ Take count exposures, each of length time, with binning, using the filter
        filt, and save it in the file built from basename. 
        """
        # change to that filter
        self.__log("Switching to {} filter".format(filt))
        self.telescope.change_filter(filt)
         
        # take exposure_count exposures
        for i in range(0, count):
                
            # create image name
            filename = basename+'_'+filt+'_'+str(time)+'s'
            filename += '_bin'+str(binning)+'_'+str(i)
            self.__log("Taking exposure {}/{} with name: {}".format(i+1, count, filename))

            # take exposure
            self.telescope.take_exposure(filename, time, binning)

        
    def take_darks(self, basename: str, time: int, count: int, binning: int):
        """ Take a full set of dark frames for a given session. Takes exposure_count
        dark frames.
        """
        for nd in range(0, count):
            # create file name
            filename = basename+'_dark_'+str(time)+'s'
            filename += '_bin'+str(binning)+'_'+str(nd)
            self.__log("Taking dark {}/{} with name: {}".format(nd+1, count, filename))

            self.telescope.take_dark(filename, time, binning)

            
    def take_biases(self,  basename: str, time: int, count: int, binning: int, numbias: int):
        """ Take the full set of biases for a given session. 
        This takes exposure_count*numbias biases
        """

        # create file name for biases
        biasname = basename+'_'+str(time)
        biasname += '_bin'+str(binning)
        self.__log("Taking {} biases with names: {}".format(count*numbias, biasname))

        # take 3*exposure_count biases
        for nb in range(0, count*numbias):
            self.telescope.take_bias(biasname+'_'+str(nb), binning)

    
    def handle_exit(self, signal, frame):
        """ SIGINT handler to check for Ctrl+C for quitting the executor. 
        """
        self.log('Are you sure you would like to quit [y/n]?', 'cyan')
        choice = input().lower()
        if choice == "y":
            self.__log('Quitting executor and closing down...', 'cyan')
            self.telescope.close_down()
            sys.exit(0)

            
    def __log(self, msg: str, color: str = 'white') -> bool:
        """ Prints a log message to STDOUT. Returns True if successful, False
        otherwise.
        """
        colors = {'red':'31', 'green':'32', 'blue':'34', 'cyan':'36',
                  'white':'37', 'yellow':'33', 'magenta':'34'}
        logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        log = '\033[1;'+colors[color]+'m'+logtime+' EXECUTOR: '+msg+'\033[0m'
        print(log)
        return True


if __name__ == "__main__":
    exec = Executor("/Volumes/andromeda/seo/seo/logs/seo_2017-01-27_imaging_queue.json", dryrun=True)
    exec.execute_queue()
    
