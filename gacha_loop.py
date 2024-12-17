import os
import sys
import time
import cv2
import ldagent
import numpy as np
import yaml
import argparse
import state_list
import card_list

# GACHA_RESULT_XY_LIST = [
#     (51,111),(119,111),(187,111),
#     (84,205),(154,205),
# ]
# GACHA_RESULT_SIZE = (62,86)

# TARGET_PACK = 'c'
# TARGET_CARD_SET = set(['cTR_20_000170_00_NATSUME_SR'])

# USERNAME = 'abc'

def main():
    parser = argparse.ArgumentParser(description='Gacha loop')
    parser.add_argument('config', type=str)
    args = parser.parse_args()

    config_data = yaml.load(open(args.config, 'r'), Loader=yaml.FullLoader)
    TARGET_PACK = config_data['TARGET_PACK']
    TARGET_CARD_SET = set(config_data['TARGET_CARD_LIST'])
    USERNAME = config_data['USERNAME']
    ldagent.config(config_data)

    # ldagent.set_LDPLAYER_PATH(config_data['LDPLAYER_PATH'])
    # ldagent.set_LD_EMU_NAME(config_data['LD_EMU_NAME'])

    if not ldagent.check():
        return
    
    os.makedirs('var', exist_ok=True)
    user_idx = 0
    if os.path.exists('var/user_idx.txt'):
        with open('var/user_idx.txt', 'r') as f:
            user_idx = int(f.read())

    # load_state()
    # load_card_img()
    state_list.load_state()
    card_list.load_card_img()

    flag_set = set()
    
    state_history = ['UNKNOWN']*10
    state = 'UNKNOWN'
    while True:
        img = ldagent.screencap().astype(np.float32)
        
        if state != 'UNKNOWN':
            state_history.append(state)
            state_history = state_history[-5:]

        # old_state = None
        # while True:
        #     state = state_list.get_state(img)
        #     if state == old_state:
        #         break
        #     old_state = state
        #     time.sleep(0.1)
        state = state_list.get_state(img)

        print(state_history, state)

        if 's03-start-01' in flag_set:
            if state not in ['xxx-dialog-swc', 'xxx-dialog-sc', 'xxx-dialog-lw']:
                ldagent.tap(275,378)
                time.sleep(0.1)
                continue
            if state == 'xxx-dialog-lw':
                flag_set.remove('s03-start-01')

        if 'xxx-gacha-03' in flag_set:
            if state not in ['xxx-gacha-05','s06-gacha1-03','s06-gacha1-04'] and (not state.startswith('xxx-gacha-03')):
                ldagent.tap(150,304)
                ldagent.tap(281,381)
                time.sleep(0.1)
                continue
            if state in ['xxx-gacha-05','s06-gacha1-03','s06-gacha1-04']:
                flag_set.remove('xxx-gacha-03')

        if 'xxx-swipeup' in flag_set:
            if state not in ['xxx-cont']:
                # ldagent.tap(275,378)
                time.sleep(0.1)
                continue
            flag_set.remove('xxx-swipeup')

        if state == 'err-badname':
            ldagent.tap(150, 280)
            flag_set.add(state)
            time.sleep(0.5)
            continue
        if 'err-badname' in flag_set:
            if state == 'xxx-dialog-sc':
                state = 's05-name-00'
            if state == 'xxx-dialog-swc':
                ldagent.tap(150, 179)
                time.sleep(0.5)
                state = 's05-name-02'
            

        if state == 's00-cover':
            ldagent.tap(150, 200)
            time.sleep(4)
            continue
        if state == 's01-info-00':
            ldagent.tap(100, 292)
            time.sleep(0.5)
            continue
        if state == 's01-info-01':
            ldagent.tap(100, 196)
            time.sleep(0.5)
            continue
        if state == 's01-info-02':
            ldagent.tap(200, 292)
            time.sleep(0.5)
            continue
        if state == 's01-info-03':
            ldagent.tap(198, 204)
            time.sleep(0.5)
            continue
        if state == 's01-info-04':
            ldagent.tap(153, 361)
            time.sleep(0.5)
            continue
        if state == 's02-toc-00':
            if state_history[-1] != 's02-toc-01':
                ldagent.tap(149, 207)
                time.sleep(1)
                continue
            else:
                ldagent.tap(74, 268)
                time.sleep(0.5)
                continue
        if state == 's02-toc-01':
            ldagent.tap(150, 360)
            time.sleep(0.5)
            continue
        if state == 's02-toc-02':
            if state_history[-1] != 's02-toc-01':
                ldagent.tap(150, 240)
                time.sleep(1)
                continue
            else:
                ldagent.tap(73, 294)
                time.sleep(0.5)
                continue
        # if state == 's02-toc-03':
        #     ldagent.tap(150, 360)
        #     time.sleep(0.5)
        #     continue
        if state == 's02-toc-04':
            ldagent.tap(150, 360)
            time.sleep(0.5)
            continue
        if state == 's03-start-00':
            ldagent.tap(150, 248)
            time.sleep(0.5)
            continue
        if state == 's03-start-01':
            ldagent.tap(150, 340)
            time.sleep(5)
            flag_set.add(state)
            continue
        if state == 's05-name-00':
            ldagent.tap(150, 171)
            time.sleep(0.5)
            continue
        if state == 's05-name-01':
            ldagent.tap(150, 179)
            time.sleep(0.5)
            continue
        if state == 's05-name-02':
            for _ in range(10):
                ldagent.keyevent(67)
                time.sleep(0.2)
            if 'err-badname' in flag_set:
                flag_set.remove('err-badname')
            continue
        if state == 's05-name-02-empty':
            username = USERNAME.replace('{IDX}', '%03d' % user_idx)
            ldagent.input_text(username)
            user_idx += 1
            user_idx %= 1000
            with open('var/user_idx.txt', 'w') as f:
                f.write(str(user_idx))
            time.sleep(0.1)
            ldagent.tap(250, 364)
            time.sleep(0.5)
            continue
        if state == 's06-gacha1-00':
            ldagent.tap(150,200)
            time.sleep(0.5)
            continue
        if state == 's06-gacha1-01':
            ldagent.tap(150,312)
            time.sleep(6)
            continue
        # if state == 's06-gacha1-02':
        #     ldagent.tap()
        #     time.sleep(0.5)
        #     continue
        if state == 's06-gacha1-03':
            for _ in range(4):
                ldagent.tap(150,200)
                time.sleep(0.5)
            time.sleep(3.5)
            ldagent.tap(150,200)
            time.sleep(10)
            continue
        if state == 's06-gacha1-04':
            ldagent.swipe(150,300,150,100,50)
            time.sleep(10)
            continue
        # if state == 's06-gacha1-05':
        #     ldagent.tap(150,268)
        #     time.sleep(10)
        #     continue
        if state == 's06-gacha1-06':
            ldagent.tap(150,268)
            time.sleep(0.5)
            continue
        if state == 's06-gacha1-07':
            ldagent.tap(150,360)
            time.sleep(0.5)
            continue
        # if state == 's06-gacha1-08':
        #     ldagent.tap()
        #     time.sleep(0.5)
        #     continue
        if state == 's07-mission-00':
            ldagent.tap(273,347)
            time.sleep(5)
            continue
        # if state == 's07-mission-01':
        #     ldagent.tap(150,194)
        #     time.sleep(3)
        #     continue
        if state == 's07-mission-02':
            ldagent.tap(150,194)
            time.sleep(0.5)
            continue
        if state == 's07-mission-03':
            ldagent.tap(150,375)
            time.sleep(3)
            continue
        if state == 's07-mission-04':
            ldagent.tap(150,257)
            time.sleep(0.5)
            continue
        if state == 's08-gacha2-02':
            ldagent.tap(150,155)
            time.sleep(3)
            continue
        # if state == 's08-gacha2-03':
        #     ldagent.tap(150,313)
        #     time.sleep(5)
        #     continue
        if state == 's08-gacha2-04':
            ldagent.tap(150,313)
            time.sleep(5)
            continue

        if state == 's09-wonder-00':
            ldagent.tap(150,256)
            time.sleep(0.5)
            continue
        if state == 's09-wonder-01':
            ldagent.tap(150,373)
            time.sleep(0.5)
            continue
        if state == 's09-wonder-04':
            ldagent.tap(100,289)
            time.sleep(3)
            continue
        if state == 's09-wonder-10':
            ldagent.tap(150,373)
            time.sleep(0.5)
            continue
        if state == 's09-wonder-11':
            ldagent.tap(150,200)
            time.sleep(0.5)
            continue
        if state == 's09-wonder-12':
            ldagent.tap(184,257)
            time.sleep(0.5)
            continue
        if state == 's09-wonder-13':
            ldagent.tap(200,341)
            time.sleep(5)
            continue
        if state == 's09-wonder-14':
            ldagent.tap(184,250)
            time.sleep(5)
            continue
        if state == 's09-wonder-15':
            ldagent.tap(150,380)
            time.sleep(5)
            continue
        if state == 's09-wonder-16':
            ldagent.tap(150,373)
            time.sleep(0.5)
            continue

        if state == 's11-hourglass-00':
            ldagent.tap(200,311)
            time.sleep(0.5)
            continue
        if state == 's11-hourglass-01':
            ldagent.tap(200,340)
            time.sleep(10)
            continue

        if state == 's12-end-00':
            ldagent.tap(263,385)
            time.sleep(0.5)
            continue
        if state == 's12-end-01':
            ldagent.tap(161,325)
            time.sleep(0.5)
            continue
        if state == 's12-end-02':
            ldagent.tap(150,173)
            time.sleep(0.5)
            continue
        if state == 's12-end-03':
            ldagent.tap(150,327)
            time.sleep(0.5)
            continue


        if state == 'xxx-cont':
            ldagent.tap(150, 360)
            time.sleep(1)
            continue

        if state == 'xxx-dialog-lc':
            ldagent.tap(150, 318)
            time.sleep(0.5)
            continue
        if state == 'xxx-dialog-lw':
            ldagent.tap(150, 318)
            time.sleep(0.5)
            continue
        if state == 'xxx-dialog-lwc':
            ldagent.tap(200, 318)
            time.sleep(0.5)
            continue
        if state == 'xxx-dialog-lwr':
            ldagent.tap(200, 318)
            time.sleep(0.5)
            continue
        if state == 'xxx-dialog-lww':
            ldagent.tap(200, 318)
            time.sleep(0.5)
            continue

        if state == 'xxx-dialog-sc':
            ldagent.tap(150, 266)
            time.sleep(0.5)
            continue
        if state == 'xxx-dialog-swc':
            ldagent.tap(200, 266)
            time.sleep(0.5)
            continue
        if state == 'xxx-dialog-swr':
            ldagent.tap(200, 266)
            time.sleep(0.5)
            continue

        if state == 'xxx-gacha-00-charizard':
            if TARGET_PACK == 'pikachu':
                ldagent.tap(85,214)
                time.sleep(0.5)
                continue
            if TARGET_PACK == 'mewtwo':
                ldagent.tap(218,221)
                time.sleep(0.5)
                continue
            if TARGET_PACK == 'mew':
                ldagent.tap(150,347)
                time.sleep(0.5)
                continue
            ldagent.tap(150,200)
            time.sleep(0.5)
            continue
        if state == 'xxx-gacha-00-mew':
            if TARGET_PACK != 'mew':
                ldagent.tap(150,347)
                time.sleep(0.5)
                continue
            ldagent.tap(150,200)
            time.sleep(0.5)
            continue
        if state == 'xxx-gacha-00-mewtwo':
            if TARGET_PACK == 'charizard':
                ldagent.tap(85,214)
                time.sleep(0.5)
                continue
            if TARGET_PACK == 'pikachu':
                ldagent.tap(218,221)
                time.sleep(0.5)
                continue
            if TARGET_PACK == 'mew':
                ldagent.tap(150,347)
                time.sleep(0.5)
                continue
            ldagent.tap(150,200)
            time.sleep(0.5)
            continue
        if state == 'xxx-gacha-00-pikachu':
            if TARGET_PACK == 'mewtwo':
                ldagent.tap(85,214)
                time.sleep(0.5)
                continue
            if TARGET_PACK == 'charizard':
                ldagent.tap(218,221)
                time.sleep(0.5)
                continue
            if TARGET_PACK == 'mew':
                ldagent.tap(150,347)
                time.sleep(0.5)
                continue
            ldagent.tap(150,200)
            time.sleep(0.5)
            continue

        if state.startswith('xxx-gacha-01-'):
            if TARGET_PACK != state[13:]:
                ldagent.tap(150,348)
                time.sleep(0.5)
                continue
            ldagent.tap(150,313)
            time.sleep(6)
            continue

        if state.startswith('xxx-gacha-02-'):
            ldagent.tap(275,378)
            time.sleep(0.5)
            continue

        if state.startswith('xxx-gacha-03-'):
            ldagent.swipe(45,231,253,231,1000)
            flag_set.add('xxx-gacha-03')
            time.sleep(0.5)
            continue

        if state == 'xxx-gacha-04':
            ldagent.tap(275,378)
            flag_set.add('xxx-gacha-03')
            time.sleep(0.5)
            continue
        if state == 'xxx-gacha-04-x':
            ldagent.tap(275,378)
            flag_set.add('xxx-gacha-03')
            time.sleep(0.5)
            continue

        # gacha result
        if state == 'xxx-gacha-05':
            t = int(time.time())
            os.makedirs('gacha_result', exist_ok=True)
            ret_fn = os.path.join('gacha_result', f'{t}.png')
            cv2.imwrite(ret_fn, img)
            gacha_result = card_list.read_gacha_result(img)
            if set(gacha_result) & TARGET_CARD_SET:
                sys.exit(0)
            ldagent.tap(150,377)
            time.sleep(8)
            continue

        if state == 'xxx-home':
            if TARGET_PACK in ['charizard', 'pikachu', 'mewtwo']:
                ldagent.tap(185,154)
            if TARGET_PACK == 'mew':
                ldagent.tap(111,154)
            time.sleep(8)
            continue

        if state == 'xxx-msg':
            ldagent.tap(150,200)
            time.sleep(0.5)
            continue

        if state == 'xxx-noitem':
            ldagent.tap(100,280)
            time.sleep(0.5)
            continue

        if state == 'xxx-swipeup':
            ldagent.tap(275,378)
            flag_set.add(state)
            time.sleep(0.5)
            continue

        if state.startswith('xxx-tips'):
            ldagent.tap(150,377)
            time.sleep(3)
            continue

        # if state == 'center':
        #     ldagent.tap(150,200)
        #     time.sleep(0.5)
        #     continue
        # if state == 'skip':
        #     ldagent.tap(275,378)
        #     time.sleep(0.5)
        #     continue
        # if state == 'click-cont':
        #     ldagent.tap(150,377)
        #     time.sleep(8)
        #     continue

