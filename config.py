import os
import const
import yaml
import card_list
from my_logger import logger

MY_PATH = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(MY_PATH, 'default.yaml')  

def get_config(fn):
    ret = yaml.load(open(DEFAULT_CONFIG_PATH, 'r'), Loader=yaml.FullLoader)
    config_data = yaml.load(open(fn, 'r'), Loader=yaml.FullLoader)
    ret.update(config_data)

    return ret

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
