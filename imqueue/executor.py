## This file implements the execution of telescope queues; at the scheduled time,
## it loads in the queue file for tonight's imaging and executes each request

import json
import time
from templates import mqtt
import telescope
from telescope import telescope
from routines import schedule


class Executor(mqtt.MQTTServer):
    """ This class is responsible for executing and scheduling a
    list of imaging sessions stored in the queue constructed by
    the queue server.
    """

    def __init__(self, filename: str, config: {str}, dryrun: bool=False):
        """ This creates a new executor to execute a single nights
        list of sessions stored in the JSON file specified by filename.
        """

        # MUST INIT SUPERCLASS FIRST
        super().__init__(config, "Executor")

        # load queue from disk
        self.sessions = []
        self.load_queue(filename)
        self.log("Executor has successfully loaded queue")

        # instantiate telescope object for control
        self.telescope = telescope.Telescope(dryrun=dryrun)

        # take numbias*exposure_count biases
        self.numbias = config.get('queue').get('numbias') or 5

        # directory to store images on telescope controller
        self.remote_dir = config.get('queue').get('remote_dir') or '/tmp'

        # directory to store images locally during pipeline
        self.local_dir = config.get('queue').get('dir')

        # MUST END WITH start() - THIS BLOCKS
        self.start()


    def load_queue(self, filename: str) -> list:
        """ This loads a JSON queue file into a list of Python session
        objects that can then be executed.
        """

        try:
            with open(filename) as queue:
                for line in queue:
                    if line[0] == '#' or len(line) <= 1:
                        continue
                    else:
                        self.sessions.append(json.loads(line))
        except Exception as e:
            self.log('Unable to open queue file. Please check that it exists. Exitting',
                     color='red')
            # TODO: Email system admin if there is an error
            self.log("load_queue: "+str(e), color='red')
            exit(-1)

            
    def wait_until_good(self) -> bool:
        """ Wait until the weather is good for observing.
        Waits 10 minutes between each trial. Cancels execution
        if weather is bad for 4 hours.
        """
        self.log('Waiting until weather is good...')
        elapsed_time = 0 # total elapsed wait time

        # get weather from telescope
        weather = self.telescope.weather_ok()
        while weather is False:

            # sleep for 10 minutes
            self.log('Executor is sleeping for 15 minutes...')
            time.sleep(15*60) # time to sleep in seconds
            elapsed_time += (15*60)

            # shut down after 4 hours of continuous waiting
            if elapsed_time >= 14400:
                self.log("Bad weather for 4 hours. Shutting down the queue...", color="magenta")
                exit(1)

            # update weather
            weather = self.telescope.weather_ok()

        self.log('Weather is good...')
        return True

    
    def start(self) -> bool:
        """ Executes the list of session objects for this queue.
        """

        # wait until weather is good
        self.wait_until_good()

        # open telescope
        self.log('Opening telescope dome...')
        self.telescope.open_dome()

        # iterate over session list
        while len(self.sessions) != 0:

            # default location
            location = ""

            # schedule remaining sessions
            session, wait = schedule.schedule(self.sessions)

            # remove whitespace 'M 83' -> 'M82'
            session['target'] = session['target'].replace(' ', '')
            wait = -1
            self.log("Scheduler has selected {}".format(session))

            # check whether we need to wait before executing
            if wait != -1:
                self.log('Sleeping for {} seconds as requested by scheduler'.format(wait))
                if wait > 10*60:
                    self.telescope.close_down()
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

            except Exception as e:
                self.log("Error while executiong session for {}".format(session['user']),
                         color="red")
                self.log("start: "+str(e), color='red')
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
        date = time.strftime('%Y-%m-%d', time.gmtime())
        username = session.get('user').split('@')[0]
        dirname = self.remote_dir+'/'+'_'.join([date, username, session.get('target')])

        # create directory
        self.log('Making directory to store observations on telescope server...')
        self.telescope.make_dir(dirname)

        basename = dirname+'/'+'_'.join([date, username, session.get('target')])

        try:
            self.telescope.open_dome()
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

        except Exception as e:
            self.log('The executor has encountered an error. Please manually'
                     'close down the telescope.', 'red')
            self.log("execute: "+str(e), color='red')
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

    
    def finish(self) -> bool:
        """ Close the executor in event of success of failure; closes the telescope, 
        closes ssh connection, closes log file
        """
        self.telescope.close_down()
        self.telescope.disconnect()

        
    def close(self):
        """ This function is called when the server receives a shutdown
        signal (Ctrl+C) or SIGINT signal from the OS. Use this to close
        down open files or connections. 
        """
        self.finish()
        
        return 
