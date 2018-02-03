import httplib2
import os

from config import config
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import datetime

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/atlas-calendar.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'config/client_secret.json'
APPLICATION_NAME = 'Atlas'

class Calendar(object):
    """ Manages API access to Google Calendar for queue scheduling
    and booking checks.
    """

    def __init__(self):
        """ Initialize the Calendar object. 
        """
        # the service object needed to make requests
        self.service = None

        # connect and authorize our access
        self.connect()


    def get_credentials(self):
        """ Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        credential_path = os.path.join(os.getcwd(), '/../config/atlas-calendar.json')

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            credentials = tools.run_flow(flow, store, None)
            print('Storing credentials to ' + credential_path)
        return credentials

    def connect(self):
        """ Authorize and connect to the Google Calendar API 
        """
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        self.service = discovery.build('calendar', 'v3', http=http)

    def get_events(self, start: datetime.datetime, end: datetime.datetime):
        """ Return a list of all calendar events between start and end times. 
        """
        eventsResult = self.service.events().list(
            calendarId=config.queue.calendar,
            timeMin=start.isoformat()+'Z', timeMax=end.isoformat()+'Z',
            singleEvents=True,
            orderBy='startTime').execute()
        return eventsResult.get('items', [])
