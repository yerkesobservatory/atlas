import paramiko
import flask
import Telescope

app = flask.Flask("TelescopeServer")

telescope = Telescope.Telescope()

@app.route('/status/weather', methods=['GET'])
def get_weather():
    """ Return all available weather data from the telescope. 
    """
    weather = telescope.get_weather()
    if weather is not None:
        return flask.jsonify(weather)
    else:
        flask.abort(503)

@app.route('/status/weather_ok', methods=['GET'])
def weather_ok():
    """ Indicates whether the weather is currently OK.
    """
    weather = telescope.weather_ok()
    if weather is not None:
        return flask.jsonify({'weather':'ok'})
    else:
        flask.abort(503)

@app.route('/status/dome_open', methods=['GET'])
def dome_open():
    """ Returns true if the dome is open, or false if it is closed.
    """
    status = telescope.dome_open()
    if status is True:
        return flask.jsonify({'status':'open'})
    elif status is False:
        return flask.jsonify({'status':'closed'})
    else:
        flask.abort(503)

@app.route('/status/target_visible/<string:target>', methods=['GET'])
def target_visible(target):
    """ Indicates whether a given target is visible.
    """
    # status = telescope.target_visible(target)
    status = True
    if status is True:
        return flask.jsonify({target:'true'})
    elif status is False:
        return flask.jsonify({target:'false'})
    else:
        flask.abort(503)

@app.route('/control/open_dome', methods=['POST'])
def open_dome():
    """ Opens the dome. 
    """
    status = telescope.open_dome()
    if status is True:
         return flask.jsonify({'open_dome':'success'})
    else:
        flask.abort(503)

        

if __name__ == "__main__":
    app.run(debug=True)
