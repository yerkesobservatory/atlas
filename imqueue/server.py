# This file implements a Server that listens for requests from Submit programs
# to add Sessions to the queue for tonight's imaging session
import paho.mqtt.client as mqtt
import typing
import sys
import json
import os
import maya
import threading
import executor

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

        # the time (in Sonoma) to start observing
        self.start_time = "17:00"

        # whether we are enabled
        if config['queue']['default'] == 'on':
            self.enabled = True
        else:
            self.enabled = False

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

        # get list of all files in queue dir
        qdir = config['queue']['dir']
        files = []
        for (_, _, filenames) in os.walk(qdir):
            files.extend(filenames)
            break

        # extract only valid queue dates
        dates = []
        for f in files:
            splitname = f.split('_')
            if len(splitname) >= 3:
                if splitname[2] == 'imaging':
                    dates.append(maya.parse(splitname[1]))


        # file parameters
        self.qdir = config['queue']['dir']
        self.qname = config['queue']['name']+'_'
        self.rootdir = config['rootdir']

        # there are no queue files
        if len(dates) == 0:
            self.qfilename = None
            self.queue = []
        else: # open the latest queue file
            # sort by date
            dates.sort()

            # pick earliest date
            self.qdate = dates[0].datetime(to_timezone="UTC").strftime('%Y-%m-%d')

            qfilename = self.rootdir+"/"+self.qdir+"/"
            qfilename += self.qname+self.qdate+"_imaging_queue.json"
            self.qfilename = qfilename

            # try and open queue - file should already exist
            try:
                self.queue = open(self.qfilename, 'a')
                self.log('Storing queue in %s' % self.qfilename)
                self.queue.close()
            except:
                self.log('Unable to open queue!', color='red')

        # calculate time to start executing, and time now
        exec_time = maya.when(self.qdate+" "+self.start_time, timezone="PST")
        now = maya.now()
        delta_time = (exec_time.datetime() - now.datetime()).total_seconds

        # create timer to start executor in delta_time
        timer = threading.Timer(delta_time, self.start_executor)


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
        logtime = maya.now().datetime(to_timezone="UTC").strftime('%Y-%m-%d %H:%M:%S')
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


    def save_request(self, msg: str) -> bool:
        """ This takes a raw message from process_message and writes the JSON data
        into the queue file.
        """
        self.log('Adding new request from {} to queue.'.format(msg['user']))
        self.queue = open(self.qfilename, 'a')
        self.queue.write(json.dumps(msg)+'\n')
        self.queue.close()

        return True

    def create_queue(self, msg: str) -> bool:
        """ This takes a raw message from process_message and writes the JSON data
        into the queue file.
        """
        qfilename = self.rootdir+"/"+self.qdir+"/"
        qdate = msg['date'].datetime(to_timezone="UTC").strftime('%Y-%m-%d')
        qfilename += self.qname+qdate+"_imaging_queue.json"

        # try and open file
        try:
            self.queue = open(qfilename, 'w')
            self.queue.close()
        except:
            self.log('Unable to open new queue for {}!'.format(date), color='red')

        return True


    def update_state(self, msg: str) -> bool:
        """ This takes a raw message from process_message and updates
        the internal server state
        """
        if msg['action'] == 'enable':
            self.log('Enabling queueing server...', color='cyan')
            self.enabled = True
        elif msg['action'] == 'disable':
            self.log('Disabling queueing server...', color='cyan')
            self.enabled = False
        else:
            self.log('Received invalid queue state message...', color='magenta')


    def process_message(self, client, userdata, msg) -> list:
        """ This function is called whenever a message is received.
        """
        msg = json.loads(msg.payload.decode())
        ## we have received a new request from the queue
        if msg['type'] == 'request':
            self.save_request(msg)
        ## create new queue for future date
        if msg['type'] == 'create':
            self.create_queue(msg)
        ## change state of the server
        elif msg['type'] == 'state':
            self.update_state(msg)
        else:
            self.log('Received unknown queue message...', color+'magenta')


    def run(self):
        """ Starts the servers listening for new requests; server blocks
        on the specified port until it receives a request
        """
        self.client.on_message = self.process_message
        self.client.subscribe('/seo/queue')
        self.client.loop_forever()

    def start_executor(self):
        """ This starts a new executor to execute one session
        file. Must be started asynchronously as it takes hours
        to execute.
        """
        new_exec = executor.Executor(self.qfilename)
        new_exec.execute_queue()
