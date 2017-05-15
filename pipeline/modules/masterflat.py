import os
from pipeline.modules.master import master

def masterflat(**kwargs) -> cdproc.CCDData:
    """ This function creates a master flat from the 'flat'
    folder of given organized directory. It saves the master
    flat to the directory and returns the created CCDData object. 
    
    Parameters
    -----------

    Returns
    -------
    result: ccdproc.CCDData
        The created master flat
    """
    
    # extract dirname
    dirname = kwargs.get('dirname')

    # check that we have a directory
    if dirname is None:
        return None
    
    # extract dirname
    return master(dirname, 'flat')
