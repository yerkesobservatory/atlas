class Config(object):
    """ Load a TOML file into a set of nested Python Config() objects. 
    """
    def __init__(self, data):
        for name, value in data.items():
            setattr(self, name, self._wrap(value))
            
    def _wrap(self, value):
        if isinstance(value, (tuple, list, set, frozenset)):
            return type(value)([self._wrap(v) for v in value])
        else:
            return Config(value) if isinstance(value, dict) else value
