import common
import os
import const
import cv2
import numpy as np

from my_logger import logger

state_data_list = []
state_fix_dict = {}

STATE_DETECT_THRESHOLD = 1

def load_state():
    state_list = os.listdir(os.path.join(const.MY_PATH, 'res', 'state'))
    state_list = filter(lambda x: x.endswith('.max.png'), state_list)
    state_list = map(lambda x: x[:-8], state_list)
    state_list = list(state_list)
    for state in state_list:
        img_min_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{state}.min.png')
        img_max_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{state}.max.png')
        img_svmin_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{state}.svmin.png')
        img_svmax_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{state}.svmax.png')
        img_mask_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{state}.mask.png')

        img_min = common.cv2_imread(img_min_fn).astype(np.float32)
        img_max = common.cv2_imread(img_max_fn).astype(np.float32)
        if os.path.exists(img_svmin_fn):
            assert(os.path.exists(img_svmax_fn))
            img_svmin = common.cv2_imread(img_svmin_fn).astype(np.float32)
            img_svmin = img_svmin[:,:,0:2]
            img_svmax = common.cv2_imread(img_svmax_fn).astype(np.float32)
            img_svmax = img_svmax[:,:,0:2]
            img_min = np.append(img_min, img_svmin, axis=2)
            img_max = np.append(img_max, img_svmax, axis=2)

        if os.path.exists(img_mask_fn):
            img_mask = common.cv2_imread(img_mask_fn, flags=cv2.IMREAD_UNCHANGED).astype(np.float32)
            assert(img_mask.shape[2] == 4)
        else:
            img_mask = None

        state_data_list.append({
            'state': state,
            'img_min': img_min,
            'img_max': img_max,
            'img_mask': img_mask,
        })
    
    state_fix_list = os.listdir(os.path.join(const.MY_PATH, 'res', 'state', 'fix'))
    state_fix_list = filter(lambda x: x.endswith('.max.png'), state_fix_list)
    state_fix_list = map(lambda x: x[:-8], state_fix_list)
    state_fix_list = list(state_fix_list)
    for state_fix in state_fix_list:
        state0, state1 = state_fix.split('.')
        img_min_fn = os.path.join(const.MY_PATH, 'res', 'state', 'fix', f'{state_fix}.min.png')
        img_max_fn = os.path.join(const.MY_PATH, 'res', 'state', 'fix', f'{state_fix}.max.png')
        img_mask_fn = os.path.join(const.MY_PATH, 'res', 'state', 'fix', f'{state_fix}.mask.png')
        img_svmax_fn = os.path.join(const.MY_PATH, 'res', 'state', 'fix', f'{state_fix}.svmax.png')
        img_mask_fn = os.path.join(const.MY_PATH, 'res', 'state', 'fix', f'{state_fix}.mask.png')

        img_min = common.cv2_imread(img_min_fn).astype(np.float32)
        img_max = common.cv2_imread(img_max_fn).astype(np.float32)
        if os.path.exists(img_svmin_fn):
            assert(os.path.exists(img_svmax_fn))
            img_svmin = common.cv2_imread(img_svmin_fn).astype(np.float32)
            img_svmin = img_svmin[:,:,0:2]
            img_svmax = common.cv2_imread(img_svmax_fn).astype(np.float32)
            img_svmax = img_svmax[:,:,0:2]
            img_min = np.append(img_min, img_svmin, axis=2)
            img_max = np.append(img_max, img_svmax, axis=2)

        if os.path.exists(img_mask_fn):
            img_mask = common.cv2_imread(img_mask_fn, flags=cv2.IMREAD_UNCHANGED).astype(np.float32)
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
    imgmx = img.max(axis=2)
    imgmn = img.min(axis=2)
    imgs = imgmx-imgmn
    imgv = imgmx
    imgsv = np.stack([imgs, imgv], axis=2)
    img = np.append(img, imgsv, axis=2)
    diff, state = STATE_DETECT_THRESHOLD, 'UNKNOWN'
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
        diff, state = STATE_DETECT_THRESHOLD, state
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
    assert(img_min.shape == img_max.shape)
    if img_min.shape[2] == 3:
        img = img[:,:,:3]

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
        diff = diff.sum() / mask_sum / img.shape[2]
    else:
        diff = diff.mean()

    return diff
