import paho.mqtt.client as mqtt
import telescope
import json

def on_connect(client, userdata, flags, rc):
    """ This function handles subscribing to the appropriate MQTT topics
    as well as establishing other setup procedures. 
    """

    client.subscribe('/seo/request')
    client.subscribe('/seo/control')


def on_message(client, userdata, msg):
    """ This function is called whenever a message is received. 
    """
    message = json.loads(msg.payload.decode())

    if msg.topic == '/seo/request':

        # request for new weather data
        if message['type'] == 'weather':
            update_weather(client, telescope)
        if message['type'] == 'dome':
            update_dome(client, telescope)

                
def update_weather(client, telescope):
    """ Publish the latest weather data to /seo/request.
    """
    weather = telescope.get_weather()
    if weather is not None:

        # check whether this is OK
        weather_ok = telescope.weather_ok()
        if weather_ok is True:
            weather['ok': True]
        else:
            weather['ok': False]

            # publish results to topic
            client.publish('/seo/status/', json.dumps(weather))
            return True

    return False


# def dome_open():
#     """ Returns true if the dome is open, or false if it is closed.
#     """
#     status = telescope.dome_open()
#     if status is True:
#         return flask.jsonify({'status':'open'})
#     elif status is False:
#         return flask.jsonify({'status':'closed'})
#     else:
#         flask.abort(503)

# @app.route('/status/target_visible/<string:target>', methods=['GET'])
# def target_visible(target):
#     """ Indicates whether a given target is visible.
#     """
#     # status = telescope.target_visible(target)
#     status = True
#     if status is True:
#         return flask.jsonify({target:'true'})
#     elif status is False:
#         return flask.jsonify({target:'false'})
#     else:
#         flask.abort(503)

# @app.route('/control/open_dome', methods=['POST'])
# def open_dome():
#     """ Opens the dome. 
#     """
#     status = telescope.open_dome()
#     if status is True:
#          return flask.jsonify({'open_dome':'success'})
#     else:
#         flask.abort(503)

        

if __name__ == "__main__":
    ## CREATE TELESCOPE 
    telescope = telescope.Telescope()

    #################### CREATE CLIENT ####################
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    ## connect to local mosquitto instance
    client.connect('localhost',  1883, 60)

    # start receiving messages
    client.loop_forever()
