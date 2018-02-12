from telescope import SSHTelescope

t = SSHTelescope()

#t.chip_temp_ok()
#t.lamps_on()
#t.lamps_off()
#t.cool_ccd()
#t.disable_tracking()
#t.move_dome(300)
#t.enable_tracking()
#t.home_dome()
#t.home_ha()
#t.home_dec()
#t.calibrate_motors()

t.take_flats()

