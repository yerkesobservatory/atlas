import io
import flask
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict
from routines import plots
from config import config

class ResourceServer(object):
    """ This class is a REST endpoint designed to serve custom files (primary plots and images)
    for the Meteor web app.
    """

    def __init__(self):
        """ We create the app, register routes, and runz.
        """

        # create the Flask app
        app = flask.Flask("Resource Server")

        @app.route('/visibility/<string:target>', methods=['GET'])
        def visibility(target: str, **kwargs) -> Dict[str, str]:
            return self.visibility(target, **kwargs)

        # start it
        app.run(host='0.0.0.0', port=config.queue.resource_port)

    def visibility(self, target: str) -> Dict[str, str]:
        """ This endpoint produces a visibility curve (using code in /routines)
        for the object provided by 'target', and returns it to the requester.
        """
        fig = plots.visibility_curve(target, figsize=(8, 4))
        if fig:
            # create bytes object to store image
            img = io.BytesIO()

            # save the figure into bytes
            plt.savefig(img, format='png', bbox_inches='tight', transparent=False)
            img.seek(0)

            # construct HTML response from image
            response = flask.make_response(base64.b64encode(img.getvalue()))
            response.headers['Content-Type'] = 'image/png'
            response.headers['Content-Transfer-Encoding'] = 'BASE64'

            # support CORS
            response.headers['Access-Control-Allow-Origin'] = (flask.request.headers.get('ORIGIN') or 'https://queue.stoneedgeobservatory.com')

            img.close()

            return response

        return flask.Response("{'error': 'Unable to create visibility plot'}", status=500, mimetype='application/json')

