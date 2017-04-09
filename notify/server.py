""" This server process listens for notification requests, processes their messages, and emails
the appropriate email address with the time, date, error message, and other relevant information. 
"""
import time
import typing
import smtplib
import email

import slackclient

from templates import mqtt

class NotificationServer(mqtt.MQTTServer):
    """ This class represents a server that listens for notification requests on
    /seo/notify and emails these messages to the destination
    """
    def __init__(self, config: {str}):
        """ Initializes mail construct and starts server
        """

        # MUST INIT SUPERCLASS FIRST
        super().__init__(config, "Notification Server")

        # create Slack client
        self.sc = slackclient.SlackClient(config['general'].get('slack-token'))

        # MUST END WITH start() - THIS BLOCKS
        self.start()


    def topics(self) -> [str]:
        """ This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/seo/queue'] etc.
        """

        prefix = '/'+self.config['general']['shortname']+'/'
        return [prefix+'notify']

    
    def process_message(self, topic: str, msg: {str}) -> bool:
        """ This function is given a JSON dictionary message from the broker
        and must decide how to process the message given the servers purpose. This
        is automatically called whenever a message is received
        """

        if msg.get('type') == 'notify':
            if msg.get('action') == 'email':
                self.send_email(msg)
            elif msg.get('action') == 'slack':
                self.publish_slack(msg)
            else:
                self.log('Unknown message received', color='magenta')
        else:
            self.log('Unknown message received', color='magenta')

        return True


    def send_email(self, msg: {str}) -> bool:
        """ Sends email given the parameters in msg. 
        """
        s=smtplib.SMTP(self.config['mail']['server'])

        # construct the message
        message = email.message.EmailMessage()
        message.set_content(msg.get('content'))
        message['Subject'] = msg.get('subject')
        message['From'] = self.config.get('mail').get('username')
        message['To'] = msg.get('to')

        # make a TLS connection
        s.starttls()

        # login using provided username and password
        s.login(self.config['mail']['username'], self.config['mail']['password'])

        # send the email and quit
        s.send_message(message)
        s.quit()
        

    def publish_slack(self,  msg: {str}) -> bool:
        """ Publish `msg` to the Slack channel `channel`. 
        'channel' can be group channels #queue or users @rprechelt
        """
        channel = msg.get('channel') or '#queue'
        content = msg.get('content') or ''

        self.sc.api_call("chat.postMessage",
            channel=channel,
            text=content,
            username="sirius", as_user="false")

        # we cannot send more than one message a second
        # let MQTT build a queue for us
        time.sleep(1.1)

        return True
