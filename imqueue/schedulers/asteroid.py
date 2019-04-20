from typing import List
import telescope.ssh_telescope as Telescope

def schedule(observations: List['Observation'], session: 'Session') -> ('Observation', int):
    """ Return the next object to be imaged according to this algorithm, and the
    time that the executor must wait before imaging this observation. 

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
    return observations[0], 0


def execute(observation: 'Observation', telescope: Telescope, session: 'Session') -> bool:
    """ Observe the requested observation and save the data according to session. 

    This function is provided a connected Telescope() object that should be used
    to execute (observe) the target specified by Observation. The telescope will be provided 
    "ready-to-image" (slit open etc.) The Session object that includes this observation 
    is also provided. Any execute() function must abide by the rules outlined below; 
    these constitute a contract with the queue executor. 

    1. At reasonable intervals, execute() must check the current time (Telescope.current_time), 
    and compare it to session.end_time. If the current time is later than the end time
    of the session, execute() must return. 

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
    return True
