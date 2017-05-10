import ccdproc
from typing import List

def Task(data: List[ccdproc.CCDData], **kwargs) -> ccdproc.CCDData:
    """ This class performs a single pipeline task. 
    
    Parameters
    -----------
    data: List[ccdproc.CCDData]
        A list of ccdproc.CCDData objects that are the outputs
        from the previous steps in the pipeline that this task
        lists as its required dependencies. This list could also
        be empty if this task has no required dependencies.

    Returns
    -------
    output: ccdproc.CCDData
        The processed output CCDData object from this task.
    """
    return data[0]
