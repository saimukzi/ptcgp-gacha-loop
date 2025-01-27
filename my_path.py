import const
import config
import os

# def global_var():
#     return os.path.join(const.APP_PATH, 'var')

_global_work = None
def global_work():
    global _global_work
    if _global_work is None:
        if config.my_config_data['WORK_PATH'] is not None:
            _global_work = config.my_config_data['WORK_PATH']
        else:
            _global_work = const.APP_PATH
    return _global_work

_instance_var = None
def instance_var():
    # return os.path.join(const.APP_PATH, 'var', 'instances', config.my_config_data['INSTANCE_ID'])
    global _instance_var
    if _instance_var is None:
        if config.my_config_data['VAR_PATH'] is not None:
            _instance_var = config.my_config_data['VAR_PATH']
        else:
            _instance_var = os.path.join(global_work(), 'var', 'instances', config.my_config_data['INSTANCE_ID'])
    return _instance_var

_instance_debug = None
def instance_debug():
    # return os.path.join(const.APP_PATH, 'debug', 'instances', config.my_config_data['INSTANCE_ID'])
    global _instance_debug
    if _instance_debug is None:
        if config.my_config_data['DEBUG_PATH'] is not None:
            _instance_debug = config.my_config_data['DEBUG_PATH']
        else:
            _instance_debug = os.path.join(global_work(), 'debug', 'instances', config.my_config_data['INSTANCE_ID'])
    return _instance_debug

# def instance_gacha_result():
#     return os.path.join(const.APP_PATH, 'gacha_result', 'instances', config.my_config_data['INSTANCE_ID'])

_global_gacha_result = None
def global_gacha_result():
    # return os.path.join(const.APP_PATH, 'gacha_result')
    global _global_gacha_result
    if _global_gacha_result is None:
        if config.my_config_data['GACHA_RESULT_PATH'] is not None:
            _global_gacha_result = config.my_config_data['GACHA_RESULT_PATH']
        else:
            _global_gacha_result = os.path.join(global_work(), 'gacha_result')
    return _global_gacha_result

_global_bingo = None
def global_bingo():
    # return os.path.join(const.APP_PATH, 'bingo')
    global _global_bingo
    if _global_bingo is None:
        if config.my_config_data['BINGO_PATH'] is not None:
            _global_bingo = config.my_config_data['BINGO_PATH']
        else:
            _global_bingo = os.path.join(global_work(), 'bingo')
    return _global_bingo

def makedirs():
    os.makedirs(global_work(), exist_ok=True)
    os.makedirs(instance_var(), exist_ok=True)
    os.makedirs(instance_debug(), exist_ok=True)
    os.makedirs(global_gacha_result(), exist_ok=True)
    os.makedirs(global_bingo(), exist_ok=True)
