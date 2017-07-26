""" This file implements the execution of telescope queues; at the scheduled time,
it loads in the queue file for tonight's imaging and executes each request
"""

import time
import pymongo
import telescope
import schedule as run
import telescope.exception as exception
from config import config
from typing import List, Dict
from imqueue import schedule


class Executor(objects):
    """ This class is responsible for executing and scheduling a
    list of imaging observations stored in the queue constructed by
    the queue server.
    """

    def __init__(self):
        """ This creates a new executor to execute a single nights observations. 
      
        This creates a new Executor object; it does not start the executor, or load
        the queue from the database.
        """
        
        # initialize logging system
        if not Executor.log:
            Executor.__init_log()

        # dummy telescope variable
        self.telescope: telescope.Telescope = None

        # create connection to database - get users collection
        try:
            self.db_client = pymongo.MongoClient()
            self.users = self.db_client.seo.users
            self.observations = self.db_client.seo.observations
            self.sessions = self.db_client.seo.sessions
        except:
            errmsg = 'Unable to connect or authenticate to database. Exiting...'
            self.log.critical(errmsg)
            raise ConnectionException(errmsg)

        # schedule the start() function to run every night
        run.every().day.at("18:00").do(self.start)

        # loop while we wait for the right time to start
        while True:
            wait = run.idle_seconds()
            self.log.info(f'Executor is sleeping {wait/60/60:.{2}} hours until startup...')
            run.run_pending()
            time.sleep(wait)

    def load_observations(self, session: Dict) -> List[Dict]:
        """ This function returns a list of all observations
        in the database that have not been executed, and that match
        the conditions specified in the session. 
        """
        return self.observations.find({'session': session['_id']})

    def open_up(self):
        """ Open up the telescope, enable tracking, and set
        the dome to stay on. 
        """
        self.telescope.open_dome()
        self.telescope.enable_tracking()
        self.telescope.keep_open(3600)  # TODO: use shorter keep_open times more regularly

    def calibrate(self):
        """ Run a series of calibration routines at sunset in order
        to prepare the telescope for observation. 
        """
        pass

    def start(self) -> bool:
        """ Start the execution routine. 

        This method is called by the Threading timer when the executor
        is scheduled to start. This attempts to lock the telescope, take flats, 
        focus the telescope, and then, if their is a scheduled Session, execute
        that session, or if not, unlock the telescope and start a new timer. 
        """

        # instantiate telescope object for control
        try:
            self.telescope = telescope.SSHTelescope()
            self.log.info('Executor has connection to telescope')
        except exception.ConnectionException as e:
            self.log.critical(f'Error connecting to telescope: {e}')
            return
        except Exception as e:
            self.log.critical(f'Unknown error connecting to telescope: {e}')
            return

        # try and acquire the telescope lock; TODO: This could be made smarter
        while not self.telescope.lock(config.telescope.username):
            time.sleep(300) # sleep for 5 minutes

        # wait until sunset
        self.telescope.wait_until_good()
        
        # calibrate the system
        self.calibrate()

        # wait until the weather is good to observe stars
        self.telescope.wait_until_good()

        # focus the telescope
        self.telescope.auto_focus()

        # TODO: Check if queue is scheduled
        sessions = self.sessions.find({'start_date': {'$eq': datetime.date.today()}}).sort('start_time', pymongo.ASCENDING)
        for session in sessions:
            self.execute_session(session)

        self.log.info('Finished executing the queue! Closing down...')
        self.close()
        
        return True

    def execute_session(self, session: Dict) -> bool:
        """ Executes the list of observations.
        
        TODO: Describe docstring
        """

        # continually execute observations from the queue
        while True:

            # load observations from the database
            # we load it in the loop so that database changes can be made after the queue has started
            observations = self.load_observations(session)

            # run the scheduler and get the next observation to complete
            self.log.info(f'Calling the {session.get("scheduler")} scheduler...')
            observation, wait = schedule.schedule(observations, session)

            # if the scheduler returns None, we are done
            if not observation:
                self.log.info('Scheduler reports no observations left for tonight... Closing down')
                break

            # if we need to wait for this observation, we wait
            self.telescope.wait(wait)

            # make sure that the weather is still good
            self.telescope.wait_until_good()

            self.log.info(f'Executing session for {observation.user}')
            try:
                # execute session
                schedule.execute(observation, self.telescope, session, self.db)
            except Exception as e:
                self.log.warn(f'Error while executing {observation}')
                break

        return True
    
    def close(self) -> bool:
        """ Close the executor in event of success of failure; closes the telescope, 
        closes ssh connection. Returns True if shutdown was successful, False otherwise.
        """
        if self.telescope is not None:
            self.telescope.close_down()
            self.telescope.disconnect()

        return True
    
    @classmethod
    def __init_log(cls) -> bool:
        """ Initialize the logging system for this module and set
        a ColoredFormatter. 
        """
        # create format string for this module
        format_str = config.logging.fmt.replace('[name]', 'EXECUTOR')
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
