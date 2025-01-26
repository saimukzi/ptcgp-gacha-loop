import common
import config
import const
import cv2
import my_path
import numpy as np
import os

from my_logger import logger

state_name_set = set()
state_data_list = []
state_fix_dict = {}
state1_to_state0_set_dict = {}
state_to_action_dist = {}
state_to_forget_img_dict = {}
state_to_calibrate_mask_hwaf1_dict = {}

STATE_DETECT_THRESHOLD = 1

def load_state(input_mask255f_img = None):
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
            img_mask = img_mask[:,:,3:4]
        else:
            img_mask = None

        if input_mask255f_img is not None:
            if img_mask is None:
                img_mask = input_mask255f_img
            else:
                img_mask = input_mask255f_img * img_mask / 255

        state_name_set.add(state)
        state_data_list.append({
            'state': state,
            'img_min': img_min,
            'img_max': img_max,
            'img_mask': img_mask,
        })
    
    state_fix_list = os.listdir(os.path.join(const.MY_PATH, 'res', 'state', 'fix'))
    state_fix_list = filter(lambda x: x.endswith('.mask.png'), state_fix_list)
    state_fix_list = map(lambda x: x[:-9], state_fix_list)
    state_fix_list = list(state_fix_list)
    for state_fix in state_fix_list:
        state0, state1 = state_fix.split('.')
        img_mask_fn = os.path.join(const.MY_PATH, 'res', 'state', 'fix', f'{state_fix}.mask.png')

        img_min_fn = os.path.join(const.MY_PATH, 'res', 'state', 'fix', f'{state_fix}.min.png')
        if not os.path.exists(img_min_fn):
            img_min_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{state1}.min.png')
        img_max_fn = os.path.join(const.MY_PATH, 'res', 'state', 'fix', f'{state_fix}.max.png')
        if not os.path.exists(img_max_fn):
            img_max_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{state1}.max.png')
        img_svmin_fn = os.path.join(const.MY_PATH, 'res', 'state', 'fix', f'{state_fix}.svmin.png')
        if not os.path.exists(img_svmin_fn):
            img_svmin_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{state1}.svmin.png')
        img_svmax_fn = os.path.join(const.MY_PATH, 'res', 'state', 'fix', f'{state_fix}.svmax.png')
        if not os.path.exists(img_svmax_fn):
            img_svmax_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{state1}.svmax.png')

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
            img_mask = img_mask[:,:,3:4]
        else:
            img_mask = None

        if input_mask255f_img is not None:
            if img_mask is None:
                img_mask = input_mask255f_img
            else:
                img_mask = input_mask255f_img * img_mask / 255

        state_name_set.add(state0)
        state_name_set.add(state1)

        if state0 not in state_fix_dict:
            state_fix_dict[state0] = []
        state_fix_dict[state0].append({
            'state1': state1,
            'img_min': img_min,
            'img_max': img_max,
            'img_mask': img_mask,
        })

        if state1 not in state1_to_state0_set_dict:
            state1_to_state0_set_dict[state1] = set()
        state1_to_state0_set_dict[state1].add(state0)

    # action
    for img_fn in os.listdir(os.path.join(const.MY_PATH, 'res', 'state')):
        if not img_fn.endswith('.png'):
            continue
        token = img_fn.split('.')[:-1]
        state = token[0]
        img = common.cv2_imread(os.path.join(const.MY_PATH, 'res', 'state', img_fn)).astype(np.float32)
        if token[1] == 'click':
            assert(state not in state_to_action_dist)
            state_to_action_dist[state] = {
                'action': token[1],
                'xy_list': _to_xy_list(img, 'RGB'),
            }
        elif token[1] == 'swipe':
            assert(state not in state_to_action_dist)
            duration = token[2:]
            duration = filter(lambda x: x.startswith('d'), duration)
            duration = list(duration)
            assert(len(duration) == 1)
            duration = duration[0][1:]
            duration = int(duration)
            state_to_action_dist[state] = {
                'action': token[1],
                'duration': duration,
                'from_xy_list': _to_xy_list(img, 'R'),
                'to_xy_list': _to_xy_list(img, 'G'),
            }
        elif token[1] == 'select':
            assert(state not in state_to_action_dist)
            state_to_action_dist[state] = {
                'action': token[1],
                'R_xy_list': _to_xy_list(img, 'R'),
                'G_xy_list': _to_xy_list(img, 'G'),
                'B_xy_list': _to_xy_list(img, 'B'),
                'RG_xy_list': _to_xy_list(img, 'RG'),
                'RB_xy_list': _to_xy_list(img, 'RB'),
                'BG_xy_list': _to_xy_list(img, 'BG'),
                'RGB_xy_list': _to_xy_list(img, 'RGB'),
            }

    # forget
    for img_fn in os.listdir(os.path.join(const.MY_PATH, 'res', 'state')):
        if not img_fn.endswith('.forget.png'):
            continue
        token = img_fn.split('.')[:-1]
        state = token[0]
        img = common.cv2_imread(os.path.join(const.MY_PATH, 'res', 'state', img_fn), flags=cv2.IMREAD_UNCHANGED).astype(np.float32)
        img = img[:,:,3:4] / 255
        state_to_forget_img_dict[state] = img

    # state_to_calibrate_img_dict
    for img_fn in os.listdir(os.path.join(const.MY_PATH, 'res', 'state')):
        if not img_fn.endswith('.calibrate.png'):
            continue
        token = img_fn.split('.')[:-1]
        state = token[0]
        img = common.cv2_imread(os.path.join(const.MY_PATH, 'res', 'state', img_fn), flags=cv2.IMREAD_UNCHANGED).astype(np.float32)
        img = img[:,:,3:4] / 255
        state_to_calibrate_mask_hwaf1_dict[state] = img

