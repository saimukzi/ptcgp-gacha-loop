import os
import const
import yaml
import card_list
from my_logger import logger

MY_PATH = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(MY_PATH, 'default.yaml')  

my_config_data = None

def get_config(fn):
    global my_config_data

    ret = yaml.load(open(DEFAULT_CONFIG_PATH, 'rt', encoding='utf-8'), Loader=yaml.FullLoader)
    # config_data = yaml.load(open(fn, 'rt', encoding='utf-8'), Loader=yaml.FullLoader)
    config_data = get_config_with_import(fn)

    # old value key
    if ('STOP_AT_WONDER_RARE_PACK' not in config_data) and ('STOP_AT_RARE_PACK' in config_data):
        config_data['STOP_AT_WONDER_RARE_PACK'] = config_data['STOP_AT_RARE_PACK']
    if ('STOP_AT_NONWONDER_RARE_PACK' not in config_data) and ('STOP_AT_RARE_PACK' in config_data):
        config_data['STOP_AT_NONWONDER_RARE_PACK'] = config_data['STOP_AT_RARE_PACK']

    if ('HANDLE_WONDER_RARE_PACK' not in config_data) and ('STOP_AT_WONDER_RARE_PACK' in config_data):
        config_data['HANDLE_WONDER_RARE_PACK'] = 'STOP' if config_data['STOP_AT_WONDER_RARE_PACK'] else 'IGNORE'
    if ('HANDLE_NONWONDER_RARE_PACK' not in config_data) and ('STOP_AT_NONWONDER_RARE_PACK' in config_data):
        config_data['HANDLE_NONWONDER_RARE_PACK'] = 'STOP' if config_data['STOP_AT_NONWONDER_RARE_PACK'] else 'IGNORE'
    if ('HANDLE_WONDER_TARGET_PACK' not in config_data) and ('STOP_AT_WONDER_RARE_PACK' in config_data):
        config_data['HANDLE_WONDER_TARGET_PACK'] = 'STOP' if config_data['STOP_AT_WONDER_RARE_PACK'] else 'IGNORE'
    if ('HANDLE_NONWONDER_TARGET_PACK' not in config_data) and ('STOP_AT_NONWONDER_RARE_PACK' in config_data):
        config_data['HANDLE_NONWONDER_TARGET_PACK'] = 'STOP' if config_data['STOP_AT_NONWONDER_RARE_PACK'] else 'IGNORE'

    # check disk space only if needed
    check_disk_space = False
    check_disk_space = check_disk_space or (config_data['HANDLE_WONDER_TARGET_PACK'] not in ['STOP','IGNORE'])
    check_disk_space = check_disk_space or (config_data['HANDLE_NONWONDER_TARGET_PACK'] not in ['STOP','IGNORE'])
    check_disk_space = check_disk_space or (config_data['HANDLE_WONDER_RARE_PACK'] not in ['STOP','IGNORE'])
    check_disk_space = check_disk_space or (config_data['HANDLE_NONWONDER_RARE_PACK'] not in ['STOP','IGNORE'])
    check_disk_space = check_disk_space or (config_data['HANDLE_WONDER_TARGET_RARE_PACK'] not in ['STOP','IGNORE'])
    check_disk_space = check_disk_space or (config_data['HANDLE_NONWONDER_TARGET_RARE_PACK'] not in ['STOP','IGNORE'])
    if not check_disk_space:
        config_data['MIN_FREE_DISK_SPACE'] = 0

    ret.update(config_data)

    my_config_data = ret

    return ret

def get_config_with_import(fn):
    ret = yaml.load(open(fn, 'rt', encoding='utf-8'), Loader=yaml.FullLoader)
    ret0 = {}
    if ('IMPORT_LIST' in ret) and (ret['IMPORT_LIST'] is not None):
        for import_fn in ret['IMPORT_LIST']:
            import_fn0 = os.path.join(os.path.dirname(fn), import_fn)
            ret1 = get_config_with_import(import_fn0)
            ret0.update(ret1)
    ret0.update(ret)
    return ret0

def check(config_data, check_TARGET_CARD_LIST=True):
    assert('TARGET_PACK' in config_data)
    assert(config_data['TARGET_PACK'] in const.TARGET_PACK_LIST)

    if check_TARGET_CARD_LIST:
        assert(len(card_list.CARD_LIST)>0)
        assert('TARGET_CARD_LIST' in config_data)
        card_set = card_list.CARD_LIST
        card_set = map(lambda x: x['card'], card_set)
        card_set = set(card_set)

        for target_card in config_data['TARGET_CARD_LIST']:
            if target_card not in card_set:
                logger.error(f'HCFBYRITEH Invalid TARGET_CARD: {target_card}')
                assert(False)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=str)
    args = parser.parse_args()

    config_data = get_config(args.config)

    card_list.load_card_img()
    check(config_data)
