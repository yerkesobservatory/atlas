from config import config
from templates import mqtt

class MyServer(mqtt.MQTTServer):
    """ USER MUST DESCRIBE FUNCTIONALITY OF THIS CLASS IN THIS DOCSTRING
    """

    def __init__(self, config: {str}):
        """ USER MUST PROVIDE DOCSTRING FOR __init__
        """

        # MUST INIT SUPERCLASS FIRST
        super().__init__("SERVER NAME")

        # USER MUST COMPLETE THEIR INITIALIZATION HERE

        # MUST END WITH start() - THIS BLOCKS
        self.start()


    def topics(self) -> [str]:
        """ This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/atlas/queue'] etc.
        """

        # USER MUST COMPLETE

        return []


    def process_message(self, topic: str, msg: {str}):
        """ This function is given a JSON dictionary message from the broker
        and must decide how to process the message given the servers purpose. This
        is automatically called whenever a message is received
        """

        # USER MUST COMPLETE

        return


    def close(self):
        """ This function is called when the server receives a shutdown
        signal (Ctrl+C) or SIGINT signal from the OS. Use this to close
        down open files or connections.
        """

        # USER [OPTIONAL]

        return
