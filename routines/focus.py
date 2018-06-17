import os
import requests
import subprocess
import datetime
from time import gmtime, strftime

import numpy as np
import astropy.table
import astropy.io.ascii
from astropy.io import fits, ascii
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.coordinates import Angle


""" This function provides utilities to evaluate the focus of a given image, and
autofocus a connected telescope. 
"""


def focus(telescope: 'Telescope') -> bool:
    """ Automatically focus the telescope. 

    Use an automated image processing routine (TODO: info here) to 
    automatically focus the telescope; this takes multiple images and
    evaluates their respective "focus". 

    Parameters
    ----------
    telescope: Telescope
        A connected telescope object

    Returns
    -------
    res: bool
        True if focus was successful, False if otherwise
    focus: float
        The final value of the focus metric used to evaluate focus.
    """
    # wait until weather is good to observe
    telescope.wait_until_good()
    
    # create tonight's focus folder
    folder = "/home/sirius/focus/focus_"+str(strftime("%Y-%m-%d_%Hh%Mm%Ss", gmtime()))
    subprocess.check_call(['mkdir',folder])
    os.chdir("/home/sirius/focus/")
    
    # define observer parameters
    observer = astropy.coordinates.EarthLocation(lat=38.336667*u.deg, lon=-122.6675*u.deg, height=75*u.m)
    now = astropy.time.Time(datetime.datetime.utcnow(), scale='utc')

    altaz_frame_seo = astropy.coordinates.AltAz(obstime=now, location=observer)
    altaz_zenith_seo = SkyCoord(0*u.degree, +90*u.degree, frame=altaz_frame_seo)
    radec_zenith_seo = altaz_zenith_seo.transform_to("icrs")
    
    # define standard star parameters
    sdss_standard_stars = astropy.table.Table.read("SDSS_Standard_Stars", format="ascii.commented_header")
    standard_stars_name = sdss_standard_stars['StarName']
    standard_stars_ra = sdss_standard_stars['RA(J2000.0)']
    standard_stars_dec = sdss_standard_stars['DEC(J2000.0)']

    standard_stars_r = sdss_standard_stars['r\'']
    standard_stars_g = sdss_standard_stars['g\'-r\'']+standard_stars_r
    standard_stars_i = -sdss_standard_stars['r\'-i\'']+standard_stars_r
    standard_stars_z = -sdss_standard_stars['i\'-z\'']+standard_stars_i
    standard_stars_u = sdss_standard_stars['u\'-g\'']+standard_stars_g

    # choose the standard star closest to zenith
    standard_stars_altaz = SkyCoord(ra=standard_stars_ra, dec=standard_stars_dec, unit=(u.hourangle, u.deg), frame="icrs").transform_to(altaz_frame_seo)
    standard_stars_maxalt = np.argmax(standard_stars_altaz.alt)
    standard_stars_radec_decimaldeg = SkyCoord(ra=standard_stars_ra[standard_stars_maxalt], dec=standard_stars_dec[standard_stars_maxalt], unit=(u.hourangle, u.deg), frame="icrs")

    ra = str(standard_stars_ra[standard_stars_maxalt][0:2])+":"+str(standard_stars_ra[standard_stars_maxalt][3:5])+":"+str(int(round(float(standard_stars_ra[standard_stars_maxalt][6:11]))))
    dec = str(standard_stars_dec[standard_stars_maxalt][0:3])+":"+str(standard_stars_dec[standard_stars_maxalt][4:6])+":"+str(int(round(float(standard_stars_dec[standard_stars_maxalt][7:12]))))

    print("Focus star: ", standard_stars_name[standard_stars_maxalt], "ra: ", ra, "dec: ", dec)
    
    # initialize array covering a range of focus positions
    pass1_array = [4650,4675,4700,4725,4750,4775,4800,4825,4850,4875,4900,4925,4950,4975,5000]
    pass1_array_focus = np.zeros((len(pass1_array),2))
    
    subprocess.check_call(['openup','nocloud'])
    subprocess.check_call(['keepopen', 'slit', 'maxtime=3000'])
    subprocess.check_call(['tx', 'track', 'on'])
    subprocess.check_call(['/home/mcnowinski/seo/bin/pinpoint',ra,dec])
    
    # calculate PSF for pass1_array focus positions
    for i,position in enumerate(pass1_array):
        focus_position="pos="+str(position)
        subprocess.check_call(['tx','focus',focus_position])
        outfile = "outfile=/home/sirius/focus/"+folder+"/focus_"+str(standard_stars_name[standard_stars_maxalt])+"_30s_"+"pos"+str(position)+".fits"
        outfile_name = "/home/sirius/focus/"+folder+"/focus_"+str(standard_stars_name[standard_stars_maxalt])+"_30s_"+"pos"+str(position)+".fits"
        psfex_cat = "/home/sirius/focus/"+folder+"/test.cat"
        subprocess.check_call(['openup','nocloud'])
        subprocess.check_call(['tx','track','on'])
        subprocess.check_call(['keepopen', 'slit', 'maxtime=600'])
        subprocess.check_call(['image','time=30','bin=2',str(outfile)])
        subprocess.check_call(['/home/mcnowinski/sex/sextractor/bin/sex',str(outfile_name), '-c', 'psf.sex'])
        subprocess.check_call(['/home/mcnowinski/psfex/bin/psfex',str(psfex_cat), '-c', 'default.psfex'])
    
        psf = fits.open("/home/sirius/focus/"+folder+"/test.psf")
        fwhm = psf[1].header['PSF_FWHM']
    
        pass1_array_focus[i]=position,fwhm
    
    # fit data points to a 2nd-deg polynomial
    pass1_fit = np.polyfit(pass1_array_focus[:,0], pass1_array_focus[:,1], 2)
    pass1_fit_focus_pos = int(-pass1_fit[1]/(2*pass1_fit[0]))
    
    # set focus to minimum
    final_focus_pos = "pos="+str(pass1_fit_focus_pos)
    subprocess.check_call(['tx','focus',final_focus_pos])
    
    # save focus pos array
    np.savetxt("/home/sirius/focus/"+folder+"/"+folder+".dat", pass1_array_focus, fmt='%.5f', header='focus_pos PSF')
    
    # graph focus fits
    array = np.array(pass1_array_focus)
    plt.scatter(array[:,0], array[:,1])
    x = np.arange(4000,5100)
    y = pass1_fit[0]*x**2+pass1_fit[1]*x+pass1_fit[2]
    
    plt.plot(x,y)
    plt.ylim(2,5.5)
    plt.xlim(4550,5100)
    plt.savefig("/home/sirius/focus/"+folder+"/"+folder+"_fig.png")
    
    
    

