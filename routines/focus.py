from telescope.telescope import Telescope

def focus(telescope: Telescope) -> bool:
    """ Automatically focus the telescope. 

    Use an automated image processing routine (TODO: info here) to 
    automatically focus the telescope; this takes multiple images and
    evaluates their respective "focus". This can be called before stars
    are visible but it will wait until sun <= -15. 

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
    return True, 1.0
