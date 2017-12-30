import pymongo
import importlib
import imqueue
import imqueue.schedulers.general as general
from telescope import Telescope
from typing import List, Dict


def schedule(observations: List[Dict], session: Dict, program: Dict) -> (Dict, int):
    """ Call the requested scheduler and return the next requested observation. 

    This function is responsible for finding the correct scheduler to use
    for the given program (using program.scheduler), and then calling
    that scheduler to determine the next object to observe. This object
    is immediately returned to the caller. 

    Parameters
    ----------
    observations: List[Observation]
        The observations to be observed as part of this program
    program: Program
        The Program object containing parameters for the observing program

    Returns
    -------
    obs: Observation
        The next observation that should be executed. 
    wait: int
        The number of seconds to wait before imaging this observation
    """

    # the normal scheduler
    # if program.get('executor') == 'general':
    #     return general.schedule(observations, session, program)

    # asteroids
    # elif program.get('executor') == 'asteroid':
    #     return asteroid.schedule(observations, program)
    
    # try and load the scheduler dynamically 
    # else:
        # try and load module with that name
    try:
        scheduler = importlib.import_module(f'imqueue.schedulers.{program.get("executor")}')

        # check that it provides both schedule and execute commands
        if 'schedule' in dir(scheduler) and 'execute' in dir(scheduler):
            return scheduler.schedule(observations, session, program)
        # if the above does not work, use general scheduler
    except Exception as e:
        imqueue.Executor.log.warning('Unable to load desired scheduler. Using "general" scheduler...')
        return scheduler.general.schedule(observations, session, program)
        

def execute(observation: Dict, program: Dict, telescope: Telescope, db_client: pymongo.MongoClient) -> bool:
    """ Observe the requested observation and save the data according to program. 

    This function is provided a connected Telescope() object that should be used
    to execute (observe) the target specified by Observation. The Program object 
    that includes this observation is also provided. 

    Parameters
    ----------
    observation: Observation
        The observation to be observed as part of this program
    telescope: Telescope
        A connected telescope object to be used to execute the observation.
    program: Program
        The Program object containing parameters for the observing program

    Returns
    -------
    success: bool
        Return True if successfuly, False otherwise. 
    """

    # the normal executor
    if program.get('executor') == 'general':
        return general.execute(observation, program, telescope, db_client)

    # asteroids
    # elif program.get('executor') == 'asteroid':
    #     return schedulers.asteroid.execute(observation, telescope, program)

    # try and load the scheduler dynamically 
    else:
        # try and load module with that name
        try:
            scheduler = importlib.import_module(f'imqueue.schedulers.{program.get("executor")}')

            # check that it provides both schedule and execute commands
            if 'schedule' in dir(scheduler) and 'execute' in dir(scheduler):
                return scheduler.execute(observation, program, telescope, db_client)
        # if the above does not work, use general scheduler
        finally:
            return general.execute(observation, program, telescope, db_client)
