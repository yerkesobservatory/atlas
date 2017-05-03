""" This file provides the telescope specific commands to execute the needed
actions on the telescope, and regular expressions to parse their output in order
to extract desired information. 
"""

# open the dome and setup telescope for operation
open_dome = 'openup nocloud'
open_dome_re = r''

# close the dome but leave the telescope ready
close_dome = 'closedown'
close_dome_re = r''

# keep the slit open for a given amount of time
keep_open = 'keepopen maxtime={} slit'
keep_open_re = r''

# close down the telescope at the end of the night
close_down = 'closedown'
close_down_re = r''

# enable tracking
enable_tracking = 'tx track on'
enable_tracking_re = r''

# get cloud cover percentage
get_cloud = 'tx taux'
get_cloud_re = r'(?<=cloud=).*?(?= )'

# get dew level
get_dew = 'tx taux'
get_dew_re = r'(?<=dew=).*?(?= )'

# get rain value 
get_rain = 'tx taux'
get_rain_re = r'(?<=rain=).*?(?= )'

# get the altitude of the sun
get_sun_alt = 'sun'
get_sun_alt_re = r'(?<=alt=).*$'

# get the altitude of the moon
get_moon_alt = 'moon'
get_moon_alt_re = r'(?<=alt=).*?(?= )'

# status of slit 'open' or 'closed'
dome_open = 'tx slit'
dome_open_re = r'(?<=slit=).*?(?= )'

# slew telescope to target name - i.e. M31
goto_target = 'catalog {} | dopoint'
goto_target_re = r''

# get altaz of target
altaz_target = 'catalog {} | altaz'
altaz_target_re = r'(?<=alt=).*?(?= )'

# slew telescope to RA/Dec
goto = 'tx point ra={} dec={} equinox=2000'
goto_re = r''

# get altaz of RA/Dec
altaz = 'echo {} {} 2000 | altaz'
altaz_re = r'(?<=alt=).*?(?= )'

# offset the telescope by given RA/Dec
offset = 'tx offset ra={} dec={}'
offset_re = r''

# get current filter
current_filter = 'pfilter'
current_filter_re = r''

# change filter
change_filter = 'pfilter {}'
change_filter_re = r''

# take an exposure - should contain {} for parameters
# in this order: exposure_time, binning, output filename
take_exposure = 'image time={} bin={} outfile={}'
take_exposure_re = r''

# take a dark frame - should contain {} for parameters
# in this order: exposure_time, binning, output filename
take_dark = 'image time={} bin={} outfile={} dark'
take_dark_re = r''