# state_data_list = []

# def load_state():
#     state_list = os.listdir(os.path.join('res', 'state'))
#     state_list = filter(lambda x: x.endswith('.max.png'), state_list)
#     state_list = map(lambda x: x[:-8], state_list)
#     state_list = list(state_list)
#     for state in state_list:
#         img_min_fn = os.path.join('res', 'state', f'{state}.min.png')
#         img_max_fn = os.path.join('res', 'state', f'{state}.max.png')
#         img_mask_fn = os.path.join('res', 'state', f'{state}.mask.png')
#         img_min = cv2.imread(img_min_fn).astype(np.float32)
#         img_max = cv2.imread(img_max_fn).astype(np.float32)
#         if os.path.exists(img_mask_fn):
#             # print(img_max_fn)
#             img_mask = cv2.imread(img_mask_fn, cv2.IMREAD_UNCHANGED).astype(np.float32)
#             # print(img_mask.shape)
#             assert(img_mask.shape[2] == 4)
#         else:
#             img_mask = None
#         state_data_list.append({
#             'state': state,
#             'img_min': img_min,
#             'img_max': img_max,
#             'img_mask': img_mask,
#         })

# def get_state(img):
#     diff, state = 1, 'UNKNOWN'
#     for state_data in state_data_list:
#         new_state = state_data['state']
#         img_min = state_data['img_min']
#         img_max = state_data['img_max']
#         img_mask = state_data['img_mask']
#         new_diff = _get_state_diff(img, img_min, img_max, img_mask)
#         # print(f'{new_state}: {new_diff}')
#         if new_diff < diff:
#             diff = new_diff
#             state = new_state
#     print(f'{state}: {diff}')
#     return state

