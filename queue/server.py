# This file implements a Server that listens for requests from Submit programs
# to add Sessions to the queue for tonight's imaging session
import time
import paho.mqtt.client as mqtt
import typing
import signal
import sys
import json
import yaml
import os
from os.path import dirname, realpath

class Server(object):
    """ This class represents a server that listens for queueing requests from 
    clients; once it has received a request, process_message() is called, which
    adds the request to the queue.
    """

    def __init__(self):
        """ This creates a new server listening on the specified port; this does
        not start the server listening, it just creates the server. start() must
        be called for the server to be initialized. 
        """

        ######################### IMPORT CONFIGURATION PARAMETERS ######################
        root_dir = dirname(dirname(realpath(__file__))) ## locate file containing config
        try:
            with open(root_dir+'/config.yaml', 'r') as config_file:
                try:
                    config = yaml.safe_load(config_file)
                except yaml.YAMLError as exception:
                    self.__log('Invalid YAML configuration file; '
                               'please check syntax.', 'red')
                    exit(-1)
        except:
            self.__log('Queue server unable to locate config.yaml; '
                       'please make sure that it exists.', 'red')
            exit(-1)
                    
        self.__log('Creating new queue server...', 'green')
        
        # the port to be used for communication
        self.port = config['mosquitto']['port']

        # whether we are enabled
        if config['queue']['default'] == 'on':
            self.enabled = True
        else:
            self.enabled = False

        # mqtt client to handle connection
        self.client = mqtt.Client()


        # connect to stone edge observatory
        try:
            self.client.connect(config['server']['host'], config['mosquitto']['port'], 60)
            self.__log('Successfully connected to Stone Edge Observatory!', color='green')
        except:
            self.__log('Unable to connect to Stone Edge Observatory. Please try again later. '
                     'If the problem persists, please contact <admin@stoneedgeobservatory.com>', 'red')
            exit(-1)

        # file name for JSON store
        qdir = config['queue']['dir']
        qname = config['queue']['name']+'_'
        currdate = time.strftime('%Y-%m-%d', time.gmtime())
        self.filename = root_dir+"/"+qdir+"/"+qname+currdate+"_imaging_queue.json"
        self.file = open(self.filename, 'w')
        if self.file is None:
            self.__log('Unable to open queue!', color='red')
        self.__log('Storing queue in %s' % self.filename)
        self.file.close()

        # create a handler for SIGINT
        signal.signal(signal.SIGINT, self.handle_exit)

        
    def handle_exit(self, signal, frame):
        """ SIGINT handler to check for Ctrl+C for quitting the server. 
        """
        self.__log('Are you sure you would like to quit [y/n]?', 'cyan')
        choice = input().lower()
        if choice == 'y':
            self.__log('Quitting server...', 'cyan')

            # if the file is open, close it
            if not self.file.closed:
                self.file.close()

            # disconnect from MQTT broker
            self.client.disconnect()
            sys.exit(0)

            
    def __del__(self):
        """ Called when the server is garbage collected - at this point, 
        this function does nothing.
        """
        pass

    
    def __log(self, msg: str, color: str = 'white') -> bool:
        """ Prints a log message to STDOUT. Returns True if successful, False
        otherwise.
        """
        colors = {'red':'31', 'green':'32', 'blue':'34', 'cyan':'36',
                  'white':'37', 'yellow':'33', 'magenta':'34'}
        logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        log = '\033[1;'+colors[color]+'m'+logtime+' SERVER: '+msg+'\033[0m'
        print(log)
        return True

    
    def enable(self) -> bool:
        """ Enable the queue server to start taking imaging requests
        """
        self.enabled = True

        
    def disable(self) -> bool:
        """ Disable the queue server from taking any requests. 
        """
        self.enabled = False


    def save_request(self, msg: str) -> list:
        """ This takes a raw message from process_message and writes the JSON data
        into the queue file. 
        """
        self.file = open(self.filename, 'a')
        self.file.write(json.dumps(msg)+'\n')
        self.file.close()

        
    def process_message(self, client, userdata, msg) -> list:
        """ This function is called whenever a message is received.
        """
        msg = json.loads(msg.payload.decode())
        ## we have received a new request from the queue
        if msg['type'] == 'request':
            self.__log('Adding new request to queue.')
            self.save_request(msg)
        ## change state of the server
        elif msg['type'] == 'state':
            if msg['action'] == 'enable':
                self.__log('Enabling queueing server...', color='cyan')
                self.enabled = True
            elif msg['action'] == 'disable':
                self.__log('Disabling queueing server...', color='cyan')
                self.enabled = False
            else:
                self.__log('Received invalid admin state message...', color='magenta')
        else:
            self.__log('Received unknown admin message...', color+'magenta')


    def start(self):
        """ Starts the servers listening for new requests; server blocks
        on the specified port until it receives a request
        """
        self.client.on_message = self.process_message
        self.client.subscribe('/seo/queue')
        self.client.loop_forever()

if __name__ == "__main__":
    s = Server()
    s.start()
