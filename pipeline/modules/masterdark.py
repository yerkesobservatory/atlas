import os
import ccdproc

def masterdark(**kwargs) -> cdproc.CCDData:
    """ This function creates a master dark from the 'dark'
    folder of given organized directory. It saves the master
    dark to the directory and returns the created CCDData object. 
    
    Parameters
    -----------

    Returns
    -------
    result: ccdproc.CCDData
        The created master dark
    """
    # extract dirname
    dirname = kwargs.get('dirname')

    # check that we have a directory
    if dirname is None:
        return None

    # directory for the darks
    darkdir = os.path.join(dirname, 'dark')

    darks = []
    # find all fits files
    for file in os.listdir(darkdir):

        fmt = file.split('.')[-1]
        if fmt.lower() in ['fits', 'fit']:
            darks.append(os.path.join(darkdir, file))

    # filename for master dark
    base = darks[0]
    ending = base.split('_')[-1]
    basename = base[0:-len(ending)-1]
    name = basename+'_masterdark.fits'
    
    # make master dark
    master = ccdproc.combine(darks, output_file=name, method='average',
                             unit='adu')

    return master
