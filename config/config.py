class Config():
    pass


## Astrometry parameters for WCS solving
astrometry = Config()
astrometry.binning = 2
astrometry.exposure_time = 10
astrometry.downsample = 2
astrometry.scale_low = 0.55
astrometry.scale_high = 0.05
astrometry.radius = 20.0
astrometry.cpu_limit = 50
astrometry.min_ra_offset = 0.05
astrometry.min_dec_offset = 0.05
astrometry.max_ra_offset = 20.0
astrometry.max_dec_offset = 20.0
astrometry.max_tries = 20
astrometry.bin_dir = '/usr/local/bin'
