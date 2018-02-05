""" This file implements the execution of telescope queues; at the scheduled time,
it loads in the queue file for tonight's imaging and executes each request
"""

import re
import time
import json
import pytz
import datetime
import pymongo
import logging
import colorlog
import telescope
import schedule as run
import telescope.exception as exception
import imqueue.calendar as calendar
import imqueue.database as database
import imqueue.schedule as schedule
from config import config
from routines import lookup
from typing import List, Dict
from slacker_log_handler import SlackerLogHandler
from dateutil import parser, tz
from telescope.exception import *


class Executor(object):
    """ This class is responsible for scheduling and executing observations
    stored in the queue database.
    """

    # default logger
    log = None

    def __init__(self):
        """ This creates a new queue executor.

        This creates a new Executor object; it does not start the executor, or load
        the queue from the database.
        """

        # initialize logging system
        if not Executor.log:
            Executor.__init_log()

        # say hi
        self.log.info('Executor is starting up...')

        # dummy telescope variable
        self.telescope: telescope.Telescope = None

        # create connection to database; this raises a fatal
        # exception if it fails
        self.db = database.Database()

        # create calendar
        self.log.info('Connecting to Google Calendar...')
        self.calendar = calendar.Calendar()

        # variable to store completed observations every night
        self.completed_observations = []

        # schedule the start function to run each night at the
        # designated start time (in the servers timezone)
        run.every().day.at(config.queue.start_time).do(self.start)

        # the execution loop; this waits until the appropriate time
        # and then runs self.start()
        while True:

            # we try and start the queue
            self.start()

            # otherwise wait until we are meant to start at night
            self.log.info(f'Executor is initialized and waiting {run.idle_seconds()/60/60:.1f} hours to the designated start time...')
            time.sleep(int((1/24)*run.idle_seconds())) # check in roughly every hour

            self.log.info('Executor is awake; checking if any jobs need to be run...')
            run.run_pending()

    def start(self) -> bool:
        """ Start the execution routine.

        This method is called by the timer when the executor
        is scheduled to start. This attempts to lock the telescope, take flats,
        focus the telescope, and then, if there is a scheduled Session, execute
        that session, or if not, unlock the telescope and start a new timer.
        """

        # check if telescope is available tonight
        available, endtime = self.telescope_available()
        self.log.debug(f'Telescope is available between now and {endtime}')
        if not available:
            self.log.info('Telescope is not available tonight. Shutting down...')
            return

        # instantiate telescope object for control
        try:
            self.log.info('Connecting to telescope controller...')
            self.telescope = telescope.SSHTelescope()
            self.log.info('Executor has successfully connected to the telescope')
        except exception.ConnectionException as e:
            self.log.error(f'Error connecting to telescope: {e}')
            return
        except Exception as e:
            self.log.error(f'Unknown error connecting to telescope: {e}')
            return

        # attempt to lock the telescope
        self.log.info('Attempting to lock telescope...')
        if not (self.lock_telescope()):
            self.log.error('Unable to lock the telescope. Quitting...')
            return

        # attempt to auto-calibrate the system
        self.log.info('Starting calibration routines...')
        self.log.debug('No calibration routines are being run.')
        # self.calibrate()

        # we attempt to load any sessions that are scheduled and end
        # by the end of the telescope availability
        now = datetime.datetime.now()
        sessions = self.db.sessions.find({'end': {'$gte' : now, '$lt' : endtime},
                                          'start': {'$gt' : now - datetime.timedelta(hours=2)}})
        # sort the sessions
        if sessions:
            # sort in ascending order
            sessions = list(sessions.sort('start_time', pymongo.ASCENDING))

        # if there are no scheduled sessions, we create a session to execute
        # general observations
        if not len(sessions):
            self.log.info('No scheduled sessions. Creating a session for the General program...')
            sessions = [{'_id': None, 'programId': None, 'start': datetime.datetime.now(),
                         'end': endtime, 'owner': None, 'email': None, 'completed': False}]
        else:
            self.log.info(f'Executor has found {len(sessions)} sessions.')

        # wait until the weather is good to observe
        self.telescope.wait_until_good()

        # for each session scheduled to start tonight
        for session in sessions:
            self.execute_session(session)

        # we notify the users of all observations that have been completed
        self.notify_users()

        # and we close
        self.log.info('Finished executing the queue! Closing down...')
        self.close()
        self.log.info('Executor has stopped for the night.')

        return True

    def notify_users(self):
        """ Notify the corresponding users of all observations that have
        been completed during the night.
        """
        # this is a map from username to observations
        emails = {}

        # we look at each completed observation
        for observation in self.completed_observations:

            # if we haven't seen this user before, add them to emails
            if observation['email'] not in emails.keys():
                emails[observation['email']] = []

            # add the observation name to the array
            emails[observation['email']].append(observation['target'])

    def telescope_available(self) -> (bool, datetime.datetime):
        """ We check whether the telescope is available for
        queue usage.
        """

        # quick utility to convert times to UTC
        def to_utc(dt: datetime.datetime) -> datetime.datetime:
            return (dt - dt.utcoffset()).replace(tzinfo=tz.tzutc())

        # we check whether the telescope is booked in the previous and next 12 hours
        start = datetime.datetime.now() - datetime.timedelta(hours=12)
        end = datetime.datetime.now() + datetime.timedelta(hours=12)
        return True, end
        events = self.calendar.get_events(start, end)

        # there are events booked tonight
        if len(events) != 0:
            # we sort the events by start time
            events = sorted(events,
                            key=lambda k: parser.parse(k['start'].get('dateTime')))

            # we find the times when the telescope isn't booked
            start = datetime.datetime.now(tz=pytz.utc)
            end = datetime.datetime.now(tz=pytz.utc)

            # if there is already an event started, we assume that
            # the telescope is not available for the rest of the night
            # we can usen events[0] here since we sorted earlier
            first_start = parser.parse(events[0].get('start').get('dateTime'))
            print(start)
            print(first_start)
            print(to_utc(first_start))
            if first_start <= start:
                return False, None

            # we now check each event to find the first non-queue event
            # the queue will run up until the first non-queue event
            for event in events:
                # if the event starts with "Queue", we consider it available time
                if re.match('Queue', event.get('summary', '')):
                    end = to_utc(parser.parse(event.get('end').get('dateTime')))
                else:
                    break

            # assume that we need at least 2 hours for calibration
            if (end - datetime.datetime.now()) <= datetime.timedelta(hours=2):
                return False, None
            else:
                return True, end

        else: # there are no events booked tonight, we go!
            return True, end

    def load_observations(self, session: Dict) -> (List[Dict], Dict):
        """ This function returns a list of all observations
        in the database that have not been executed, and that match
        the conditions specified in the session.
        """
        # check if this is a regular session
        if session.get('_id'):
            # find program that session belongs to
            program = self.programs.find_one({'sessions': session['_id']})

            if program:
                return list(self.db.observations.find({'program': program['_id'],
                                                    'completed': False})), program
            else:
                self.log.debug('Unable to find program for this session. Cancelling this session...')
                return None, None
        else: # TODO: figure priority between multiple public programs
            programs = list(self.db.programs.find({'name': 'General'}))

            # find all observations that are in these programs
            observations = sum([list(self.db.observations.find({'program': program['_id'],
                                                             'completed': False}))
                                for program in programs], [])

            # construct a general program
            program = {'_id': None, 'name': 'General', 'executor': 'general',
                       'owner': None, 'email': None, 'completed': False,
                       'sessions': [], 'observations': [obs['_id'] for obs in observations],
                       'createdAt': datetime.datetime.now()}

            return observations, program

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
            self.log.info(msg)
        except Exception as e:
            msg = f'An error occured while auto-calibrating {config.general.name}. Please use care when '
            msg += f'using the telescope'
            self.log.warning(msg)

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
                self.log.info('Successfully locked telescope.')
                return True

            # sleep for 5 minutes
            time.sleep(300)

        return False

    def execute_session(self, session: Dict[str, str]) -> bool:
        """ Executes the observations of the program that
        the session is attached.

        Wait until the session is due to start, and load all uncompleted
        observations for the corresponding observing program. Schedule the observations,
        and execute the first observation. We then repeat the scheduling in order
        to optimize target position.
        """

        if session.get('_id'):
            self.log.info(f'Starting execution of session {session["_id"]} for {session["email"]}')
        else:
            self.log.info('Executing a public session...')

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
                        # TODO: set error field on observations to prevent code from running again
                        continue

                    # save the RA/Dec
                    self.log.info(f'Adding RA/Dec information to observation {observation["_id"]}')
                    self.db.observations.update({'_id': observation['_id']},
                                                {'$set':
                                                 {'RA': ra,
                                                  'Dec': dec}})

            # we need to refresh observations since we updated the RA/Dec
            observations, program = self.load_observations(session)

            # run the scheduler and get the next observation to complete
            self.log.debug(f'Calling the {program.get("executor")} scheduler...')
            observing_schedule = schedule.schedule(observations, session, program)

            # if the scheduler returns None, we are done
            if len(observing_schedule.scheduled_blocks) == 0:
                self.log.debug('Scheduler reports no observations left for this session...')
                break

            self.log.info(f'Executing observation for {observation["email"]}...')

            # we wait until this observation needs to start
            start_time = observing_schedule.slots[0].start.datetime
            wait_time = (start_time - datetime.datetime.now()).seconds
            # some time elapses between scheduling and execution, must
            # account for wait times that are only a few seconds past
            # the current time
            if (wait_time >= 23.5) and (wait_time <= 24):
                pass # we start immedatiately
            else:
                pass
                # self.telescope.wait(wait_time)

            # make sure that the weather is still good
            self.telescope.wait_until_good()

            # we execute
            try:
                # extract observation from ObservingBlock
                observation = observing_schedule.scheduled_blocks[0].configuration
                schedule.execute(observation, program, self.telescope)
                self.log.info(f'Finished observing {observation["target"]} for {observation["email"]}')

                # record that we completed this observation
                self.completed_observations.append(observation)

            except Exception as e:
                self.log.warn(f'Error while executing {observation}')
                self.log.warn(f'{e}')
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
