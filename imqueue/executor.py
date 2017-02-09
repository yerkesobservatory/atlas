## This file implements the execution of telescope queues; at the scheduled time,
## it loads in the queue file for tonight's imaging, converts them to Session objects,
## and executes them
import sys
import time
import typing
import json
import paho.mqtt.client as mqtt
import telescope
import schedule

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

        # load queue from disk
        self.sessions = []
        self.load_queue(self.filename)
        self.log("Executor has successfully loaded queue")

        # instantiate telescope object for control
        self.telescope = telescope.Telescope(dryrun=dryrun)

        # take numbias*exposure_count biases
        self.numbias = 3

        # directory to store images on telescope controller
        self.remote_dir = config['queue']['remote_dir']

        # directory to store images locally
        self.local_dir = config['queue']['local_dir']

        # create mqtt client
        self.client = mqtt.Client()

        # connect to message broker
        try:
            self.client.connect(config['server']['host'], config['mosquitto']['port'], 60)
            self.log('Successfully connected to '+config['general']['name'], color='green')
        except:
            self.log('Unable to connect to '+config['general']['name']+'. Please try again later. '
                     'If the problem persists, please contact '+config['general']['email'], 'red')
            print(sys.exc_info())
            exit(-1)


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
                     'red')
            # TODO: Email system admin
            exit(-1)

    def wait_until_good(self) -> bool:
        """ Wait until the weather is good for observing.
        Waits 10 minutes between each trial. Cancels execution
        if weather is bad for 4 hours.
        """
        elapsed_time = 0 # total elapsed wait time

        # get weather from telescope
        weather = self.telescope.weather_ok()
        while weather is False:

            time.sleep(10*60)  # seconds to sleep
            elapsed_time += 600

            # shut down after 2 hours of continuous waiting
            if elapsed_time >= 14400:
                self.log("Bad weather for 4 hours. Shutting down the queue...", color="magenta")
                exit(1)

        return True


    def execute_queue(self) -> bool:
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
            session = schedule.schedule(self.sessions)

            # check whether we need to wait before executing
            wait = session.get('wait')
            if wait is not None:
                time.sleep(wait)

            # check whether every session executed correctly
            self.log("Executing session for {}".format(session['user']), color="blue")
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
                print(sys.exc_info())
                self.telescope.close_down()
                exit(1)

        # close down
        self.telescope.close_down()

        return True


    def execute(self, session: dict) -> str:
        """ Execute a single imaging session. If successful, returns
        directory where files are stored on telescope control server.
        """

        # calculate base file name
        date = self.remote_dir+"/"+time.strftime('%Y_%m_%d', time.gmtime())
        basename = date+'_'+session['user']+'_'+session['target']

        # create directory
        self.telescope.mkdir(basename)

        try:
            # point telescope at target
            self.log("Slewing to {}".format(session['target']))
            self.telescope.goto_target(session['target'])

            # extract variables
            exposure_time = session['exposure_time']
            exposure_count = session['exposure_count']
            binning = session['binning']

            # for each filter
            for filt in session['filters']:
                self.telescope.enable_tracking()
                self.take_exposures(basename, exposure_time, exposure_count, binning, filt)

            # reset filter back to clear
            self.log("Switching to clear filter")
            self.telescope.change_filter('clear')

            # take exposure_count darks
            self.take_darks(basename, exposure_time, exposure_count, binning)

            # take numbias*exposure_count biases
            self.take_biases(basename, exposure_time, exposure_count, binning, self.numbias)

        except:
            self.log('The executor has encountered an error. Please manually'
                     'close down the telescope.', 'red')
            return None




    def take_exposures(self, basename: str, exp_time: int, count: int, binning: int, filt: str):
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


    def take_darks(self, basename: str, exp_time: int, count: int, binning: int):
        """ Take a full set of dark frames for a given session. Takes exposure_count
        dark frames.
        """
        for numdark in range(0, count):
            # create file name
            filename = basename+'_dark_'+str(exp_time)+'s'
            filename += '_bin'+str(binning)+'_'+str(numdark)
            self.log("Taking dark {}/{} with name: {}".format(numdark+1, count, filename))

            self.telescope.take_dark(filename, exp_time, binning)


    def take_biases(self, basename: str, exp_time: int, count: int, binning: int, numbias: int):
        """ Take the full set of biases for a given session.
        This takes exposure_count*numbias biases
        """

        # create file name for biases
        biasname = basename+'_'+str(exp_time)
        biasname += '_bin'+str(binning)
        self.log("Taking {} biases with names: {}".format(count*numbias, biasname))

        # take 3*exposure_count biases
        for nb in range(0, count*numbias):
            self.telescope.take_bias(biasname+'_'+str(nb), binning)

    @staticmethod
    def log(msg: str, color: str='white') -> bool:
        """ Prints a log message to STDOUT. Returns True if successful, False
        otherwise.
        """
        colors = {'red':'31', 'green':'32', 'blue':'34', 'cyan':'36',
                  'white':'37', 'yellow':'33', 'magenta':'34'}
        logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        log = '\033[1;'+colors[color]+'m'+logtime+' EXECUTOR: '+msg+'\033[0m'
        print(log)
        return True


# if __name__ == "__main__":
#     exec = Executor("/Volumes/andromeda/seo/seo/logs/seo_2017-01-27_imaging_queue.json",
#     dryrun=True)
#     exec.execute_queue()
