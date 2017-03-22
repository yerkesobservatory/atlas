""" This server process listens for notification requests, processes their messages, and emails
the appropriate email address with the time, date, error message, and other relevant information. 
"""

import typing
import smtplib
import email
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


        # MUST END WITH start() - THIS BLOCKS
        self.start()


    def topics(self) -> [str]:
        """ This function must return a list of topics that you wish the server
        to subscribe to. i.e. ['/seo/queue'] etc.
        """

        prefix = '/'+self.config['general']['shortname']+'/'
        return [prefix+'notify']

    
    def process_message(self, msg: {str}) -> bool:
        """ This function is given a JSON dictionary message from the broker
        and must decide how to process the message given the servers purpose. This
        is automatically called whenever a message is received
        """

        if msg['action'] == 'email' and msg.get('to') is not None:
            self.send_email(msg)
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
        
