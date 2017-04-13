import time
import json
import atexit
import typing

import paho.mqtt.client as mqtt

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

        # set the name of the component
        self.__name = name

        # initialize the logging system
        self.__init_log()

        # connect to MQTT broker
        self.client = self.__connect()
        self.log('Creating new '+name+'...', 'green')

        # register atexit handler
        atexit.register(self.__handle_exit)


    def topics(self) -> [str]:
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
            self.log('Successfully connected to '+name, color='green')
        except Exception as e:
            self.log('Unable to connect to '+name+'. Please try again later. '
                     'If the problem persists, please contact '+email, 'red')
            self.log(str(e))
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

    
    def __process_message(self, client, userdata, msg) -> list:
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
        msg = {}
        msg['action'] = 'email'
        msg['to'] = to or config.notification.sysadmin
        msg['subject'] = config.notification.subject
        msg['content'] = content

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
        msg = {}
        msg['type'] = 'notify'
        msg['action'] = 'slack'
        msg['content'] = content
        msg['channel'] = channel or config.notification.slack_channel

        notify = '/'.join(('', config.general.shortname, 'notify'))
        # publish message to notification server
        self.publish(notify, msg)

        return True
        
            
    def __init_log(self) -> bool:
        """ Initialize the logging system.

        This function currently only opens a file
        in the system log directory that later functions
        write to. 
        """
        logname = self.__name.replace(' ', '_').lower()
        logdir = config.server.logdir
        try:
            self.log_file = open(logdir+'/'+logname+'.log', 'a+')
        except Exception as e:
            self.log_file = None
            self.log('Unable to open log file! Disabling log file writes...', color='red')
            self.log(str(e), color='red')

        return True

    
    def __handle_exit(self, *_) -> bool:
        """ Cleanup resources on program exit. 

        This method is registered with atexit which calls
        this function during program exit. This handles some
        behind the scene cleanup as well as call the user 
        close function.
        """
        self.log('Closing down...', 'cyan')

        success = False
        try:
            # call user close function
            success = self.close()

            if self.log_file is not None:
                # close log file
                self.log_file.close()

            # close MQTT connection
            self.client.disconnect()
        except Exception as e:
            self.log(e)
            exit(1)
        finally:
            # quit the process
            exit(success)
        
    
    def log(self, msg: str, color: str='white') -> None:
        """ Log a message to the logging system. 

        This prints a colorized version to STDOUT, and writes
        a plaintext version to the modules log file. Available colors
        are: red, green, blue, cyan, white, yellow, magenta. 
        The default color is white. 
        """
        colors = {'red':'31', 'green':'32', 'blue':'34', 'cyan':'36',
                  'white':'37', 'yellow':'33', 'magenta':'34'}
        logtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        logname = self.__name.upper()
        log = logtime+' '+logname+': '+msg
        color_log = '\033[1;'+colors[color]+'m'+log+'\033[0m'

        if self.log_file is not None:
            self.log_file.write(log+'\n')
            self.log_file.flush()
        print(color_log)
