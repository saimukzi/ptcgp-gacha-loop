import common
import const
import cv2
import math
import numpy as np
import os

from my_logger import logger

GACHA_RESULT_XY_LIST = [
    (51,111),(119,111),(187,111),
    (84,205),(154,205),
]
GACHA_RESULT_SIZE = (62,86)

CARD_LIST = []

GRAY_RESULT_IMG = None

def load_card_img():
    global GRAY_RESULT_IMG
    if len(CARD_LIST) > 0:
        return
    card_list = os.listdir(os.path.join(const.MY_PATH, 'res', 'card'))
    card_list = filter(lambda x: x.endswith('.png'), card_list)
    card_list = map(lambda x: x[:-4], card_list)
    card_list = list(card_list)
    for card in card_list:
        img_path = os.path.join(const.MY_PATH, 'res', 'card', f'{card}.png')
        img = common.cv2_imread(img_path)
        img = cv2.resize(img, GACHA_RESULT_SIZE)
        CARD_LIST.append({
            'card': card,
            'img': img,
        })
    GRAY_RESULT_IMG = common.cv2_imread(os.path.join(const.MY_PATH, 'res', 'gray_result.png'))

def read_gacha_result(img):
    img = img.astype(np.float32)
    ret_list = []

    # check gray
    gray_match = np.abs(img - GRAY_RESULT_IMG)
    gray_match = gray_match.sum(axis=2)
    gray_match = gray_match < 2
    for i, xy in enumerate(GACHA_RESULT_XY_LIST):
        x,y = xy
        card_gmatch_img = gray_match[y:y+GACHA_RESULT_SIZE[1], x:x+GACHA_RESULT_SIZE[0]]
        gmatch_sum = card_gmatch_img.sum()
        gmatch_rate = gmatch_sum / math.prod(GACHA_RESULT_SIZE)
        if gmatch_rate >= 0.1:
            logger.warning(f'HZPBCAOBRO: gray card, i={i} match={gmatch_rate}')
            return 'GRAY'

    # check card
    for i, xy in enumerate(GACHA_RESULT_XY_LIST):
        x,y = xy
        card_img = img[y:y+GACHA_RESULT_SIZE[1], x:x+GACHA_RESULT_SIZE[0]]
        diff_list = []
        for card_data in CARD_LIST:
            # card = card_data['card']
            card_img_data = card_data['img']
            diff = np.abs(card_img - card_img_data)
            diff = diff.mean()
            diff_list.append(diff)
        idx = np.argmin(diff_list)
        logger.debug(f'YTNYAWSKRB {i}: {CARD_LIST[idx]["card"]}')
        ret_list.append(CARD_LIST[idx]["card"])
    return ret_list
