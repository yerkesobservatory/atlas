import importlib
import imqueue.schedulers as schedulers
from telescope.telescope import Telescope
from typing import List
from db.observation import Observation
from db.session import Session


def schedule(observations: List[Observation], session: Session) -> Observation:
    """ Call the requested scheduler and return the next requested observation. 

    This function is responsible for finding the correct scheduler to use
    for the given session (using session.scheduler), and then calling
    that scheduler to determine the next object to observe. This object
    is immediately returned to the caller. 

    Parameters
    ----------
    observations: List[Observation]
        The observations to be observed as part of this session
    session: Session
        The Session object containing parameters for the observing session

    Returns
    -------
    obs: Observation
        The next observation that should be executed. 
    wait: int
        The number of seconds to wait before imaging this observation
    """

    # the normal scheduler
    if session.scheduler == 'general':
        return schedulers.general.schedule(observations, session)

    # asteroids
    elif session.scheduler == 'asteroid':
        return schedulers.asteroid.schedule(observations, session)
    
    # try and load the scheduler dynamically 
    else:
        # try and load module with that name
        try:
            scheduler = importlib.import_module(f'imqueue.schedulers.{session.scheduler}')

            # check that it provides both schedule and execute commands
            if 'schedule' in dir(scheduler) and 'execute' in dir(scheduler):
                return scheduler.schedule(observations, session)
        # if the above does not work, use general scheduler
        finally:
            return scheduler.general.schedule(observations, session)
        

def execute(observation: Observation, telescope: Telescope, session: Session) -> bool:
    """ Observe the requested observation and save the data according to session. 

    This function is provided a connected Telescope() object that should be used
    to execute (observe) the target specified by Observation. The Session object 
    that includes this observation is also provided. 

    Parameters
    ----------
    observation: Observation
        The observation to be observed as part of this session
    telescope: Telescope
        A connected telescope object to be used to execute the observation.
    session: Session
        The Session object containing parameters for the observing session

    Returns
    -------
    success: bool
        Return True if successfuly, False otherwise. 
    """

    # the normal executor
    if session.scheduler == 'general':
        return schedulers.general.execute(observation, telescope, session, db)

    # asteroids
    elif session.scheduler == 'asteroid':
        return schedulers.asteroid.execute(observation, telescope, session, db)
    
    # try and load the scheduler dynamically 
    else:
        # try and load module with that name
        try:
            scheduler = importlib.import_module(f'imqueue.schedulers.{session.scheduler}')

            # check that it provides both schedule and execute commands
            if 'schedule' in dir(scheduler) and 'execute' in dir(scheduler):
                return scheduler.execute(observation, telescope, session, db)
        # if the above does not work, use general scheduler
        finally:
            return scheduler.general.schedule(observation, telescope, session, db)
