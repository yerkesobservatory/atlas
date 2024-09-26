import io
import flask
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict
from routines import plots
from config import config
import logging
import colorlog
#from flask_cors import CORS


class ResourceServer(object):
    """ This class is a REST endpoint designed to serve custom files (primary plots and images)
    for the Meteor web app.
    """

    # logger for class
    log = None

    def __init__(self):
        """ We create the app, register routes, and runz.
        """

        # initialize logging system if not already done
        if not ResourceServer.log:
            ResourceServer.__init_log()

        # create the Flask app
        app = flask.Flask("Resource Server")

        # make it CORS compatible
        # CORS(app)

        @app.route('/visibility/<string:target>', methods=['GET'])
        def visibility(target: str, **kwargs) -> Dict[str, str]:
            return self.visibility(target, **kwargs)

        @app.route('/preview/<string:target>', methods=['GET'])
        def preview(target: str, **kwargs) -> Dict[str, str]:
            return self.preview(target, **kwargs)

        # start it
        app.run(host='0.0.0.0', port=config.queue.resource_port)

    def make_plot_response(self, figure: matplotlib.figure.Figure, **kwargs):
        """ Given a matplotlib figure, base64 encode the figure and
        make the appropriate HTML response.
        """
        # create bytes object to store image
        img = io.BytesIO()

        # save the figure into bytes
        self.log.debug('make_plot_response')
        figure.savefig(img, format='png', bbox_inches='tight', **kwargs)
        figure.savefig('/tmp/test.png', format='png',
                       bbox_inches='tight', **kwargs)
        img.seek(0)

        # construct HTML response from image
        response = flask.make_response(
            base64.b64encode(img.getvalue()).decode())
        response.headers['Content-Type'] = 'image/png'
        response.headers['Content-Transfer-Encoding'] = 'BASE64'

        # support CORS
        # response.headers['Access-Control-Allow-Origin'] = (
        #     flask.request.headers.get('ORIGIN') or 'https://queue.stoneedgeobservatory.com' or 'https://sirius.stoneedgeobservatory.com:8179/*')

        # close image and figures
        img.close()

        return response

    def visibility(self, target: str) -> Dict[str, str]:
        """ This endpoint produces a visibility curve (using code in /routines)
        for the object provided by 'target', and returns it to the requester.
        """

        self.log.info('visibility called!')
        fig = plots.visibility_curve(target, self.log, figsize=(8, 4))
        self.log.debug("got past vis curve")
        self.log.debug(fig)
        if fig:
            response = self.make_plot_response(fig, transparent=False)
            plt.close(fig)

            return response

        return flask.Response("{'error': 'Unable to create visibility plot'}", status=500, mimetype='application/json')

    def preview(self, target: str) -> Dict[str, str]:
        """ This endpoint uses astroplan to produce a preview image

        """
        fig = plots.target_preview(target)
        
        if fig:
            response = self.make_plot_response(fig, transparent=True)
            plt.close(fig)

            return response

        return flask.Response("{'error': 'Unable to create target preview'}", status=500, mimetype='application/json')

    @classmethod
    def __init_log(cls) -> bool:
        """ Initialize the logging system for this module and set
        a ColoredFormatter.
        """
        # create format string for this module
        format_str = config.logging.fmt.replace('[name]', 'RESOURCE')
        formatter = colorlog.ColoredFormatter(
            format_str, datefmt=config.logging.datefmt)

        # create stream
        stream = logging.StreamHandler()
        stream.setLevel(logging.DEBUG)
        stream.setFormatter(formatter)

        # assign log method and set handler
        cls.log = logging.getLogger('resource')
        cls.log.setLevel(logging.DEBUG)
        cls.log.addHandler(stream)

        # create filehandler
        logfile = time.strftime(config.logging.filename)
        fhand = logging.FileHandler(logfile)
        fhand.setFormatter(formatter)
        cls.log.addHandler(fhand)
