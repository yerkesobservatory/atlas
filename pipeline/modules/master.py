import os
import ccdproc

def master(dirname: str, imtype: str) -> cdproc.CCDData:
    """ This function creates a master image from the 'imtype'
    folder of given organized directory. It saves the master
    to the directory and returns the created CCDData object. 
    
    Parameters
    -----------

    Returns
    -------
    result: ccdproc.CCDData
        The created imtype master
    """
    # directory for the darks
    imdir = os.path.join(dirname, imtype)

    imgs = []
    # find all fits files
    for file in os.listdir(imdir):

        fmt = file.split('.')[-1]
        if fmt.lower() in ['fits', 'fit']:
            imgs.append(os.path.join(imdir, file))

    # filename for master dark
    base = imgs[0]
    ending = base.split('_')[-1]
    basename = base[0:-len(ending)-1]
    name = basename+f'_master{imtype}.fits'
    
    # make master dark
    master = ccdproc.combine(imgs, output_file=name, method='average',
                             unit='adu')

    return master
