""" This file implements the execution of telescope queues; at the scheduled time,
it loads in the queue file for tonight's imaging and executes each request
"""

import time
import pymodm
import telescope
import schedule as run
from config import config
from typing import List, Dict
from imqueue import schedule
from routines import focus
from routines import flats
from db.observation import Observation
from db.session import Session
from telescope import telescope
from templates import base
from telescope.exception import *


class Executor(base.AtlasServer):
    """ This class is responsible for executing and scheduling a
    list of imaging observations stored in the queue constructed by
    the queue server.
    """

    def __init__(self):
        """ This creates a new executor to execute a single nights observations. 
      
        This creates a new Executor object; it does not start the executor, or load
        the queue from the database.
        """

        # initialize AtlasServer superclass
        super().__init__('Executor')

        # dummy telescope variable
        self.telescope: telescope.Telescope = None

        # connect to mongodb
        pymodm.connect("mongodb://127.0.0.1:3001/meteor", alias="atlas")
        self.log.info('Successfully connected to the queue database')

        # schedule the start() function to run every night
        run.every().day.at("20:00").do(self.start)

        # loop while we wait for the right time to start
        while True:
            wait = run.idle_seconds()
            self.log.info(f'Executor is sleeping {wait/60/60:.{2}} hours until startup...')
            run.run_pending()
            time.sleep(wait)

    @staticmethod
    def topics() -> List[str]:
        """ Returns the topics the server will be subscribed to.
                
        This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/atlas/queue'] etc.
        """

        return ['/'+config.general.shortname+'/executor']
    
    def process_message(self, topic: str, msg: Dict):
        """ This function is given a dictionary message from the broker
        and must decide how to process the message. 
        """
        # TODO: what messages should the queue receive? 
        self.log.warn('Executor received unknown message')

    def load_observations(self, session: Session) -> List[Observation]:
        """ This function returns a list of all observations
        in the database that have not been executed, and that match
        the conditions specified in the session. 
        """
        # TODO: Add filtering based upon session requirements
        return Observation.objects.all()

    def open_up(self):
        """ Open up the telescope, enable tracking, and set
        the dome to stay on. 
        """
        self.telescope.open_dome()
        self.telescope.enable_tracking()
        self.telescope.keep_open(3600)  # TODO: use shorter keep_open times more regularly

    def start(self) -> bool:
        """ Start the execution routine. 

        This method is called by the Threading timer when the executor
        is scheduled to start. This attempts to lock the telescope, take flats, 
        focus the telescope, and then, if their is a scheduled Session, execute
        that session, or if not, unlock the telescope and start a new timer. 
        """
        # instantiate telescope object for control
        try:
            self.telescope = telescope.Telescope()
            self.log.info('Executor has connection to telescope')
        except Exception as e:
            self.log.warn(f'Error connecting to telescope: {e}')

        # try and acquire the telescope lock; TODO: This could be made smarter
        while not self.telescope.lock(config.telescope.username):
            time.sleep(300) # sleep for 5 minutes
            
        # check that weather is acceptable for flats
        self.telescope.wait_until_good(sun=0)

        # open telescope
        self.log.info('Opening telescope dome...')
        self.open_up()

        # take flats
        flats.take_flats(self.telescope)

        # wait until the weather is good to observe stars
        self.telescope.wait_until_good()

        # focus the telescope
        focus.focus(self.telescope)

        # TODO: Check if queue is scheduled
        session = None # TODO: we need to find the sesion for tonight
        while self.execute_session(session):
            pass # we need to find the next session for tonight

        return True

    def execute_session(self, session: Session) -> bool:
        """ Executes the list of observations.
        
        TODO: Describe docstring
        """

        # continually execute observations from the queue
        while True:

            # load observations from the database
            # we load it in the loop so that database changes can be made after the queue has started
            observations = self.load_observations(session)

            # run the scheduler and get the next observation to complete
            self.log.info(f'Calling the {session.scheduler} scheduler...')
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

        # close down
        self.log.info('Finished executing the queue! Closing down...')
        self.close()

        return True
    
    def close(self) -> bool:
        """ Close the executor in event of success of failure; closes the telescope, 
        closes ssh connection. Returns True if shutdown was successful, False otherwise.
        """
        if self.telescope is not None:
            self.telescope.close_down()
            self.telescope.disconnect()

        return True
