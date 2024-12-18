import os

import yaml


MY_PATH = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(MY_PATH, 'default.yaml')  

def get_config(fn):
    ret = yaml.load(open(DEFAULT_CONFIG_PATH, 'r'), Loader=yaml.FullLoader)
    config_data = yaml.load(open(fn, 'r'), Loader=yaml.FullLoader)
    ret.update(config_data)
    return ret
