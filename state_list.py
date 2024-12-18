import os

import cv2
import numpy as np

from my_logger import logger

state_data_list = []
state_fix_dict = {}

def load_state():
    state_list = os.listdir(os.path.join('res', 'state'))
    state_list = filter(lambda x: x.endswith('.max.png'), state_list)
    state_list = map(lambda x: x[:-8], state_list)
    state_list = list(state_list)
    for state in state_list:
        img_min_fn = os.path.join('res', 'state', f'{state}.min.png')
        img_max_fn = os.path.join('res', 'state', f'{state}.max.png')
        img_mask_fn = os.path.join('res', 'state', f'{state}.mask.png')
        img_min = cv2.imread(img_min_fn).astype(np.float32)
        img_max = cv2.imread(img_max_fn).astype(np.float32)
        if os.path.exists(img_mask_fn):
            # print(img_max_fn)
            img_mask = cv2.imread(img_mask_fn, cv2.IMREAD_UNCHANGED).astype(np.float32)
            # print(img_mask.shape)
            assert(img_mask.shape[2] == 4)
        else:
            img_mask = None
        state_data_list.append({
            'state': state,
            'img_min': img_min,
            'img_max': img_max,
            'img_mask': img_mask,
        })
    
    state_fix_list = os.listdir(os.path.join('res', 'state', 'fix'))
    state_fix_list = filter(lambda x: x.endswith('.max.png'), state_fix_list)
    state_fix_list = map(lambda x: x[:-8], state_fix_list)
    state_fix_list = list(state_fix_list)
    for state_fix in state_fix_list:
        state0, state1 = state_fix.split('.')
        img_min_fn = os.path.join('res', 'state', 'fix', f'{state_fix}.min.png')
        img_max_fn = os.path.join('res', 'state', 'fix', f'{state_fix}.max.png')
        img_mask_fn = os.path.join('res', 'state', 'fix', f'{state_fix}.mask.png')
        img_min = cv2.imread(img_min_fn).astype(np.float32)
        img_max = cv2.imread(img_max_fn).astype(np.float32)
        if os.path.exists(img_mask_fn):
            img_mask = cv2.imread(img_mask_fn, cv2.IMREAD_UNCHANGED).astype(np.float32)
            assert(img_mask.shape[2] == 4)
        else:
            img_mask = None
        if state0 not in state_fix_dict:
            state_fix_dict[state0] = []
        state_fix_dict[state0].append({
            'state1': state1,
            'img_min': img_min,
            'img_max': img_max,
            'img_mask': img_mask,
        })

def get_state(img, debug=False):
    diff, state = 1, 'UNKNOWN'
    for state_data in state_data_list:
        new_state = state_data['state']
        img_min = state_data['img_min']
        img_max = state_data['img_max']
        img_mask = state_data['img_mask']
        new_diff = _get_state_diff(img, img_min, img_max, img_mask)
        if debug:
            # print(f'{new_state}: {new_diff}')
            logger.debug(f'QWHAMZOXKX {new_state}: {new_diff}')
        if new_diff < diff:
            diff = new_diff
            state = new_state
    # print(f'{state}: {diff}')
    logger.debug(f'KQMCKKWRZP {state}: {diff}')

    while state in state_fix_dict:
        old_state = state
        diff, state = 1, state
        for state_data in state_fix_dict[state]:
            new_state = state_data['state1']
            img_min = state_data['img_min']
            img_max = state_data['img_max']
            img_mask = state_data['img_mask']
            new_diff = _get_state_diff(img, img_min, img_max, img_mask)
            if debug:
                logger.debug(f'YUEAHCIRPJ {new_state}: {new_diff}')
            if new_diff < diff:
                diff = new_diff
                state = new_state
        logger.debug(f'EVUJCBNJDH {state}: {diff}')
        if state == old_state:
            break

    return state

def _get_state_diff(img, img_min, img_max, img_mask, debug=False):
    diff_max = img - img_max
    diff_max = np.maximum(diff_max, 0)
    diff_min = img_min - img
    diff_min = np.maximum(diff_min, 0)
    diff = np.maximum(diff_max, diff_min)

    if debug:
        cv2.imwrite('diff_max.png', diff_max)
        cv2.imwrite('diff_min.png', diff_min)

    if img_mask is not None:
        mask = img_mask[:,:,3:4]
        # mask = mask.reshape(mask.shape[:2])
        mask = mask / 255
        diff = diff * mask
        mask_sum = mask.sum()
        diff = diff.sum() / mask_sum / 3
    else:
        diff = diff.mean()

    return diff
