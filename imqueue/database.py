import pymongo
import logging
import colorlog
from config import config
from telescope.exception import *

class Database(object):
    """ Manages connection to MongoDB and provides a number of utility
    functions for accessing/finding/querying the database.
    """

    try:
        # database client
        client = pymongo.MongoClient(host=config.queue.database_host,
                                     port=config.queue.database_port)

        database = client[config.queue.database]

        users = database.users

        observations = database.observations

        sessions = database.sessions

        programs = database.programs

        telescopes = database.telescopes

    except Exception as e:
        errmsg = 'Unable to connect or authenticate to database. Exiting...'
        self.log.critical(errmsg)
        raise ConnectionException(errmsg)

    # default logger
    log = None

    def __init__(self):
        """ Right now, this just attempts to initialize the logging system
        """

        # initialize logging system
        if not Database.log:
            Database.__init_log()

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
