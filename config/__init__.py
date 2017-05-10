import toml
from . import config as conf

# open and read toml file
with open('config/config.toml') as config_file:
    # parse into Python dict
    config_dict = toml.load(config_file)

    # create Config class
    config = conf.Config(config_dict)
