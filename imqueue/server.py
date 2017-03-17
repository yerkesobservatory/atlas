# This file implements a Server that listens for requests from Submit programs
# to add Sessions to the queue for tonight's imaging session
import sys
import os
import threading
import multiprocessing
import typing
import json
import paho.mqtt.client as mqtt
import maya
from . import executor

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

        self.log('Creating new queue server...', 'green')
        self.config = config

        # the time (in UTC) to start observing
        self.start_time = self.config.get('queue').get('start_time') or "02:00"

        # whether we are enabled by default
        self.enabled = (self.config.get('queue').get('default') == True)

        # connect to MQTT broker
        self.client = self.connect()

        # find queue file and its date
        self.queue_dir = self.config.get('queue').get('dir') or '.'
        self.queue_file, self.queue_date = self.find_queue()

        if self.queue_file is not None:
            # start the countdown timer for execution
            self.start_timer()

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
                if len(split_name) >= 4 and split_name[3] == 'queue':

                    # check its date
                    date = maya.parse(split_name[1]+self.start_time)

                    # if it's earlier than earliest
                    if date < queue_date and date > maya.now():
                        queue_date = date
                        queue_file = f

            # we need to execute after first iteration
            # so we don't keep walking the file system recursively
            break

        return queue_file, queue_date

    
    def start_timer(self):
        """ This starts a countdown timer for the execution of the queue;
        when this timer triggers, the exeutor is started.
        """
        # calculate time at which we start the executor
        exec_time = maya.when(self.queue_date+" "+self.start_time)
        delta_time = (exec_time.datetime() - maya.now().datetime()).total_seconds

        # create timer to start executor in delta_time
        self.timer = threading.Timer(delta_time, self.start_executor)


    def start(self):
        """ Starts the servers listening for new requests; server blocks
        on the specified port until it receives a request
        """
        self.client.on_message = self.process_message
        topic = '/'+self.config.get('general').get('name')+'/queue'
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
            filename = '_'.join([name, date, 'imaging_queue.json'])
            with open(self.queue_dir+'/'+filename, 'w+') as f:
                f.write('# IMAGING QUEUE FOR {} CREATED ON {}'.format(date, maya.now()))

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
            queue_exec = executor.Executor(self.queue_file)
            exec_proc = multiprocessing.Process(target=queue_exec.start())
            exec_proc.start()
            self.log('Started executor with pid={}'.format(exec_proc.pid), 'green')


        # import the new queue
        self.queue_file, self.queue_date = self.find_queue()

        # start a new timer for the next queue
        self.start_timer()


    @staticmethod
    def log(msg: str, color: str='white') -> bool:
        """ Prints a log message to STDOUT. Returns True if successful, False
        otherwise.
        """
        colors = {'red':'31', 'green':'32', 'blue':'34', 'cyan':'36',
                  'white':'37', 'yellow':'33', 'magenta':'34'}
        logtime = maya.now().datetime(to_timezone="UTC").strftime('%Y-%m-%d %H:%M:%S')
        log = '\033[1;'+colors[color]+'m'+logtime+' SERVER: '+msg+'\033[0m'
        print(log)
        return True
