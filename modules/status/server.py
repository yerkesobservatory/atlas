import os
import paramiko
import logging
import colorlog
import scp as SCP
from imqueue import database
from typing import Dict
from config import config
from modules.template import base

class StatusServer(base.MQTTServer):
    """
    This server updates the Telescope status in MongoDB to allow
    the webapp to get access to Telescope operation.
    """

    def __init__(self):
        """
        We initialize the super class (which handles all MQTT configuration)
        and start listening.
        """

        # MUST INIT SUPERCLASS FIRST
        super().__init__("Status Server")

        self.log.info("Attempting to connect to database...")

        # get a connection to the database
        self.db = database.Database()

        # MUST END WITH start() - THIS BLOCKS
        self.log.info('Status Server starting to listen to MQTT messages...')
        self.start()


    def topics(self) -> [str]:
        """ This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/seo/queue'] etc.
        """

        return ['/'.join(['', config.mqtt.root, 'telescope'])]


    def process_message(self, topic: str, msg: Dict[str, str]):
        """ This function is given a JSON dictionary message from the broker
        and must decide how to process the message given the servers purpose. This
        is automatically called whenever a message is received
        """
        if topic.split('/')[-1] == 'telescope':
            self.handle_telescope_msg(msg)

        return

    def handle_telescope_msg(self, msg: Dict[str, str]):
        """ Handle and process messages received on the telescopee
        topic.
        """
        event = msg.get('event')
        name = config.general.name # telescope name
        if event == 'opening':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'slit': 'opening', 'status': 'opening'}})
        elif event == 'openup':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'slit': 'open', 'status': 'open'}})
        elif event == 'closing':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'slit': 'closing', 'status': 'closing'}})
        elif event == 'closedown':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'slit': 'closed', 'status': 'closed'}})
        elif event == 'filterchange':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'filter': 'changing'}})
        elif event == 'filter':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'filter': msg.get('filter')}})
        elif event == 'focus':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'focus': msg.get('focus')}})
        elif event == 'slew':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'location': msg.get('location'),
                                                    'status': 'slewing'}})
        elif event == 'point':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'location': msg.get('location'),
                                                    'location': 'open'}})
        elif event == 'lock':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'lock': msg.get('username')}})
        elif event == 'unlock':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'lock': None}})
        elif event == 'wait':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'wait': msg.get('wait'),
                                                    'status': 'sleeping'}})
        elif event == 'wake':
            slit = self.db.telescopes.find_one({'name': name}).get('slit')
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'wait': 0,
                                                    'status': slit}})
        elif event == 'weather':
            weather = {'sun': msg.get('sun'), 'moon': msg.get('moon'),
                       'rain': msg.get('rain'), 'cloud': msg.get('cloud'),
                       'dew': msg.get('dew')}
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'weather': weather}})
        elif event == 'exposing':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'status': 'exposing',
                                                    'progress': 0}})
        elif event == 'exposure':
            self.db.telescopes.update_one({'name': name},
                                          {'$set': {'status': 'open',
                                                    'progress': 100}})
        else:
            self.log.warning('Unknown telescope event message')

        return

    def close(self):
        """ This function is called when the server receives a shutdown
        signal (Ctrl+C) or SIGINT signal from the OS. Use this to close
        down open files or connections.
        """

        # USER [OPTIONAL]

        return