def get_state(src_img, src_img_mask, state_mask=None, debug=False):
    _state_mask_cal = None
    _state_mask_check = None
    if state_mask is not None:
        if '-' not in state_mask:
            _state_mask_check = set(state_mask)
        else:
            _state_mask_check = state_name_set - state_mask
        _state_mask_cal = set(_state_mask_check)
        old_len = len(_state_mask_cal)
        while True:
            for state1 in _state_mask_cal:
                if state1 in state1_to_state0_set_dict:
                    _state_mask_cal = _state_mask_cal.union(state1_to_state0_set_dict[state1])
            new_len = len(_state_mask_cal)
            if new_len == old_len:
                break
            old_len = new_len

    imgmx = src_img.max(axis=2)
    imgmn = src_img.min(axis=2)
    imgs = imgmx-imgmn
    imgv = imgmx
    imgsv = np.stack([imgs, imgv], axis=2)
    src_img = np.append(src_img, imgsv, axis=2)
    diff, state = STATE_DETECT_THRESHOLD, 'UNKNOWN'
    for state_data in state_data_list:
        new_state = state_data['state']
        if _state_mask_cal is not None and new_state not in _state_mask_cal:
            continue
        state_img_min = state_data['img_min']
        state_img_max = state_data['img_max']
        state_img_mask = state_data['img_mask']
        new_diff = _get_state_diff(src_img, src_img_mask, state_img_min, state_img_max, state_img_mask, debug=debug, debug_state_name=new_state)
        if debug:
            # print(f'CGVMDKKLJH {new_state}: {new_diff}')
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
            if (_state_mask_cal is not None) and (new_state not in _state_mask_cal) and (new_state != 'UNKNOWN'):
                continue
            state_img_min = state_data['img_min']
            state_img_max = state_data['img_max']
            state_img_mask = state_data['img_mask']
            new_diff = _get_state_diff(src_img, src_img_mask, state_img_min, state_img_max, state_img_mask, debug=debug, debug_state_name=f'{old_state}.{new_state}')
            if debug:
                logger.debug(f'YUEAHCIRPJ {new_state}: {new_diff}')
            if new_diff < diff:
                diff = new_diff
                state = new_state
        logger.debug(f'EVUJCBNJDH {state}: {diff}')
        if state == old_state:
            break

    if _state_mask_check is not None and state not in _state_mask_check:
        state = 'UNKNOWN'

    return state

def state_prefix(state_p):
    return set(filter(lambda x: x.startswith(state_p), state_name_set))

# src_mask_hwab = None

def _get_state_diff(src_img, src_img_mask, state_img_min, state_img_max, state_img_mask, debug=False, debug_state_name=None):
    assert(state_img_min.shape == state_img_max.shape)
    assert(not (debug and (debug_state_name is None)))
    if state_img_min.shape[2] == 3:
        src_img = src_img[:,:,:3]

    diff_max = src_img - state_img_max
    diff_max = np.maximum(diff_max, 0)
    diff_min = state_img_min - src_img
    diff_min = np.maximum(diff_min, 0)
    diff = np.maximum(diff_max, diff_min)

    if state_img_mask is not None:
        mask = state_img_mask
    else:
        mask = np.ones(src_img.shape[:2]+(1,), dtype=np.float32) * 255

    if src_img_mask is not None:
        # logger.debug('PPBJPURJGC src_mask_hwab is not None')
        mask = mask * src_img_mask
    # mask = mask.reshape(mask.shape[:2])
    mask = mask / 255
    diff = diff * mask
    if debug or ((config.my_config_data is not None) and (config.my_config_data['DEBUG_IMG'])):
        # os.makedirs(os.path.join(const.APP_PATH, 'tmp', 'debug'), exist_ok=True)
        try:
            common.cv2_imwrite(os.path.join(my_path.instance_debug(), '_get_state_diff', f'{debug_state_name}.diff.png'), diff[:,:,:3].astype(np.uint8))
        except:
            pass
        mask_hwc = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
        mask_hwc[:,:] = mask * 255
        try:
            common.cv2_imwrite(os.path.join(my_path.instance_debug(), '_get_state_diff', f'{debug_state_name}.mask.png'), mask_hwc.astype(np.uint8))
        except:
            pass
    mask_sum = mask.sum()
    diff = diff.sum() / mask_sum / src_img.shape[2]

    return diff

def _to_xy_list(img, color):
    img = (img/255) > 0.5

    imgb = img[:,:,0]
    imgg = img[:,:,1]
    imgr = img[:,:,2]

    if 'R' not in color: imgr = (imgr != True)
    if 'G' not in color: imgg = (imgg != True)
    if 'B' not in color: imgb = (imgb != True)

    img = imgb & imgg & imgr
    yx_list = np.argwhere(img)

    ret = []
    for yx in yx_list:
        ret.append((int(yx[1]), int(yx[0])))

    return ret

