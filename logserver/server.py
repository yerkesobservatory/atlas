""" This server process listens for notification requests, processes their messages, and emails
the appropriate email address with the time, date, error message, and other relevant information. 
"""

import json
from templates import mqtt


class LogServer(mqtt.MQTTServer):
    """ This class represents a server that subscribes to messages from every
    topic; once it has received a request, process_message() is called, which
    writes the message to a log file
    """

    def __init__(self, config: {str}):
        """ Initializes and starts server
        """

        # MUST INIT SUPERCLASS FIRST
        super().__init__(config, "Log Server")

        
        # MUST END WITH start() - THIS BLOCKS
        self.start()


    def topics(self) -> [str]:
        """ This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/seo/queue'] etc.
        """

        return ['#']


    def process_message(self, topic: str, msg: {str}) -> list:
        """ This function is called whenever a message is received.
        """
        self.log(topic+": "+msg)
