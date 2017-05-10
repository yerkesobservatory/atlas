from config import Config as config
from templates import base


class MyServer(base.AtlasServer):
    """ USER MUST DESCRIBE FUNCTIONALITY OF THIS CLASS IN THIS DOCSTRING
    """

    def __init__(self):
        """ This creates a new server listening on a user-defined set of topics
        on the MQTT broker specified in config
        """
        
        # MUST INIT SUPERCLASS FIRST
        super().__init__("SERVER NAME")

        # USER MUST COMPLETE THEIR INITIALIZATION HERE

        # MUST END WITH start() - THIS BLOCKS
        self.start()

    @staticmethod
    def topics() -> [str]:
        """ Returns the topics the server will be subscribed to.

        This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/atlas/queue'] etc.
        """

        # USER MUST COMPLETE

        return []
    
    def process_message(self, topic: str, msg: dict):
        """ This function is given a dictionary message from the broker
        and must decide how to process the message. 
        """
        # USER MUST COMPLETE

    def close(self) -> bool:
        """ This function is called during close down; use this to close
        any resources that you have opened. 

        This is called by the atexit handler; only close files/connections
        that *you* opened. Return true if all went well (server will exit(0)), 
        or False if something went wrong (server will exit(1))
        """

        return True
