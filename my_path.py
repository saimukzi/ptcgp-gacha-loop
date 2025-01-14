import const
import config
import os

def global_var():
    return os.path.join(const.APP_PATH, 'var')

def instance_var():
    return os.path.join(const.APP_PATH, 'var', 'instances', config.my_config_data['INSTANCE_ID'])

def instance_debug():
    return os.path.join(const.APP_PATH, 'debug', 'instances', config.my_config_data['INSTANCE_ID'])

# def instance_gacha_result():
#     return os.path.join(const.APP_PATH, 'gacha_result', 'instances', config.my_config_data['INSTANCE_ID'])

def global_gacha_result():
    return os.path.join(const.APP_PATH, 'gacha_result')

def global_bingo():
    return os.path.join(const.APP_PATH, 'bingo')

def makedirs():
    os.makedirs(global_var(), exist_ok=True)
    os.makedirs(instance_var(), exist_ok=True)
    os.makedirs(instance_debug(), exist_ok=True)
    os.makedirs(instance_gacha_result(), exist_ok=True)
