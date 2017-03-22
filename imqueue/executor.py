## This file implements the execution of telescope queues; at the scheduled time,
## it loads in the queue file for tonight's imaging, converts them to Session objects,
## and executes them
import sys
import time
import typing
import json

import paho.mqtt.client as mqtt
import telescope
from telescope import telescope
from imqueue import schedule

class Executor(object):
    """ This class is responsible for executing and scheduling a
    list of imaging sessions stored in the queue constructed by
    the queue server.
    """

    def __init__(self, filename: str, config: dict, dryrun: bool=False):
        """ This creates a new executor to execute a single nights
        list of sessions stored in the JSON file specified by filename.
        """

        # filename to be read
        self.filename = filename
        self.config = config

        # initialize logging
        self.init_log()

        # load queue from disk
        self.sessions = []
        self.load_queue(self.filename)
        self.log("Executor has successfully loaded queue")

        # instantiate telescope object for control
        self.telescope = telescope.Telescope(dryrun=dryrun)

        # take numbias*exposure_count biases
        self.numbias = config.get('queue').get('numbias') or 5

        # directory to store images on telescope controller
        self.remote_dir = config.get('queue').get('remote_dir') or '/tmp'

        # directory to store images locally during pipeline
        self.local_dir = config.get('queue').get('dir')

        # connect to MQTT broker
        self.client = self.connect()

        # start!
        self.start()

        
    def load_queue(self, filename: str) -> list:
        """ This loads a JSON queue file into a list of Python session
        objects that can then be executed.
        """

        try:
            with open(self.filename) as queue:
                for line in queue:
                    self.sessions.append(json.loads(line))
        except:
            self.log('Unable to open queue file. Please check that it exists. Exitting',
                     color='red')
            # TODO: Email system admin if there is an error
            self.log("load_queue: "+str(sys.exc_info()), color='red')
            exit(-1)

            
    def connect(self) -> bool:
        """ Connect to the MQTT broker and return the MQTT client
        object.
        """

        # mqtt client to handle connection
        client = mqtt.Client()

        # server information
        host = self.config.get('server').get('host') or 'localhost'
        port = self.config.get('server').get('mosquitto').get('port') or 1883
        name = self.config.get('general').get('name') or 'Atlas'
        email = self.config.get('general').get('email') or 'your system administrator'

        # connect to message broker
        try:
            client.connect(host, port, 60)
            self.log('Successfully connected to '+name, color='green')
        except:
            self.log('Unable to connect to '+name+'. Please try again later. '
                     'If the problem persists, please contact '+email, 'red')
            self.log("connect: "+str(sys.exc_info()), color='red')
            exit(-1)

        return client
    

    def finish(self) -> bool:
        """ Close the executor in event of success of failure; closes the telescope, 
        closes ssh connection, closes log file
        """
        self.telescope.close_down()
        self.telescope.disconnect()
        self.log_file.close()
    
    
    def wait_until_good(self) -> bool:
        """ Wait until the weather is good for observing.
        Waits 10 minutes between each trial. Cancels execution
        if weather is bad for 4 hours.
        """
        elapsed_time = 0 # total elapsed wait time

        # get weather from telescope
        weather = self.telescope.weather_ok()
        while weather is False:

            # sleep for 10 minutes
            time.sleep(10*60) # time to sleep in seconds
            elapsed_time += (10*60)

            # shut down after 4 hours of continuous waiting
            if elapsed_time >= 14400:
                self.log("Bad weather for 4 hours. Shutting down the queue...", color="magenta")
                exit(1)

            # update weather
            weather = self.telescope.weather_ok()

        return True


    def start(self) -> bool:
        """ Executes the list of session objects for this queue.
        """

        # wait until weather is good
        self.wait_until_good()

        # open telescope
        self.telescope.open_dome()

        # iterate over session list
        while len(self.sessions) != 0:

            # default location
            location = ""

            # schedule remaining sessions
            # session = schedule.schedule(self.sessions)
            session = self.sessions[0]

            # check whether we need to wait before executing
            wait = session.get('wait')
            if wait is not None:
                time.sleep(wait)

            # check whether every session executed correctly
            self.log("Executing session for {}".format(session.get('user') or 'none'), color="blue")
            try:
                # execute session
                location = self.execute(session)

                # send remote path to pipeline for async processing
                msg = {'type':'process', 'location':location}
                self.client.publish('/seo/pipeline', json.dumps(msg))

                # remove the session from the remaining sessions
                self.sessions.remove(session)

            except:
                self.log("Error while executiong session for {}".format(session['user']),
                         color="red")
                self.log("start: "+str(sys.exc_info()), color='red')
                self.finish()
                exit(1)
                
        # close down
        self.log('Finished executing the queue! Closing down...', color='green')
        self.finish()

        return True


    def execute(self, session: dict) -> str:
        """ Execute a single imaging session. If successful, returns
        directory where files are stored on telescope control server.
        """

        # calculate base file name
        date = time.strftime('%Y_%m_%d', time.gmtime())
        dirname = self.remote_dir+'/'+'_'.join([date, session.get('user'), session.get('target')])

        # create directory
        self.telescope.make_dir(dirname)

        basename = dirname+'/'+'_'.join([date, session.get('user'), session.get('target')])

        try:
            # point telescope at target
            self.log("Slewing to {}".format(session['target']))
            if self.telescope.goto_target(session['target']) is False:
                self.log("Object is not currently visible. Skipping...", color='magenta')
                return ""

            # extract variables
            exposure_time = session['exposure_time']
            exposure_count = session['exposure_count']
            binning = session['binning']

            # for each filter
            filters = session.get('filters') or ['clear']
            for filt in filters:
                self.telescope.enable_tracking()
                self.take_exposures(basename, exposure_time, exposure_count, binning, filt)

            # reset filter back to clear
            self.log("Switching back to clear filter")
            self.telescope.change_filter('clear')

            # take exposure_count darks
            self.take_darks(basename, exposure_time, exposure_count, binning)

            # take numbias*exposure_count biases
            self.take_biases(basename, exposure_time, exposure_count, binning, self.numbias)

            # return the directory containing the files
            return dirname

        except:
            self.log('The executor has encountered an error. Please manually'
                     'close down the telescope.', 'red')
            self.log("execute: "+str(sys.exc_info()), color='red')
            self.finish()
            return None


    def take_exposures(self, basename: str, exp_time: int,
                       count: int, binning: int, filt: str) -> bool:
        """ Take count exposures, each of length exp_time, with binning, using the filter
        filt, and save it in the file built from basename.
        """
        # change to that filter
        self.log("Switching to {} filter".format(filt))
        self.telescope.change_filter(filt)

        # take exposure_count exposures
        for i in range(0, count):

            # create image name
            filename = basename+'_'+filt+'_'+str(exp_time)+'s'
            filename += '_bin'+str(binning)+'_'+str(i)
            self.log("Taking exposure {}/{} with name: {}".format(i+1, count, filename))

            # take exposure
            self.telescope.take_exposure(filename, exp_time, binning)

        return True


    def take_darks(self, basename: str, exp_time: int, count: int, binning: int) -> bool:
        """ Take a full set of dark frames for a given session. Takes exposure_count
        dark frames.
        """
        for numdark in range(0, count):
            # create file name
            filename = basename+'_dark_'+str(exp_time)+'s'
            filename += '_bin'+str(binning)+'_'+str(numdark)
            self.log("Taking dark {}/{} with name: {}".format(numdark+1, count, filename))

            self.telescope.take_dark(filename, exp_time, binning)

        return True


    def take_biases(self, basename: str, exp_time: int,
                    count: int, binning: int, numbias: int) -> bool:
        """ Take the full set of biases for a given session.
        This takes exposure_count*numbias biases
        """

        # create file name for biases
        biasname = basename+'_'+str(exp_time)
        biasname += '_bin'+str(binning)
        self.log("Taking {} biases with names: {}".format(count*numbias, biasname))

        # take numbias*exposure_count biases
        for nb in range(0, count*numbias):
            self.telescope.take_bias(biasname+'_'+str(nb), binning)

        return True

    
    def init_log(self) -> bool:
        """ Initialize the object logging system - currently only opens
        the logging file. 
        """
        name = self.config.get('general').get('shortname') or 'atlas'
        self.log_file = open('/var/log/'+name+'/executor.log', 'a')

        return True

        
    def log(self, msg: str, color: str='white') -> bool:
        """ Prints a log message to STDOUT. Returns True if successful, False
        otherwise.
        """
        colors = {'red':'31', 'green':'32', 'blue':'34', 'cyan':'36',
                  'white':'37', 'yellow':'33', 'magenta':'34'}
        logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        log = logtime+' EXECUTOR: '+msg
        color_log = '\033[1;'+colors[color]+'m'+log+'\033[0m'
        self.log_file.write(log+'\n')
        self.log_file.flush()
        print(color_log)
        return True
