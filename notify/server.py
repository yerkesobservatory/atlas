""" This server process listens for notification requests, processes their messages, and emails
the appropriate email address with the time, date, error message, and other relevant information. 
"""

import time
import typing
import sys
import json
import paho.mqtt.client as mqtt

class NotifyServer(object):
    """ This class represents a server that listens for notification requests on
    /`shortname`/notify and emails these messages to the destination
    """

    def __init__(self, config: dict):
        """ This creates a new server listening on the specified port; this does
        not start the server listening, it just creates the server. start() must
        be called for the server to be initialized.
        """

        self.log('Creating new notification server...', 'green')

        # save config file
        self.config = config

        # mqtt client to handle connection
        self.client = self.connect()

        
    def connect(self) -> bool:
        """ Connect to the MQTT broker and return the MQTT client
        object.
        """

        # mqtt client to handle connection
        client = mqtt.Client()

        # server information
        host = self.config.get('server').get('host') or 'localhost'
        port = self.config.get('server').get('mosquitto').get('port') or 1883
        name = self.config.get('general').get('name') or 'Atlas'
        email = self.config.get('general').get('email') or 'your system administrator'

        # connect to message broker
        try:
            client.connect(host, port, 60)
            self.log('Successfully connected to '+name, color='green')
        except:
            self.log('Unable to connect to '+name+'. Please try again later. '
                     'If the problem persists, please contact '+email, 'red')
            print(sys.exc_info())
            exit(-1)

        return client
    

    def log(self, msg: str, color: str = 'white') -> bool:
        """ Prints a log message to STDOUT. Returns True if successful, False
        otherwise.
        """
        colors = {'red':'31', 'green':'32', 'blue':'34', 'cyan':'36',
                  'white':'37', 'yellow':'33', 'magenta':'34'}
        logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        log = '\033[1;'+colors[color]+'m'+logtime+' SERVER: '+msg+'\033[0m'
        print(log)
        return True


    def process_message(self, client, userdata, msg) -> list:
        """ This function is called whenever a message is received.
        """
        self.send_email(msg.payload.decode())
        self.log(msg.topic+": "+msg.payload.decode())

    def send_email(msg):
        """ Parse the decoded message and send the contents to the appropriate
        person
        """
        dest = msg.get('dest') or self.config.get('general').get('email')
        subject = msg.get('subject') or self.config.get('general').get('subject')
        message = msg.get('message')

        # TODO: Send email!


    def run(self):
        """ Starts the servers listening for new requests; server blocks
        on the specified port until it receives a request
        """
        self.client.on_message = self.process_message
        name = '/'+self.config.get('general').get('shortname') or 'atlas'
        self.client.subscribe(name+'/notify')
        self.client.loop_forever()



