# This file implements a Server that listens for requests from Submit programs
# to add Sessions to the queue for tonight's imaging session

import os
import threading
import multiprocessing
import maya
import json
from templates import mqtt
from imqueue import executor

class QueueServer(mqtt.MQTTServer):
    """ This class represents a server that listens for queueing requests from
    clients; once it has received a request, process_message() is called, which
    adds the request to the queue.

    It can also be used to enable/disable the queue, as well as to enable the queue
    for future observing dates.
    """

    def __init__(self, config: {str}):
        """ This finds the latest queue file (if it exists), 
        and assigns it as the servers queue.
        """

        # MUST INIT SUPERCLASS FIRST
        super().__init__(config, "Queue Server")

        # the time (in UTC) to start observing
        self.start_time = (self.config.get('queue').get('start_time') or "02:00")

        # whether we are enabled by default
        self.enabled = (self.config.get('queue').get('default') == True)

        # find queue file and its date
        self.queue_dir = self.config.get('queue').get('dir') or '.'
        self.queue_file, self.queue_date = self.find_queue()

        # start the countdown timer for execution
        if self.queue_file is not None:
            self.log('Initializing queue server with queue on {}'.format(self.queue_date), color='green')
            self.start_timer()
        else:
            self.log('Initializing queue server without any queue', color='green')

        # MUST END WITH start() - THIS BLOCKS
        self.start()


    def topics(self) -> [str]:
        """ This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/seo/queue'] etc.
        """

        return ['/'+self.config.get('general').get('shortname')+'/queue']


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
        if self.queue_file is None or self.queue_date is None:
            self.log('Received a request but queue is disabled. Discarding...', color='magenta')
            return False
        else:
            self.log('Adding new request from {} to queue.'.format(msg.get('user')))
            print(self.queue_dir+'/'+self.queue_file)
            with open(self.queue_dir+'/'+self.queue_file, 'a+') as f:
                f.write(json.dumps(msg)+'\n')
                self.log(json.dumps(msg))
                f.flush()

            return True

    
    def create_queue(self, msg: dict) -> bool:
        """ This takes a raw message from process_message and writes the JSON data
        into the queue file.
        """
        name = self.config.get('general').get('shortname')
        date = msg.get('date') or None
        if date is not None:
            filename = '_'.join([date.replace('/', '-'), name, 'imaging_queue.json'])
            self.log('Saving queue in file: {}'.format(self.queue_dir+'/'+filename))
            with open(self.queue_dir+'/'+filename, 'w+') as f:
                f.write('# IMAGING QUEUE FOR {} CREATED ON {}\n'.format(date, maya.now()))
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


    def process_message(self, msg) -> list:
        """ This function is called whenever a message is received.
        """

        ## we have received a new request from the queue topic
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
        dest = queue.replace('json', '_started.json')
        subprocess.call(['mv', queue, dest])
        
        # import the new queue
        self.queue_file, self.queue_date = self.find_queue()
        print(self.queue_file, self.queue_date)

        # start a new timer for the next queue
        self.start_timer()

        
    def close(self):
        """ This function is called when the server receives a shutdown
        signal (Ctrl+C) or SIGINT signal from the OS. Use this to close
        down open files or connections. 
        """

        try:
            self.queue_file.close()
        except Exception as e:
            self.log("Encountered error while shutting down")
            
        return 
