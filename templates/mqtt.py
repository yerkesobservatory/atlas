import sys
import os
import threading
import typing
import json
import time

import paho.mqtt.client as mqtt


class MQTTServer(object):
    """ This class represents a general purpose server that interacts with the SEO
    ecosystem; subclasses of this server are able to easily extend the feature 
    set of SEO.
    """

    def __init__(self, config: dict, name: str):
        """ This creates a new server listening on a user-defined set of topics
        on the MQTT broker specified in config
        """

        # save config
        self.config = config
        self._name = name

        # initialize logging
        self._init_log()
        self.log('Creating new '+name+'...', 'green')

        # connect to MQTT broker
        self.client = self._connect()


    def topics(self) -> [str]:
        """ This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/seo/queue'] etc.
        """

        # USER MUST COMPLETE

        return []

    def process_message(self, msg: {str}) -> bool:
        """ This function is given a JSON dictionary message from the broker
        and must decide how to process the message given the application. 
        """

        # USER MUST COMPLETE

        return True


    def _connect(self) -> bool:
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

    
    def start(self):
        """ Starts the servers listening for new requests; server blocks
        on the specified port until it receives a request
        """
        self.client.on_message = self._process_message
        for topic in self.topics():
            self.client.subscribe(topic)
        self.client.loop_forever()

    
    def _process_message(self, client, userdata, msg) -> list:
        """ This function is called whenever a message is received.
        """
        msg = json.loads(msg.payload.decode())
        self.process_message(msg)


    def notify(self, content, to:str = None) -> bool:
        """ Send an email to the 'to' destination, with content 'content'
        """
        msg = {}
        msg['action'] = 'email'
        if to is None:
            msg['to'] = self.config['general']['email']
        else:
            msg['to'] = to
        msg['subject'] = self.config['mail']['subject']
        msg['content'] = content
        self.client.publish('/seo/notify', json.dumps(msg))
        
            
    def _init_log(self) -> bool:
        """ Initialize the object logging system - currently only opens
        the logging file
        """
        logname = self._name.replace(" ", "_").lower()
        logdir = self.config['queue']['dir']
        try:
            self.log_file = open(logdir+'/'+logname, 'a+')
        except:
            self.log('Unable to open log file', color='red')

        return True

    
    def log(self, msg: str, color: str='white') -> bool:
        """ Prints a log message to STDOUT. Returns True if successful, False
        otherwise.
        """
        colors = {'red':'31', 'green':'32', 'blue':'34', 'cyan':'36',
                  'white':'37', 'yellow':'33', 'magenta':'34'}
        logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        logname = self._name.upper()
        log = logtime+' '+logname+': '+msg
        color_log = '\033[1;'+colors[color]+'m'+log+'\033[0m'
        
        self.log_file.write(log+'\n')
        print(color_log)
        
        return True
