""" This file provides the telescope specific commands to execute the needed
actions on the telescope, and regular expressions to parse their output in order
to extract desired information. 
"""

# open the dome and setup telescope for operation
open_dome = 'openup nocloud'
open_dome_re = r' opening observatory '

# status of slit 'open' or 'closed'
dome_open = 'tx slit'
dome_open_re = r'(?<=slit=).*?(?=$)'

# close the dome but leave the telescope ready
close_dome = 'closedown'
# DATE closing observatory user={}
close_dome_re = r' closing observatory '

# move the dome
move_dome = 'tx dome put={az}'
move_dome_re = r'done dome az='

# home the dome
home_dome = 'tx home dome'
home_dome_re = r'done home az_hit='

# home the HA motor
home_ha = 'tx home ha'
home_ha_re = r'done home ha_hit='

# home the HA motor
home_dec = 'tx home dec'
home_dec_re = r'done home dec_hit='

# keep the slit open for a given amount of time
keep_open = r'keepopen maxtime={time} slit'
keep_open_re = r''

# close down the telescope at the end of the night
close_down = 'closedown'
close_down_re = r' closing observatory '

# lock the telescope for a given user
lock = r'tx lock user={user} comment={comment}'
lock_re = r'done lock user='

# check who has the telescope locked
check_lock = 'tx lock'
# unlocked - "done lock"
# locked - "done lock user=rprechelt@gmail.com"
check_lock_re = r'done lock'

# unlock the telescope
unlock = 'tx lock clear'
unlock_re = r'done lock'

# enable tracking
enable_tracking = 'tx track on'
# "done track ha={} dec={}"
enable_tracking_re = r'done track ha='

# disable tracking
disable_tracking = 'tx track off'
disable_tracking_re = r'done track ha='

# turn dome lamps 'on' or 'off'
dome_lamps = 'tx lamps all={state}'

# mcn
# get ccd status
# done ccd_status nrow=2048 ncol=2048 readtime=8 tchip=-20.0 setpoint=-20.0 name=ProLine_PL230 darktime=16179 pixel=15.0 rot=180 drive=68
get_ccd_status = 'tx ccd_status'
tchip_ccd_re = r'(?<=tchip=).*?(?= )'
setpoint_ccd_re = r'(?<=setpoint=).*?(?= )'

# mcn
# cool ccd
cool_ccd = 'ccd cool'

# get cloud cover percentage
get_cloud = 'tx taux'
get_cloud_re = r'(?<=cloud=).*?(?= )'

# get dew level
get_dew = 'tx taux'
get_dew_re = r'(?<=dew=).*?(?=$)'

# get rain value 
get_rain = 'tx taux'
get_rain_re = r'(?<=rain=).*?(?= )'

# get the altitude of the sun
get_sun_alt = 'sun'
get_sun_alt_re = r'(?<=alt=).*$'

# get the altitude of the moon
get_moon_alt = 'moon'
get_moon_alt_re = r'(?<=alt=).*?(?= )'

# slew telescope to target name - i.e. M31
goto_target = 'catalog {target} | dopoint'
goto_target_re = r''

# get alt of target
altaz_target = 'catalog {target} | altaz'
alt_target_re = r'(?<=alt=).*?(?= )'
az_target_re = r'(?<=az=).*?(?= )'

# slew telescope to RA/Dec
goto = 'tx point ra={ra} dec={dec} equinox=2000'
goto_re = r''

# slew telescope to HA/DEC without moving the dome
# this is for dusk flats
goto_for_flats = 'tx point ha={ha} dec={dec} decimal nodome'
goto_for_flats = r''

# get altaz of RA/Dec
altaz = 'echo {ra} {dec} 2000 | altaz'
alt_re = r'(?<=alt=).*?(?= )'
az_re = r'(?<=az=).*?(?= )'

# offset the telescope by given RA/Dec
offset = 'tx offset ra={ra} dec={dec}'
offset_re = r'done offset'

# get the current focus value of the telescope
get_focus = 'tx focus'
get_focus_re = r''

# set the current focus value of the telescope
set_focus = 'tx focus pos={focus}'
set_focus_re = r''

# get current filter
current_filter = 'pfilter'
current_filter_re = r''

# change filter
change_filter = 'pfilter {name}'
change_filter_re = r''

# take an exposure - should contain {} for parameters
# in this order: exposure_time, binning, output filename
take_exposure = 'image time={time} bin={binning} outfile={filename}'
take_exposure_re = r''

# take a dark frame - should contain {} for parameters
# in this order: exposure_time, binning, output filename
take_dark = 'image time={time} bin={binning} outfile={filename} dark'
take_dark_re = r''

# take a bias frame
take_bias = 'image bin={binning} outfile={filename} notime'
