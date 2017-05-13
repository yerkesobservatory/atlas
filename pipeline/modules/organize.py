import os

def Organize(**kwargs) -> bool:
    """ This class organizes the folder of images into a standard
    heirarchy. The dirname is passed in as a keyword argument 'dirname'
    
    Parameters
    -----------

    Returns
    -------
    result: bool
        True if organization was successful, False otherwise
    """
    # extract dirname
    dirname = kwargs.get('dirname')

    # check that we have a directory
    if dirname is None:
        return False
    
    # create directories for files
    os.makedirs(dirname+'/dark')
    os.makedirs(dirname+'/flat')
    os.makedirs(dirname+'/bias')
    os.makedirs(dirname+'/science')
    os.makedirs(dirname+'/processed')

    # create science subdirectories for the filters
    for filt in ['i-band', 'r-band', 'g-band',
                 'u-band', 'z-band', 'h-alpha', 'clear']:
        os.makedirs(dirname+'/science/'+filt)

    # move files into correct directories
    for file in os.listdir(dirname):

        # path to file
        path = os.path.join(dirname, file)
        
        # check that it is not a directory
        if not os.path.isfile(path):
            continue

        # move dark, flat, bias
        for imtype in ['dark', 'flat', 'bias']:
            if f'_{imtype}' in file:
                os.rename(path, os.path.join(dirname, imtype, file))
                continue

        # move each of the SDSS filters
        for filt in ['i', 'r', 'g', 'u', 'z']:
            if f'_{filt}_' in file:
                os.rename(path, os.path.join(dirname, 'science', f'{filt}-band', file))
                continue

        # move h-alpha
        if '_ha_' in file:
            
            os.rename(path, os.path.join(dirname, 'science', 'h-alpha', file))
            continue

        # move h-alpha
        if '_clear_' in file:
            os.rename(path, os.path.join(dirname, 'science', 'clear', file))
            continue

    return True
