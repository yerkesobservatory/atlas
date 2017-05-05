""" This file implements the execution of telescope queues; at the scheduled time,
it loads in the queue file for tonight's imaging and executes each request
"""

import pymodm
import telescope
from typing import List, Dict
from config import config
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

        # create mongodb session
        self.db = odm.ThreadLocalODMSession(bind=ming.create_datastore('observations'))
        self.log('Successfully connected to the queue database')

        # MUST END WITH start() - THIS BLOCKS
        self.start()

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
        self.log('Executor received unknown message')

    def load_observations(self, session: Session) -> List[Observation]:
        """ This function returns a list of all observations
        in the database that have not been executed, and that match
        the conditions specified in the session. 
        """
        # TODO - load unexecuted sessions from mongodb

        return []

    def open_up(self):
        """ Open up the telescope, enable tracking, and set
        the dome to stay on. 
        """
        self.telescope.open_dome()
        self.telescope.enable_tracking()
        self.telescope.keep_open(3600)  # TODO: use shorter keep_open times more regularly

    def execute_session(self, session: Session) -> bool:
        """ Executes the list of observations.
        
        TODO: Describe docstring
        """

        # instantiate telescope object for control
        self.telescope = telescope.Telescope()
        self.log('Executor has connection to telescope')

        # check that weather is acceeptable for flats
        self.telescope.wait_until_good(sun=0)

        # open telescope
        self.log('Opening telescope dome...')
        self.open_up()

        # take flats
        flats.take_flats(self.telescope)

        # wait until the weather is good to observe proper
        self.telescope.wait_until_good()

        # focus the telescope
        focus.focus(self.telescope)

        # continually execute observations from the queue
        while True:

            # load observations from the database
            # we load it in the loop so that database changes can be made after the queue has started
            observations = self.load_observations(session)

            # run the scheduler and get the next observation to complete
            self.log(f'Calling the {session.scheduler} scheduler...')
            observation, wait = schedule.schedule(observations, session)

            # if the scheduler returns None, we are done
            if not observation:
                self.log('Scheduler reports no observations left for tonight... Closing down')
                break

            # if we need to wait for this observation, we wait
            self.telescope.wait(wait)

            self.log(f'Executing session for {observation.user}')
            try:
                # execute session
                schedule.execute(observation, self.telescope, session, self.db)
            except Exception as e:
                self.log(f'Error while executing {observation}', color='red')
                break

        # close down
        self.log('Finished executing the queue! Closing down...', color='green')
        self.finish()

        return True
    
    def finish(self):
        """ Close the executor in event of success of failure; closes the telescope, 
        closes ssh connection, closes log file
        """
        if self.telescope is not None:
            self.telescope.close_down()
            self.telescope.disconnect()

        return 

        
    def close(self):
        """ This function is called when the server receives a shutdown
        signal (Ctrl+C) or SIGINT signal from the OS. Use this to close
        down open files or connections. 
        """
        self.finish()
        
        return
