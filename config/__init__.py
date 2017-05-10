import toml
from . import config as conf

# open and read toml file
config_file = open('config/config.toml')

# parse into Python dict
config_dict = toml.load(config_file)

# create Config class
config = conf.Config(config_dict)
