# This file implements a Server that listens for requests from Submit programs
# to add Sessions to the queue for tonight's imaging session

import os
import json
import datetime
import threading

import maya
import sqlalchemy

from templates import mqtt
from imqueue import executor
from db.models import Night


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

        # create connection to database
        self.engine = sqlalchemy.create_engine(config['database']['address'], echo=False)

        # create session to database with engine
        session_maker = sqlalchemy.orm.sessionmaker(bind=self.engine)
        self.dbsession = session_maker()
        self.log("Succesfully connected to the queue database")

        # MUST END WITH start() - THIS BLOCKS
        self.start()


    def topics(self) -> [str]:
        """ This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/seo/queue'] etc.
        """

        return ['/'+self.config.get('general').get('shortname')+'/queue']


    def start_timer(self):
        """ This starts a countdown timer for the execution of the queue;
        when this timer triggers, the exeutor is started.
        """

        if delta_time < (60*60*24*30*12):
            # create timer to start executor in delta_time
            self.timer = threading.Timer(delta_time, self.start_executor)
            self.log('Starting timer; queue will start at {}'.format(self.exec_time))
            self.timer.start()
        else:
            self.log('Queue date is too far in the past or future', color='red')


    def enable_queue(self, msg: dict) -> bool:
        """ This takes a raw message from process_message and enables the 
        queue on the date and time given in the message
        """
        date = msg.get('date')
        if date is None:
            return False

        # convert to date object
        date = maya.parse(date).datetime().date()

        # convert to time object
        start_time = msg.get('start_time') or self.config['queue']['start_time']
        start_time = maya.parse(start_time).datetime().time()

        # convert to time object
        end_time = msg.get('end_time') or self.confg['queue']['end_time']
        end_time = maya.parse(end_time).datetime().time()

        # create observing night
        night = Night(date=date, start_time=start_time, end_time=end_time)

        try:
            # add to database
            self.dbsession.add(night)
            self.dbsession.commit()
        except sqlalchemy.exc.IntegrityError:
            self.log('Queue is already enabled for that date.', color='cyan')

        self.log("Successfully enabled queue for {}".format(date))

        return True

    
    def process_message(self, topic, msg) -> list:
        """ This function is called whenever a message is received.
        """

        ## we have received a new request from the queue topic
        msg_type = msg.get('type')
        if msg_type == 'enable':
            self.enable_queue(msg)

        # something we don't understand
        else:
            self.log('Received unknown queue message...', color='magenta')


    def start_executor(self):
        """ This starts a new executor to execute one session
        file. 
        """
        
        msg = {}
        msg['type'] = 'start'
        self.publish('/seo/executor', msg)

        
    def close(self):
        """ This function is called when the server receives a shutdown
        signal (Ctrl+C) or SIGINT signal from the OS. Use this to close
        down open files or connections. 
        """

        return 