# def _get_state_diff(img, img_min, img_max, img_mask, debug=False):
#     diff_max = img - img_max
#     diff_max = np.maximum(diff_max, 0)
#     diff_min = img_min - img
#     diff_min = np.maximum(diff_min, 0)
#     diff = np.maximum(diff_max, diff_min)

#     if debug:
#         cv2.imwrite('diff_max.png', diff_max)
#         cv2.imwrite('diff_min.png', diff_min)

#     if img_mask is not None:
#         mask = img_mask[:,:,3:4]
#         # mask = mask.reshape(mask.shape[:2])
#         mask = mask / 255
#         diff = diff * mask
#         mask_sum = mask.sum()
#         diff = diff.sum() / mask_sum / 3
#     else:
#         diff = diff.mean()

#     return diff

# def _check_state(score, state, img, img_key, xy, new_state):
#     diff = match_diff(img, xy, img_key)
#     print(f'{img_key}: {diff}')
#     if diff < score:
#         score = diff
#         state = new_state
#     return score, state

# img_key_to_img_dict = {}
# def match_diff(img, xy, img_key):
#     if img_key not in img_key_to_img_dict:
#         img_path = os.path.join('res', f'{img_key}.png')
#         img_key_to_img_dict[img_key] = cv2.imread(img_path)
#     imgg = img_key_to_img_dict[img_key]
#     h,w = imgg.shape[:2]
#     x,y = xy
#     diff = np.abs(img[y:y+h, x:x+w] - imgg)
#     diff = diff.mean()
#     return diff

if __name__ == '__main__':
    main()
