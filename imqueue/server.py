# This file implements a Server that listens for requests from Submit programs
# to add Sessions to the queue for tonight's imaging session
import sys
import os
import threading
import multiprocessing
import subprocess
import typing
import json
import time

import paho.mqtt.client as mqtt
import maya
from imqueue import executor


class QueueServer(object):
    """ This class represents a server that listens for queueing requests from
    clients; once it has received a request, process_message() is called, which
    adds the request to the queue.

    It can also be used to enable/disable the queue, as well as to enable the queue
    for future observing dates.
    """

    def __init__(self, config: dict):
        """ This creates a new server listening on the specified port; this does
        not start the server listening, it just creates the server. run() must
        be called for the server to be initialized.
        """

        # save config
        self.config = config

        # initialize logging
        self.init_log()
        self.log('Creating new queue server...', 'green')

        # the time (in UTC) to start observing
        self.start_time = (self.config.get('queue').get('start_time') or "02:00")

        # whether we are enabled by default
        self.enabled = (self.config.get('queue').get('default') == True)

        # connect to MQTT broker
        self.client = self.connect()

        # find queue file and its date
        self.queue_dir = self.config.get('queue').get('dir') or '.'
        self.queue_file, self.queue_date = self.find_queue()

        # start the countdown timer for execution
        if self.queue_file is not None:
            self.log('Initializing queue server with queue on {}'.format(self.queue_date), color='green')
            self.start_timer()
        else:
            self.log('Initializing queue server without any queue', color='green')

        # start!
        self.start()


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


    def find_queue(self) -> str:
        """ Searches queue_dir for all valid queue files,
        and returns the queue file that is chronologically next
        by date.

        TODO: this logic needs to be made more rigorous, uncertain
        about boundary conditions when the queue is started the same
        day as observation, and other odd situations (up for grabs!)
        """

        # set earliest date to far in future
        queue_date = maya.when('2100')
        queue_file = None

        # search through all files in queue directory
        for (_, _, files) in os.walk(self.queue_dir):

            # look at all the files
            for f in files:
                
                split_name = f.split('_')

                # if file is a queue
                if len(split_name) == 4 and split_name[3] == 'queue.json':

                    # check its date
                    try:
                        date = maya.parse(split_name[0]+' '+self.start_time+' UTC')
                    except:
                        continue
                    
                    # if it's earlier than earliest
                    if date < queue_date and date > maya.when('now', timezone='UTC'):
                        queue_date = date
                        queue_file = f

            # we need to execute after first iteration
            # so we don't keep walking the file system recursively
            break

        if queue_date != maya.when('2100'):
            return queue_file, queue_date
        else:
            return None, None

    
    def start_timer(self):
        """ This starts a countdown timer for the execution of the queue;
        when this timer triggers, the exeutor is started.
        """
        # calculate time at which we start the executor
        exec_time = maya.parse(self.queue_date.iso8601()[0:10]+' '+self.start_time+' UTC')
        delta_time = (exec_time.datetime() - maya.now().datetime()).total_seconds()

        if delta_time < (60*60*24*30*12):
            # create timer to start executor in delta_time
            self.timer = threading.Timer(delta_time, self.start_executor)
            self.timer.start()
        else:
            self.log('Queue date is too far in the past or future', color='red')


    def start(self):
        """ Starts the servers listening for new requests; server blocks
        on the specified port until it receives a request
        """
        self.client.on_message = self.process_message
        topic = '/'+self.config.get('general').get('shortname')+'/queue'
        self.client.subscribe(topic)
        self.client.loop_forever()

        
    def enable(self) -> bool:
        """ Enable the queue server to start taking imaging requests
        """
        self.enabled = True


    def disable(self) -> bool:
        """ Disable the queue server from taking any requests.
        """
        self.enabled = False


    def save_request(self, msg: str) -> bool:
        """ This takes a raw message from process_message and writes the JSON data
        into the queue file.
        """
        self.log('Adding new request from {} to queue.'.format(msg.get('user')))
        with open(self.queue_file, 'a') as f:
            f.write(json.dumps(msg)+'\n')

        return True

    
    def create_queue(self, msg: dict) -> bool:
        """ This takes a raw message from process_message and writes the JSON data
        into the queue file.
        """
        name = self.config.get('general').get('shortname')
        date = msg.get('date') or None
        if date is not None:
            filename = '_'.join([date.replace('/', '-'), name, 'imaging_queue.json'])
            with open(self.queue_dir+'/'+filename, 'w') as f:
                f.write('# IMAGING QUEUE FOR {} CREATED ON {}'.format(date, maya.now()))
                self.log('Creating image queue for {} on {}'.format(date, maya.now()), color='green')

            # if this is our first queue
            if self.queue_file is None:
                self.queue_file, self.queue_date = self.find_queue()
                self.start_timer()

        return True


    def update_state(self, msg: str) -> bool:
        """ This takes a raw message from process_message and updates
        the internal server state
        """
        if msg.get('action') == 'enable':
            self.log('Enabling queueing server...', color='cyan')
            self.enable()

        elif msg.get('action') == 'disable':
            self.log('Disabling queueing server...', color='cyan')
            self.disable()

        else:
            self.log('Received invalid queue state message...', color='magenta')


    def process_message(self, client, userdata, msg) -> list:
        """ This function is called whenever a message is received.
        """
        msg = json.loads(msg.payload.decode())

        ## we have received a new request from the queue
        msg_type = msg.get('type')
        if msg_type == 'request':
            self.save_request(msg)

        ## create new queue for future date
        elif msg_type == 'create':
            self.create_queue(msg)

        ## change state of the server
        elif msg_type == 'state':
            self.update_state(msg)

        else:
            self.log('Received unknown queue message...', color='magenta')


    def start_executor(self):
        """ This starts a new executor to execute one session
        file. Must be started asynchronously as it takes hours
        to execute.
        """
        if self.enabled is True:
            queue = self.queue_dir+'/'+self.queue_file
            queue_exec = executor.Executor(queue, self.config)
            exec_proc = multiprocessing.Process(target=queue_exec.start())
            exec_proc.start()
            self.log('Started executor with pid={}'.format(exec_proc.pid), 'green')


        # append _completed to queue file
        dest = queue.replace('json', '_completed.json')
        subprocess.call(['mv', queue, dest])
        
        # import the new queue
        self.queue_file, self.queue_date = self.find_queue()
        print(self.queue_file, self.queue_date)

        # start a new timer for the next queue
        self.start_timer()

        
    def init_log(self) -> bool:
        """ Initialize the object logging system - currently only opens
        the logging file
        """
        name = self.config.get('general').get('shortname') or 'atlas'
        try:
            self.log_file = open('/var/log/'+name+'/imqueue_server.log', 'a')
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
        log = logtime+' QUEUE SERVER: '+msg
        color_log = '\033[1;'+colors[color]+'m'+log+'\033[0m'
        self.log_file.write(log+'\n')
        print(color_log)
        return True
