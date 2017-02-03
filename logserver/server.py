# This file subscribes to all topics and writes a detailed log of every message to
# a log file
import time
import paho.mqtt.client as mqtt
import typing
import signal
import sys
import json
import yaml
import os
from os.path import dirname, realpath

class LogServer(object):
    """ This class represents a server that subscribes to messages from every
    topic; once it has received a request, process_message() is called, which
    writes the message to a log file
    """

    def __init__(self, config: dict):
        """ This creates a new server listening on the specified port; this does
        not start the server listening, it just creates the server. start() must
        be called for the server to be initialized.
        """

        self.log('Creating new log server...', 'green')

        # mqtt client to handle connection
        self.client = mqtt.Client()

        # connect to message broker
        try:
            self.client.connect(config['server']['host'], config['mosquitto']['port'], 60)
            self.log('Successfully connected to '+config['general']['name'], color='green')
        except:
            self.log('Unable to connect to '+config['general']['name']+'. Please try again later. '
                     'If the problem persists, please contact '+config['general']['email'], 'red')
            print(sys.exc_info())
            exit(-1)

        # file name for JSON log
        qdir = config['logging']['dir']
        qname = config['logging']['name']+'_'
        rootdir = config['rootdir']
        currdate = time.strftime('%Y-%m-%d', time.gmtime())
        self.filename = rootdir+"/"+qdir+"/"+qname+currdate+"_all_messages.json"
        self.file = open(self.filename, 'a')
        if self.file is None:
            self.log('Unable to open log file!', color='red')
        self.log('Storing logs in %s' % self.filename)


    def __del__(self):
        """ Called when the server is garbage collected - at this point, 
        this function does nothing.
        """
        pass


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
        self.file.write(msg.topic+": ")
        self.file.write(msg.payload.decode()+'\n')
        self.log(msg.topic+": "+msg.payload.decode())


    def run(self):
        """ Starts the servers listening for new requests; server blocks
        on the specified port until it receives a request
        """
        self.client.on_message = self.process_message
        self.client.subscribe('/seo/status')
        self.client.subscribe('/seo/telescope')
        self.client.subscribe('/seo/pipeline')
        self.client.subscribe('/seo/queue')
        self.client.loop_forever()
