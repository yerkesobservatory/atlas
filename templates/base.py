import time
import json
import atexit
import logging
import colorlog
import paho.mqtt.client as mqtt
from typing import List
from config import config


class AtlasServer(object):
    """ This class represents a general purpose server that interacts with an Atlas
    ecosystem; subclasses of this server are able to easily extend the feature 
    set of Atlas-controlled telescopes.
    """
    
    def __init__(self, name: str):
        """ This creates a new server listening on a user-defined set of topics
        on the MQTT broker specified in config
        """
        # save log of telescope
        self.__name = name

        # initialize logging system
        self.__init_log()

        # connect to MQTT broker
        self.client = self.__connect()
        self.log.info(f'Creating new {name}...')

        # register atexit handler
        atexit.register(self.__handle_exit)

    @staticmethod
    def topics() -> List[str]:
        """ Returns the topics the server will be subscribed to.

        This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/atlas/queue'] etc.
        """

        # USER MUST COMPLETE

        return []

    def process_message(self, topic: str, msg: dict) -> None:
        """ This function is given a dictionary message from the broker
        and must decide how to process the message. 
        """
        # USER MUST COMPLETE

    def close(self) -> bool:
        """ This function is called during close down; use this to close
        any resources that you have opened. 

        This is called by the atexit handler; only close files/connections
        that *you* opened. Return true if all went well (server will exit(0)), 
        or False if something went wrong (server will exit(1))
        """

        return True

    def publish(self, topic: str, message: dict) -> None:
        """ Publish a dictionary to a given topic. 

        This method converts the message to JSON and publishes
        it on the topic using the MQTT client. 
        """
        self.log.info(f'Publishing {message} to {topic}...')
        self.client.publish(topic, json.dumps(message))

    def __connect(self) -> mqtt.Client:
        """ Connect to an Atlas infrastructure. 

        This method establishes a MQTT connection to the broker. Runs
        exit(-1) if an exception was thrown while connecting to the 
        broker.
        """

        # mqtt client to handle connection
        client = mqtt.Client()

        # server information
        host = config.server.host 
        port = config.mosquitto.port
        name = config.general.name
        email = config.notification.sysadmin
        
        # connect to message broker
        try:
            client.connect(host, port, 60)
            self.log.info(f'Successfully connected to {name}')
        except Exception as e:
            self.log.critical(f'Unable to connect to {name}. Please try again later. '
                              f'If the problem persists, please contact {email}')
            self.log.critical(e)
            exit(-1)

        return client
    
    def start(self):
        """ Starts the servers listening for new requests; server blocks
        on the specified port until it receives a request
        """
        self.client.on_message = self.__process_message
        for topic in self.topics():
            self.client.subscribe(topic)
        self.client.loop_forever()

    def __process_message(self, client, userdata, msg):
        """ This function is called whenever a message is received on the broker.
        
        This function parses the message data, and passes the topic and decoded
        dictionary to the user process_message function. 
        """
        topic = msg.topic
        msg = json.loads(msg.payload.decode())
        self.process_message(topic, msg)

    def email(self, content, to:str = None) -> bool:
        """ Send an email to the 'to' destination, with content 'content'.
        
        This creates a notification message and sends it to the notification
        server via the MQTT broker. The notification server actually sends
        the email. 
        """
        # check if email is disabled
        if config.notification.email is False:
            return False

        # build the message to notification server
        msg = {'action': 'email', 'to': to or config.notification.sysadmin,
               'subject': config.notification.subject,
               'content': content}

        self.log.info(f'Sending email to {msg["to"]}...')
        notify = '/'.join(('', config.general.shortname, 'notify'))
        # publish message to notification server
        self.publish(notify, msg)

        return True

    def slack(self, content: str, channel: str = None) -> bool:
        """ Publish `content` to the Slack channel `channel`. 
        'channel' can be group channels '#queue' or users '@username'

        This creates a notification message and sends it to the notification
        server via the MQTT broker. The notification server actually publishes 
        to Slack. The notification server has built in rate-limiting so your
        slack message may not appear immediately. 
        """
        # check if slack is enabled
        if config.notification.slack is False:
            return False

        # build the message to notification server
        msg = {'type': 'notify', 'action': 'slack', 'content': content,
               'channel': channel or config.notification.slack_channel}

        self.log.info(f'Publishing message to {msg["to"]} on Slack...')
        notify = '/'.join(('', config.general.shortname, 'notify'))

        # publish message to notification server
        self.publish(notify, msg)

        return True
        
    def __handle_exit(self, *_) -> bool:
        """ Cleanup resources on program exit. 

        This method is registered with atexit which calls
        this function during program exit. This handles some
        behind the scene cleanup as well as call the user 
        close function.
        """
        self.log.info('Closing down...')

        success = False
        try:
            # call user close function
            success = self.close()

            # close up logging system for this module
            logging.shutdown()

            # close MQTT connection
            self.client.disconnect()
        except Exception as e:
            self.log.critical(e)
            exit(1)

    def __init_log(self) -> bool:
        """ Initialize the logging system for this module and set
        a ColoredFormatter. 
        """
        # create format string for this module
        format_str = config.logging.fmt.replace('[name]', self.__name.upper())
        formatter = colorlog.ColoredFormatter(format_str, datefmt=config.logging.datefmt)

        # create stream
        stream = logging.StreamHandler()
        stream.setLevel(logging.DEBUG)
        stream.setFormatter(formatter)

        # assign log method and set handler
        self.log = logging.getLogger(self.__name.lower())
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(stream)

        return True
