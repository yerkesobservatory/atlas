## This file provides direct real-time control of the telescope using WebSockets; this will
## used by the GUI, and other apps, for real-time telescope control.

import websockets
import asyncio
import telescope.telescope as telescope
import paho.mqtt.client as mqtt

class TelescopeServer(object):
    """ This class provides a websocket connection to allow for control
    of the telescope.
    """

    def __init__(self, config: dict):

        # save config as self
        self.config = config

        # the primary telescope connection used for NON-real-time requests
        self.telescope = telescope.Telescope(dryrun=config['debug']['dryrun'])

        # the list of connected websockets
        self.connected = set()

        # whether the telescope has been locked
        self.locked = False

        # email of user who has locked telescope
        self.user = None

        # connection to MQTT broker
        self.client = mqtt.Client()
        self.client.connect(config['server']['host'], config['mosquitto']['port'], 60)


    async def handle_wsocket(self, websocket, path):
        """ Handles websocket connection from initialization to removal.
        This is called asychronously for each connection.
        """
        # add the websocket to the list of connected socket
        self.connected.add(websocket)

        # while the connection is active
        while True:
            try:
                # receive messages on websocket
                msg = await websocket.recv()
                print(msg)

                # send reply on websocket
                # await websocket.send(greeting)
                self.client.publish('/seo/telescope', "Sending message on WS")

            finally: # this happens when the connection is closed
                self.client.publish('/seo/telescope', "Hello from remove!")

                # remove connection from list of connected
                self.connected.remove(websocket)

                break


    def run(self):
        """ Starts the websocket server and prepares the server to start
        receiving new telescope control connections.
        """

        # start the webscket connection
        start_server = websockets.serve(self.handle_wsocket, 'localhost',
                                        self.config['server']['websocket_port'])

        # start server
        asyncio.get_event_loop().run_until_complete(start_server)

        # continuosly wait for new connections
        asyncio.get_event_loop().run_forever()
