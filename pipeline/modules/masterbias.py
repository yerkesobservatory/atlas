import os
from pipeline.modules.master import master

def masterbias(**kwargs) -> cdproc.CCDData:
    """ This function creates a master bias from the 'bias'
    folder of given organized directory. It saves the master
    bias to the directory and returns the created CCDData object. 
    
    Parameters
    -----------

    Returns
    -------
    result: ccdproc.CCDData
        The created master bias
    """
    
    # extract dirname
    dirname = kwargs.get('dirname')

    # check that we have a directory
    if dirname is None:
        return None
    
    # extract dirname
    return master(dirname, 'bias')
