""" This file implements the execution of telescope queues; at the scheduled time,
it loads in the queue file for tonight's imaging and executes each request
"""

import time
import pymongo
import logging
import colorlog
import telescope
import schedule as run
import telescope.exception as exception
from config import config
from typing import List, Dict
from imqueue import schedule
from slacker_log_handler import SlackerLogHandler


class Executor(object):
    """ This class is responsible for executing and scheduling a
    list of imaging observations stored in the queue constructed by
    the queue server.
    """

    # default logger
    log = None

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
            self.programs = self.db_client.seo.programs
        except:
            errmsg = 'Unable to connect or authenticate to database. Exiting...'
            self.log.critical(errmsg)
            raise ConnectionException(errmsg)

        # schedule the start() function to run every night
        run.every().day.at("17:00").do(self.start)

        # loop while we wait for the right time to start
        while True:
            wait = run.idle_seconds()
            self.log.info(f'Executor is sleeping {wait/60/60:.{2}} hours until startup...')
            run.run_pending()
            time.sleep(wait)

    def load_observations(self, session: Dict) -> (List[Dict], Dict):
        """ This function returns a list of all observations
        in the database that have not been executed, and that match
        the conditions specified in the session. 
        """
        # find program that session belongs to
        program = self.programs.findOne({'sessions': session['_id']})

        if program:
            return self.observations.find({'program': program['_id']}), program
        else:
            self.log.debug('Unable to find program for this session. Cancelling this session...')
            return [], ''

    def open_telescope(self):
        """ Open up the telescope, enable tracking, and set
        the dome to stay on. 
        """
        self.telescope.open_dome()
        self.telescope.enable_tracking()
        self.telescope.keep_open(600)

    def calibrate(self):
        """ Run a series of calibration routines at sunset in order
        to prepare the telescope for observation. 
        """

        # wait for sun to set
        self.telescope.wait_until_good(sun=0)
            
        try:
            # tell slack that things are starting
            msg = f'{config.general.name} is starting its auto-calibration routine. Please do not '
            msg += f'use the telescope until you have been notified that the telescope is ready for use'
            self.slack_message('#general', msg)

            # take flats
            self.telescope.take_flats()

            # should we take darks here? telescope is still cooling down
            # so dark values will be higher?
            
            # wait until sun is at -12
            self.telescope.wait_until_good(sun=-12)

            # TODO: use routines.lookup to find appropriate star field?
            ra = 'hh:mm:ss'
            dec = 'dd:mm:ss'

            # let's enable tracking just to be safe
            self.telescope.enable_tracking()

            # pinpoint telescope to target (this will fix pointing too!)
            self.telescope.goto_point(ra, dec)
        
            # run auto-focus routine
            self.telescope.auto_focus()

            # let's try pointing again - save final offsets
            result, dra, ddec = self.telescope.goto_point(ra, dec)

            # send final dra, ddec values to slack
            # TODO: convert dra, ddec to arcseconds. Currently in degrees
            msg = f'{config.general.name} is now ready for use! The final error in pointing is RA: {dra}, Dec: {ddec}'
            self.slack_message('#general', msg)
        except Exception as e:
            msg = f'An error occured while auto-calibrating {config.general.name}. Please use care when '
            msg += f'using the telescope'
            self.slack_message('#general', msg)
            self.slack_message('#atlas', f'Auto-calibration error: {e}')
            
        return True

    def critical(self, msg) -> bool:
        """ Log the message using self.log.critical and send the message
        to the atlas channel on slack. 
        """
        self.log.critical(msg)
        return self.slack_message('#atlas', msg)

    def lock_telescope(self) -> bool:
        """ Attempt to lock the executors telescope 6 times, waiting
        5 minutes between each attempt.
        """
        # try and acquire the telescope lock
        for attempts in range(0, 6): # we try 5 times (30 minutes)
            if (attempts == 5):
                self.critical('Unable to lock the telescope after 30 minutes. Executor is shutting down...')
                return

            # try and lock telescope
            result = self.telescope.lock(config.telescope.username)
            if result: # success!
                self.log.debug('Successfully locked telescope')
                return True

            # sleep for 5 minutes
            time.sleep(300)

        return False
            
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
            self.log.debug('Executor has connection to telescope')
        except exception.ConnectionException as e:
            self.critical(f'Error connecting to telescope: {e}')
            return
        except Exception as e:
            self.critical(f'Unknown error connecting to telescope: {e}')
            return

        # attempt lock the telescope
        if not (self.lock_telescope()):
            return
            
        # attempt to auto-calibrate the system
        self.calibrate()

        # TODO: Find all sessions that start within the next 12 hours
        # sessions = self.sessions.find({'start_date': {'$eq': datetime.date.today()}}).sort('start_time', pymongo.ASCENDING)
        sessions = None

        # TODO: sort sessions by start datetime

        # if there are no sessions, we return so other people can use the telescope
        if not sessions:
            self.log.debug('Executor has no sessions. Quitting...')
            return
            
        # wait until the weather is good to observe
        self.telescope.wait_until_good()

        # for each session scheduled to start tonight
        for session in sessions:
            self.execute_session(session)

        self.log.info('Finished executing the queue! Closing down...')
        self.close()
        
        return True

    def execute_session(self, session: Dict) -> bool:
        """ Executes the observations of the program that
        the session is attached.
        
        Wait until the session is due to start, and load all uncompleted
        observations for the corresponding observing program. Schedule the observations, 
        and execute the first observation. We then repeat the scheduling in order
        to optimize target position.
        """
        # get times from session
        start = session['start']
        end = session['end']

        # wait until the session is meant to start
        self.telescope.wait((start - datetime.datetime.now()).seconds)

        # try to open the telescope just to be sure
        self.open_telescope()

        # continually execute observations from the queue
        while True:

            # load observations from the database
            # we load it in the loop so that database changes can be made after the queue has started
            observations, program = self.load_observations(session)

            # if there are no observations left in the program, we return
            if not len(observations):
                self.log.debug('No uncompleted observations left in program...')
                return

            # run the scheduler and get the next observation to complete
            self.log.debug(f'Calling the {program.get("executor")} scheduler...')
            observation, wait = schedule.schedule(observations, session)

            # if the scheduler returns None, we are done
            if not observation:
                self.log.debug('Scheduler reports no observations left for tonight... Closing down')
                break

            # if we need to wait for this observation, we wait
            self.telescope.wait(wait)

            # make sure that the weather is still good
            self.telescope.wait_until_good()

            # TODO: find username of observation
            
            self.log.info(f'Executing session for {observation.user}') # TODO: fix user email
            try:
                # execute session
                # TODO: Look at call signature
                schedule.execute(observation, program, self.telescope, self.db)
            except Exception as e:
                self.log.warn(f'Error while executing {observation}')
                continue

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
        cls.log = logging.getLogger('executor')
        cls.log.setLevel(logging.DEBUG)
        cls.log.addHandler(stream)

        # if requested, enable slack notifications
        if config.notification.slack:

            # channel
            channel = config.notification.slack_channel
            
            # create slack handler
            slack_handler = SlackerLogHandler(config.notification.slack_token, channel, stack_trace=True,
                                              username='sirius', icon_emoji=':dizzy', fail_silent=True)

            # add slack handler to logger
            cls.log.addHandler(slack_handler)

            # define the minimum level of log messages
            slack_handler.setLevel(logging.INFO)

        return True
