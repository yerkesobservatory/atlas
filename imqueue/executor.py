""" This file implements the execution of telescope queues; at the scheduled time,
it loads in the queue file for tonight's imaging and executes each request
"""

import time
import json
import datetime
import pymongo
import logging
import colorlog
import telescope
import schedule as run
import telescope.exception as exception
from config import config
from routines import lookup
from typing import List, Dict
from imqueue import schedule
from slacker_log_handler import SlackerLogHandler
from telescope.exception import *


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
            host: str = ':'.join([config.queue.database_host,
                                  str(config.queue.database_port)])
            self.db_client = pymongo.MongoClient(host=host)
            self.users = self.db_client[config.queue.database].users
            self.observations = self.db_client[config.queue.database].observations
            self.sessions = self.db_client[config.queue.database].sessions
            self.programs = self.db_client[config.queue.database].programs
        except Exception as e:
            errmsg = 'Unable to connect or authenticate to database. Exiting...'
            self.log.critical(errmsg)
            raise ConnectionException(errmsg)

        # schedule the start function to run each night at the
        # designated start time (in the servers timezone)
        self.log.info('Executor is initialized and waiting to the designated start time...')
        run.every().day.at(config.queue.start_time).do(self.start)

        while True:
            run.run_pending()
            time.sleep(1)
        
        
    def load_observations(self, session: Dict) -> (List[Dict], Dict):
        """ This function returns a list of all observations
        in the database that have not been executed, and that match
        the conditions specified in the session. 
        """
        # find program that session belongs to
        program = self.programs.find_one({'sessions': session['_id']})

        if program:
            return list(self.observations.find({'program': program['_id'],
                                           'completed': False})), program
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
        self.log.info('Waiting until sunset...')
        self.telescope.wait_until_good(sun=0)
            
        try:
            # tell slack that things are starting
            msg = f'{config.general.name} is starting its auto-calibration routine. Please do not '
            msg += f'use the telescope until you have been notified that the telescope is ready for use'
            self.log.info(msg)
            self.slack_message('#general', msg)
            
            # take flats
            alt: float = telescope.get_sun_alt()
            if (alt <= 0) and (alt >= - 12):
                self.log.info('Starting to take telescope flats...')
                self.telescope.take_flats()
            else:
                self.log.warning(f'Altitude of {alt} is not within the ' \
                                 'acceptable range for flats. Skipping flat calibration...')

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
            msg = f'{config.general.name} is now ready for use! The final error in pointing is RA: {3600*dra}, Dec: {3600*ddec}'
            self.log(msg)
            self.slack_message('#general', msg)
        except Exception as e:
            msg = f'An error occured while auto-calibrating {config.general.name}. Please use care when '
            msg += f'using the telescope'
            self.log(msg)
            self.slack_message('#general', msg)
            self.slack_message('#atlas', f'Auto-calibration error: {e}')
            
        return True
    
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
            result = self.telescope.lock(config.telescope.username, comment=config.queue.comment)
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
            self.log.info('Connecting to telescope controller...')
            self.telescope = telescope.SSHTelescope()
            self.log.debug('Executor has connection to telescope')
        except exception.ConnectionException as e:
            self.critical(f'Error connecting to telescope: {e}')
            return
        except Exception as e:
            self.critical(f'Unknown error connecting to telescope: {e}')
            return

        # attempt lock the telescope
        self.log.info('Attempting to lock telescope...')
        if not (self.lock_telescope()):
            return
            
        # attempt to auto-calibrate the system
        self.log.info('Starting calibration routines...')
        # self.calibrate()

        # Find all sessions that started within the last 12 hours,
        # and end within the next 12 hours
        now = datetime.datetime.now()
        sessions = self.sessions.find({'end': {'$gte' : now,
                                               '$lt' : now + datetime.timedelta(hours=12)},
                                       'start': {'$gt' : now - datetime.timedelta(hours=12)}})
        # sort in ascending order
        sessions.sort('start_time', pymongo.ASCENDING)

        # if there are no sessions, we return so other people can use the telescope
        if not sessions.count():
            self.log.debug('Executor has no sessions. Quitting...')
            return
        self.log.info(f'Executor has found {sessions.count()} sessions.')
            
        # wait until the weather is good to observe
        self.telescope.wait_until_good()

        # for each session scheduled to start tonight
        for session in sessions:
            self.execute_session(session)

        self.log.info('Finished executing the queue! Closing down...')
        self.close()
        
        return True

    def execute_session(self, session: Dict[str, str]) -> bool:
        """ Executes the observations of the program that
        the session is attached.
        
        Wait until the session is due to start, and load all uncompleted
        observations for the corresponding observing program. Schedule the observations, 
        and execute the first observation. We then repeat the scheduling in order
        to optimize target position.
        """

        self.log.info(f'Starting execution of session {session["_id"]} for {session["email"]}')
        
        # check that the session hasn't started already
        if session['start'] > datetime.datetime.now():
            # wait until the session is meant to start
            self.telescope.wait((session['start'] - datetime.datetime.now()).seconds)

        # continually execute observations from the queue
        while True:

            # load observations from the database
            # we load it in the loop so that database changes can be made after the queue has started
            observations, program = self.load_observations(session)

            # if there are no observations left in the program, we return
            if not len(observations):
                self.log.debug('No uncompleted observations left in program...')
                return

            # check if observations have RA/Dec
            for observation in observations:
                if not observation.get('RA') or not observation.get('Dec'):
                    # the observation is missing RA/Dec
                    ra, dec = lookup.lookup(observation.get('target'))
                    if not ra or not dec:
                        self.log.warning(f'Unable to compute RA/Dec for {observation.get("target")}.')
                        continue

                    # save the RA/Dec
                    self.log.info(f'Adding RA/Dec information to observation {observation["_id"]}')
                    self.observations.update({'_id': observation['_id']},
                                             {'$set':
                                              {'RA': ra,
                                               'Dec': dec}})

            # we need to refresh observations since we updated the RA/Dec
            observations, program = self.load_observations(session)            

            # run the scheduler and get the next observation to complete
            self.log.debug(f'Calling the {program.get("executor")} scheduler...')
            schedule = schedule.schedule(observations, session, program)

            # if the scheduler returns None, we are done
            if len(schedule) == 0:
                self.log.debug('Scheduler reports no observations left for this session...')
                break
            
            self.log.info(f'Executing session for {observation["email"]}...')

            # we wait until this observation needs to start
            start_time = schedule.slots[0].start
            self.telescope.wait((start_time - datetime.datetime.now()).to_seconds())

            # make sure that the weather is still good
            self.telescope.wait_until_good()

            # we execute
            # try:
            observation = schedule.scheduled_blocks[0]
            schedule.execute(observation, program, self.telescope, self.db_client[config.queue.database])
            # except Exception as e:
            #     self.log.warn(f'Error while executing {observation}')
            #     self.log.warn(f'{e}')
            #     continue

        return True
    
    def close(self) -> bool:
        """ Close the executor in event of success of failure; closes the telescope, 
        closes ssh connection. Returns True if shutdown was successful, False otherwise.
        """
        if self.telescope is not None:
            self.telescope.close_down()
            self.telescope.disconnect()

        return True

    # TODO
    def slack_message(channel: str, msg: str) -> bool:
        """ Log the given 'msg' to the Slack channel 'channel'. 
        Returns True if successful, False otherwise. 
        """
        return True

    def critical(self, msg) -> bool:
        """ Log the message using self.log.critical and send the message
        to the atlas channel on slack. 
        """
        self.log.critical(msg)
        return self.slack_message('#atlas', msg)
    
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
