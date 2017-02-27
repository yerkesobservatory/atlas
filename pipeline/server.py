import time
import typing
import sys
import json
import paho.mqtt.client as mqtt
import luigi

class PipelineServer(object):
    """ This class represents a server that subscribes to messages from every
    topic; once it has received a request, process_message() is called, which
    writes the message to a log file
    """

    def __init__(self, config: dict):
        """ This creates a new server listening on the specified port; this does
        not start the server listening, it just creates the server. start() must
        be called for the server to be initialized.
        """

        self.log('Creating new pipeline...', 'green')

        # mqtt client to handle connection
        self.client = self.connect()

        # start the pipeline server
        self.start()


    def connect(self):
        """ Create and return a connection to the MQTT broker.
        """
        client = mqtt.Client()

        # connect to message broker
        try:
            self.client.connect(config['server']['host'], config['mosquitto']['port'], 60)
            self.log('Successfully connected to '+config['general']['name'], color='green')
        except:
            self.log('Unable to connect to '+config['general']['name']+'. Please try again later.'
                     'If the problem persists, please contact '+config['general']['email'], 'red')
            print(sys.exc_info())
            exit(-1)

        return client


    @staticmethod
    def log(msg: str, color: str='white') -> bool:
        """ Prints a log message to STDOUT. Returns True if successful, False
        otherwise.
        """
        colors = {'red':'31', 'green':'32', 'blue':'34', 'cyan':'36',
                  'white':'37', 'yellow':'33', 'magenta':'34'}
        logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        log = '\033[1;'+colors[color]+'m'+logtime+' PIPELINE: '+msg+'\033[0m'
        print(log)
        return True


    def process_message(self, _client, _userdata, msg) -> list:
        """ This function is called whenever a message is received.
        """
        ## THIS MUST ADD TASK TO LUIGI
        


    def start(self):
        """ Starts the servers listening for new requests; server blocks
        on the specified port until it receives a request
        """
        self.client.on_message = self.process_message
        self.client.subscribe('/seo/pipeline')
        self.client.loop_forever()
