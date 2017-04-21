# General class for config settings
class Config(object): pass

# GENERAL SETTINGS
############################################################
general = Config()

# The name of the observatory
general.name = 'Your Observatory Name'

# a shortname - used to name topics in the broker i.e. /obs/queue etc.
general.shortname = 'obs'
############################################################


# SERVER SETTINGS
############################################################
server = Config()

# server host or IP address where the broker and queue is running
server.host = '127.0.0.1'

# place to store the log files on server.host
server.logdir = '/var/log/atlas'
############################################################

# QUEUE SETTINGS
############################################################
queue = Config()

# directory on telescope server to store images
queue.remote_dir = '/data/queue/'

# number of biases to take PER science exposure
queue.numbias = 5

# how many minutes to wait between checking for bad weather
queue.wait_time = 15

# after how many hours of bad weather should the queue
# wait for before shutting down for the night
queue.max_wait_time = 4

############################################################


# BROKER SETTINGS
############################################################
mosquitto = Config()

# por for mosquitto communication
mosquitto.port = 19387
############################################################


# TELESCOPE SETTINGS
############################################################
telescope = Config()

# hostname/IP for telescope control/communication
telescope.host = 'telescope.myotherhostname.com'

# ssh username for remote telescope control
telescope.username = 'username'

# port for telescope communication
telescope.port = 22
############################################################


# STORAGE SETTINGS
############################################################
storage = Config()

# which host to store files on - hostname/IP/'localhost'
storage.host = 'storage.mythirdhostname.com'

# the username for remote connections
storage.username = 'username'

# where to store image on the host
storage.dir = '/home/username/images'

# the port for remote communication
storage.port = 22
############################################################


# NOTIFICATION SETTINGS
############################################################
notification = Config()

# enable/disable email communication
notification.email = True

# email to be displayed to users in case of error
notification.sysadmin = 'admin@myhostname.com'

# STMP mail server for email
notification.server = 'smtp.myhostname.com'

# username for mail server
notification.username = 'myuser@myhostname.com'

# password for mail server
notification.password = 'thisismysupersecurepasswordNOT!'

# subject linei for emails
notification.subject = 'My Observatory Name Notifications'

# enable/disable slack communication
notification.slack = True

# token for slack communication
notification.slack_token = 'xoxp-0342039840283-230294203984-ashtash'

# default channel for slack communication
notification.slack_channel = '#queue'
############################################################


# ASTROMETRY SETTINGS
############################################################
astrometry = Config()

# the directory containing the solve-field binary
astrometry.bin_dir = '/usr/local/bin'

# CCD binning
astrometry.binning = 2

# expsorue time
astrometry.exposure_time = 10

# downsampling fraction
astrometry.downsample = 2

# low pixel scale in arcsecperpix
astrometry.scale_low = 0.55

# high pixel scale in arcsecperpix
astrometry.scale_high = 0.05

# search for solutions with radius arcsec
astrometry.radius = 20.0

# maximum CPU limit for solutiong
astrometry.cpu_limit = 50

# the minimum RA error before deciding success
astrometry.min_ra_offset = 0.05

# the minimum Dec error before deciding success
astrometry.min_dec_offset = 0.05

# the maximum RA that will be applied to the telescope
astrometry.max_ra_offset = 20.0

# the maximum Dec that will be applied to the telescope
astrometry.max_dec_offset = 20.0

# the maximum number of tries before WCS quits
astrometry.max_tries = 20
############################################################
