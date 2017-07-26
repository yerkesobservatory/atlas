""" This function provides utilities to evaluate the focus of a given image, and
autofocus a connected telescope. 
"""


def focus(telescope: 'Telescope') -> bool:
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

    # wait until weather is good to observe
    telescope.wait_until_good()
    
    # point telescope at high altitude

    # save current focus value
    original_focus = telescope.get_focus()

    # evaluate current focus
    original_value = evaluate(NEED_TO_COPY_FILE)
    
    # implement Newton's method using `evaluate` as the
    # function to be maximized

    # check that the new focus is better than old focus
    if original_value > current_value:
        telescope.set_focus(original_focus)
        return False, original_value
    
    return True, 1.0


def evaluate(filename: str) -> float:
    """ Open the FITS file located at filename on localhost and evaluate
    the focus using the autofocus metric. Returns the value of the metric. 
    """
    return 0.0
