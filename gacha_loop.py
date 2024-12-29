import common
import filelock
import os
import random
import sys
import time
import cv2
import ldagent
import numpy as np
import yaml
import argparse
import state_list
import card_list
import config
from my_logger import logger, update_logger
import const
import seed_backup as backuppy
import shutil

# YYYYMMDDHH = time.strftime('%Y%m%d%H', time.localtime(time.time()))

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
    parser.add_argument('config', type=str, default=None, nargs='?')
    parser.add_argument('--version', action='store_true')
    args = parser.parse_args()

    if args.version:
        # if os.path.exists(const.VERSION_FN):
        #     with open(const.VERSION_FN, 'r') as f:
        #         print(f.read())
        # else:
        #     print('dev')
        print(get_version())
        sys.exit(0)

    args_config = args.config
    if args_config is None:
        args_config = os.path.join(const.APP_PATH, 'config.yaml')
    args_config = os.path.abspath(args_config)

    config_data = config.get_config(args_config)
    update_logger(config_data)

    version = get_version()

    logger.debug(f'NLHFIUUXBS PTCPG-GL start version={version}')
    logger.debug(f'EOWVSWOTMF MY_PATH={const.MY_PATH}')
    logger.debug(f'KLZUCSPIFK config path={args_config}')
    logger.debug(f'JSOFIXCPAG config_data={config_data}')

    INSTANCE_ID = config_data['INSTANCE_ID']
    logger.debug(f'INSTANCE_ID={INSTANCE_ID}')

    TARGET_PACK = config_data['TARGET_PACK']
    TARGET_CARD_SET = set(config_data['TARGET_CARD_LIST'])
    USERNAME = config_data['USERNAME']

    START_YYYYMMDDHHMMSS = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
    MY_PID = os.getpid()

    swipe_speed_factor = config_data['SPEED_FACTOR']
    if config_data['ENABLE_PLATINMODS']:
        swipe_speed_factor = 1

    TIME_SLEEP = 0.5 / config_data['SPEED_FACTOR']
    logger.debug(f'IMLIDECFNW TIME_SLEEP={TIME_SLEEP}')
    if config_data['SWIPE_PACK_SEC'] is not None:
        SWIPE_PACK_MS = int(config_data['SWIPE_PACK_SEC'] * 1000)
    elif config_data['ENABLE_PLATINMODS']:
        SWIPE_PACK_MS = 1000
    else:
        SWIPE_PACK_MS = int(1000/config_data['SPEED_FACTOR'])
    logger.debug(f'KQOHOWKNBY SWIPE_PACK_MS={SWIPE_PACK_MS}')

    config_fn_lock_path = get_config_fn_lock_path(args_config)
    logger.debug(f'UKKDANILYL config_fn_lock_path={config_fn_lock_path}')
    config_fn_lock = filelock.lock(config_fn_lock_path, f'{START_YYYYMMDDHHMMSS},{MY_PID}')
    if config_fn_lock is None:
        logger.error(f'config file is locked: {args_config}')
        sys.exit(1)

    instance_lock_path = get_instance_lock_path(INSTANCE_ID)
    logger.debug(f'JEDVXLDIZW instance_lock_path={instance_lock_path}')
    instance_lock = filelock.lock(instance_lock_path, f'{START_YYYYMMDDHHMMSS},{MY_PID}')
    if instance_lock is None:
        logger.error(f'instance is locked: {INSTANCE_ID}')
        sys.exit(1)

    state_list_mask255f = None
    if config_data['ENABLE_PLATINMODS']:
        platinmods_mask255f = common.cv2_imread(os.path.join(const.MY_PATH, 'res', 'platinmods-mask.png'), flags=cv2.IMREAD_UNCHANGED).astype(np.float32)[:,:,3:4]
        state_list_mask255f = platinmods_mask255f

    state_list.load_state(state_list_mask255f)
    card_list.load_card_img()

    config.check(config_data)
    
    state_list.STATE_DETECT_THRESHOLD = float(config_data['STATE_DETECT_THRESHOLD'])

    APP_VAR_FOLDER = os.path.join(const.APP_PATH, 'var')
    logger.debug(f'APP_VAR_FOLDER={APP_VAR_FOLDER}')
    os.makedirs(APP_VAR_FOLDER, exist_ok=True)

    # SEED_EMU_BACKUP_PATH = os.path.join(APP_VAR_FOLDER, 'seed_emu_backup.ldbk')
    # logger.debug(f'SEED_EMU_BACKUP_PATH={SEED_EMU_BACKUP_PATH}')

    backup = backuppy.SeedBackup(config_data)
    backup.clear_old_backup()
    force_resetapp = False
    force_rebootemu = False
    force_killapp = False
    force_copyemu_resetapp = False
    force_copyemu_name = None

    INSTANCE_VAR_FOLDER = os.path.join(APP_VAR_FOLDER, 'instances', INSTANCE_ID)
    logger.debug(f'INSTANCE_VAR_FOLDER={INSTANCE_VAR_FOLDER}')
    os.makedirs(INSTANCE_VAR_FOLDER, exist_ok=True)
    USER_IDX_PATH = os.path.join(INSTANCE_VAR_FOLDER, 'user_idx.txt')
    user_idx = 0
    if os.path.exists(USER_IDX_PATH):
        with open(USER_IDX_PATH, 'r') as f:
            user_idx = int(f.read())

    ldagent.config(config_data)

    check_disk_space(config_data)

    emu_lock_path = get_emu_lock_path(ldagent.LDPLAYER_PATH, str(ldagent.EMU_IDX))
    logger.debug(f'XFLZMQZROH emu_lock_path={emu_lock_path}')
    emu_lock = filelock.lock(emu_lock_path, f'{START_YYYYMMDDHHMMSS},{MY_PID}')
    if emu_lock is None:
        logger.error(f'emu is locked: {ldagent.EMU_IDX}')
        sys.exit(1)

    flag_set = set()
    
    state_history = ['UNKNOWN']*10
    state = 'UNKNOWN'

    emu_ok = False

    debug_img_idx = 0

    # [EJUUQPPRST] check if the state go pass these states in order
    # - s02-toc-00
    # - s03-start-00
    # - s12-end-00
    check_cycle_loop_state = None
    check_cycle_last_reset = time.time()

    # [ZRTRNAFFLV] restart emu to free memory
    freemem_last_reset = time.time()

    state_double_act_state = None
    state_double_act_time = time.time()
    state_double_act_img = None
    STATE_DOUBLE_ACT_WAIT = 5
    # double_act_img = None
    # double_act_time = time.time()
    # DOUBLE_ACT_TIMEOUT = 5

    platinmods_speed = 1
    target_platinmods_speed = 3
    last_swipe_time = 0

    while True:
        try:
            update_logger(config_data)
            logger.debug('MMNRYHUKFQ tick')

            if force_copyemu_resetapp:
                logger.debug(f'KQZSYHRWME force_copyemu')
                assert(force_copyemu_name!=None)
                ldagent.killemu()
                freemem_last_reset = time.time()
                emu_ok = False
                ldagent.copyemu(force_copyemu_name)
                force_copyemu_name = None
                force_resetapp = True
                force_rebootemu = False
                force_killapp = False
                force_copyemu_resetapp = False
                continue

            if force_rebootemu:
                logger.debug(f'KKTWULVBBG force_restart')
                ldagent.killemu()
                freemem_last_reset = time.time()
                emu_ok = False
                force_rebootemu = False
                force_killapp = False
                continue

            if force_resetapp and ldagent.is_emu_running():
                logger.debug(f'SRDWQJYJIR force_resetapp')
                ldagent.killapp()
                emu_ok = False
                ldagent.resetapp()
                force_resetapp = False
                force_killapp = False
                continue

            if force_killapp:
                logger.debug(f'NFTCLCTTHC force_killapp')
                ldagent.killapp()
                emu_ok = False
                force_killapp = False
                continue

            # the bot did not finish the cycle of "create account" -> "gacha" -> "remove account"
            # there must be something wrong
            # force reset app to avoid infinite loop
            if (config_data['CHECK_CYCLE_SECONDS'] is not None) and (time.time() - check_cycle_last_reset > config_data['CHECK_CYCLE_SECONDS']):
                logger.debug(f'PNOCLZOWIW cycle timeout')
                check_cycle_last_reset = time.time()
                force_resetapp = True
                continue

            if not emu_ok:
                logger.debug(f'URNYXLHHXQ recover emu')
                ldagent.recover()
                emu_ok = True
                flag_set = set()
                platinmods_speed = 1
                target_platinmods_speed = 3
                continue

            if state != 'UNKNOWN':
                state_history.append(state)
            state_history = state_history[-5:]

            img = ldagent.screencap().astype(np.float32)

            state = state_list.get_state(img)

            if state == 'xxx-gacha-05-U':
                state = 'UNKNOWN'

            if config_data['DEBUG_IMG']:
                logger.debug(f'CNRSFFOMKV debug_img_idx={debug_img_idx}, state={state}')
                debug_img_fn = os.path.join(INSTANCE_VAR_FOLDER, 'debug_img', '%02d.png'%debug_img_idx)
                os.makedirs(os.path.dirname(debug_img_fn), exist_ok=True)
                cv2.imwrite(debug_img_fn, img)
                debug_img_idx += 1
                debug_img_idx %= 100

            # print(state_history, state)
            logger.debug(f'PSDLSJCDBB state_history={state_history}')
            logger.debug(f'WJPUTEHGOE state={state}')
            logger.debug(f'YAISJIINTI flag_set={flag_set}')

            if state == 'xxx-gacha-05-U':
                state = 'UNKNOWN'

            if (config_data['ENABLE_PLATINMODS']):
                if     (state in ['s06-gacha1-04']) \
                    or (state.startswith('xxx-gacha-03-')) \
                    or ('s03-start-01' in flag_set) \
                    or (time.time()-last_swipe_time<1):
                    target_platinmods_speed = 1
                elif (not state.startswith('platinmods-menu-')):
                    target_platinmods_speed = 3

                if state == 'platinmods-menu-1':
                    platinmods_speed = 1
                if state == 'platinmods-menu-2':
                    platinmods_speed = 2
                if state == 'platinmods-menu-3':
                    platinmods_speed = 3
                if (target_platinmods_speed != platinmods_speed):
                    if state.startswith('platinmods-menu-'):
                        if target_platinmods_speed == 1:
                            print('tap 35, 214')
                            ldagent.tap(35, 214)
                        if target_platinmods_speed == 2:
                            print('tap 109 214')
                            ldagent.tap(109, 214)
                        if target_platinmods_speed == 3:
                            print('tap 182, 214')
                            ldagent.tap(182, 214)
                        time.sleep(TIME_SLEEP/2)
                        continue
                    ldagent.tap(18, 125)
                    time.sleep(TIME_SLEEP/2)
                    continue
                if (target_platinmods_speed == platinmods_speed):
                    if state.startswith('platinmods-menu-'):
                        ldagent.tap(170, 324)
                        time.sleep(TIME_SLEEP/2)
                        continue
                    
            if 's03-start-01' in flag_set:
                # playing fking opening animation
                if state not in ['xxx-dialog-swc', 'xxx-dialog-sc', 'xxx-dialog-lw']:
                    ldagent.tap(275,378)
                    ldagent.tap(275,378)
                    time.sleep(TIME_SLEEP/2)
                    continue
                if state == 'xxx-dialog-lw':
                    flag_set.remove('s03-start-01')

            if 'xxx-gacha-03' in flag_set:
                # after gacha, may play fking animation
                if state not in ['xxx-gacha-05','s06-gacha1-03','s06-gacha1-04'] and (not state.startswith('xxx-gacha-03')):
                    ldagent.tap(150,304)
                    ldagent.tap(281,381)
                    ldagent.tap(281,381)
                    time.sleep(TIME_SLEEP/2)
                    continue
                if state in ['xxx-gacha-05','s06-gacha1-03','s06-gacha1-04']:
                    flag_set.remove('xxx-gacha-03')

            if 'xxx-swipeup' in flag_set:
                # fking add img to album animation
                if state in ['UNKNOWN']:
                    ldagent.tap(275,378)
                    time.sleep(TIME_SLEEP)
                    continue
                flag_set.remove('xxx-swipeup')

            logger.debug(f'IWFCYLNYDB state={state} flag_set={flag_set}')

            if (state == state_double_act_state) and (time.time() - state_double_act_time < STATE_DOUBLE_ACT_WAIT):
                is_double_act = True
                if state in state_list.state_to_forget_img_dict:
                    mask_img = state_list.state_to_forget_img_dict[state]
                    img_diff = np.abs(img - state_double_act_img)
                    img_diff = img_diff * mask_img
                    img_diff = img_diff.sum() / mask_img.sum() / img_diff.shape[2]
                    logger.debug(f'LZKXOWTZMK img_diff={img_diff}')
                    if img_diff > 5:
                        is_double_act = False
                if is_double_act:
                    logger.debug(f'AXTNCKYONS double_act')
                    time.sleep(TIME_SLEEP/2)
                    continue

            if state == 'err-badname':
                flag_set.add(state)

            # if 'err-badname' in flag_set:
            #     if state == 'xxx-dialog-sc':
            #         state = 's05-name-00'
            #     if state == 'xxx-dialog-swc':
            #         ldagent.tap(150, 179)
            #         time.sleep(TIME_SLEEP)
            #         state = 's05-name-02'

            if state == 'err-launch-00':
                force_resetapp = True
                continue

            if state == 'err-launch-01':
                force_resetapp = True
                continue

            if state == 'err-nostoredata':
                force_resetapp = True
                continue

            if state == 's00-cover':
                check_disk_space(config_data)

                # just after del account
                if 's12-end-03-confirm' in flag_set:
                    flag_set = set()

                # [ZRTRNAFFLV] restart emu to free memory
                if      config_data['ENABLE_REBOOT'] \
                    and (config_data['FREEMEM_SECONDS'] is not None) \
                    and (time.time() - freemem_last_reset > config_data['FREEMEM_SECONDS']):
                    logger.debug(f'OOHKRSARJM freemem')
                    force_rebootemu = True
                    continue

            if state == 's02-toc-00':
                if check_cycle_loop_state in [None, 's12-end-00']:
                    check_cycle_loop_state = state
                    check_cycle_last_reset = time.time()

                if 's02-toc-01' not in flag_set:
                    # ldagent.tap(149, 207)
                    ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    state_double_act_state = state
                    state_double_act_time = time.time()
                    state_double_act_img = img
                    time.sleep(TIME_SLEEP)
                    continue
                else:
                    # ldagent.tap(74, 268)
                    flag_set.remove('s02-toc-01')
                    ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                    state_double_act_state = state
                    state_double_act_time = time.time()
                    state_double_act_img = img
                    time.sleep(TIME_SLEEP)
                    continue

            if state == 's02-toc-01':
                flag_set.add(state)

            if state == 's02-toc-02':
                if 's02-toc-01' not in flag_set:
                    # ldagent.tap(150, 240)
                    ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    state_double_act_state = state
                    state_double_act_time = time.time()
                    state_double_act_img = img
                    time.sleep(TIME_SLEEP)
                    continue
                else:
                    # ldagent.tap(73, 294)
                    flag_set.remove('s02-toc-01')
                    ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                    state_double_act_state = state
                    state_double_act_time = time.time()
                    state_double_act_img = img
                    time.sleep(TIME_SLEEP)
                    continue

            if state == 's03-start-00':
                # need double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
                if check_cycle_loop_state in [None, 's02-toc-00']:
                    check_cycle_loop_state = state

            if state == 's03-start-01':
                flag_set.add(state)

            if state == 's05-name-00':
                # need double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue

            if state == 's05-name-01':
                # need double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue

            if state == 's05-name-02':
                # need double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
                for _ in range(10):
                    ldagent.keyevent(67)
                    time.sleep(0.2) # speed of typing
                state_double_act_state = state
                state_double_act_time = time.time()
                state_double_act_img = img
                time.sleep(TIME_SLEEP)
                continue

            if state == 's05-name-02-empty':
                # need double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
                if 'err-badname' in flag_set:
                    flag_set.remove('err-badname')
                yyyymmddhhmmss = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
                username = USERNAME
                username = username.replace('{IDX}', '%03d' % (user_idx%1000))
                username = username.replace('{IDX1}', '%01d' % (user_idx%10))
                username = username.replace('{IDX2}', '%02d' % (user_idx%100))
                username = username.replace('{IDX3}', '%03d' % (user_idx%1000))
                username = username.replace('{IDX4}', '%04d' % (user_idx%10000))
                username = username.replace('{YYYY}', yyyymmddhhmmss[:4])
                username = username.replace('{YY}', yyyymmddhhmmss[2:4])
                username = username.replace('{MM}', yyyymmddhhmmss[4:6])
                username = username.replace('{DD}', yyyymmddhhmmss[6:8])
                username = username.replace('{hh}', yyyymmddhhmmss[8:10])
                username = username.replace('{mm}', yyyymmddhhmmss[10:12])
                username = username.replace('{ss}', yyyymmddhhmmss[12:14])
                logger.debug(f'DCMMMGVEHA username={username}')
                ldagent.input_text(username)
                user_idx += 1
                user_idx %= 10000
                with open(USER_IDX_PATH, 'w') as f:
                    f.write(str(user_idx))
                state_double_act_state = state
                state_double_act_time = time.time()
                state_double_act_img = img
                time.sleep(TIME_SLEEP)
                # ldagent.tap(250, 364)
                # ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                # time.sleep(TIME_SLEEP)
                continue

            if state == 's05-name-03':
                if 'err-badname' in flag_set:
                    for _ in range(10):
                        ldagent.keyevent(67)
                        time.sleep(0.2) # speed of typing
                    state_double_act_state = state
                    state_double_act_time = time.time()
                    state_double_act_img = img
                    time.sleep(TIME_SLEEP)
                    continue
                ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                state_double_act_state = state
                state_double_act_time = time.time()
                state_double_act_img = img
                time.sleep(TIME_SLEEP)
                continue

            if state == 's05-name-04':
                if 'err-badname' in flag_set:
                    ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    state_double_act_state = state
                    state_double_act_time = time.time()
                    state_double_act_img = img
                    time.sleep(TIME_SLEEP)
                    continue
                ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                state_double_act_state = state
                state_double_act_time = time.time()
                state_double_act_img = img
                time.sleep(TIME_SLEEP)
                continue

            if state == 's05-name-05':
                if 'err-badname' in flag_set:
                    ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    state_double_act_state = state
                    state_double_act_time = time.time()
                    state_double_act_img = img
                    time.sleep(TIME_SLEEP)
                    continue
                ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                state_double_act_state = state
                state_double_act_time = time.time()
                state_double_act_img = img
                time.sleep(TIME_SLEEP)
                continue

            if state == 's11-hourglass-00':
                # double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue

            if state == 's12-end-00':
                if time.time() - last_s12_end_00 < 1:
                    # double click
                    continue
                if check_cycle_loop_state in [None, 's03-start-00']:
                    check_cycle_loop_state = state

            if state == 's12-end-03':
                flag_set.add(state)

            if state == 'xxx-dialog-swr':
                if 's12-end-03' in flag_set:
                    flag_set.add('s12-end-03-confirm')

            if state.startswith('xxx-gacha-00-'):
                # need double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
                state_pack = state[13:]
                color = XXX_GACHA_00_STATE_TARGET_TO_COLOR_DICT[(state_pack, TARGET_PACK)]
                ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'{color}_xy_list']))
                state_double_act_state = state
                state_double_act_time = time.time()
                state_double_act_img = img
                time.sleep(TIME_SLEEP)
                continue

            if state.startswith('xxx-gacha-01-'):
                if TARGET_PACK != state[13:]:
                    # ldagent.tap(150,348)
                    ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    state_double_act_state = state
                    state_double_act_time = time.time()
                    state_double_act_img = img
                    time.sleep(TIME_SLEEP)
                    continue
                # ldagent.tap(150,313)
                ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                state_double_act_state = state
                state_double_act_time = time.time()
                state_double_act_img = img
                time.sleep(TIME_SLEEP)
                continue

            if state.startswith('xxx-gacha-03-'):
                flag_set.add('xxx-gacha-03')

            if state == 'xxx-gacha-04':
                flag_set.add('xxx-gacha-03')

            if state == 'xxx-gacha-04-x':
                flag_set.add('xxx-gacha-03')

            # gacha result
            if state == 'xxx-gacha-05':
                check_disk_space(config_data)
                t = int(time.time())
                logger.debug(f'ZNHRHBHGMT GACHA_RESULT: {t}')
                gacha_result_folder = os.path.join(const.APP_PATH, 'gacha_result')
                os.makedirs(gacha_result_folder, exist_ok=True)
                ret_fn = os.path.join(gacha_result_folder, f'{t}.png')
                cv2.imwrite(ret_fn, img)
                gacha_result = card_list.read_gacha_result(img)
                is_target = len(set(gacha_result) & TARGET_CARD_SET)>0
                logger.debug(f'OKTLVAGTGC is_target: {is_target}')
                all_wonder = gacha_result
                all_wonder = map(is_wonder, all_wonder)
                all_wonder = all(all_wonder)
                logger.debug(f'ZQFNRKRJXO all_wonder: {all_wonder}')
                all_rare = gacha_result
                all_rare = map(is_rare, all_rare)
                all_rare = all(all_rare)
                logger.debug(f'CJAIBNJRCL all_rare: {all_rare}')

                handle_way = 'IGNORE'
                if (not all_rare) and is_target and all_wonder:
                    handle_way = config_data['HANDLE_WONDER_TARGET_PACK']
                if (not all_rare) and is_target and (not all_wonder):
                    handle_way = config_data['HANDLE_NONWONDER_TARGET_PACK']
                if all_rare and (not is_target) and all_wonder:
                    handle_way = config_data['HANDLE_WONDER_RARE_PACK']
                if all_rare and (not is_target) and (not all_wonder):
                    handle_way = config_data['HANDLE_NONWONDER_RARE_PACK']
                if all_rare and is_target and all_wonder:
                    handle_way = config_data['HANDLE_WONDER_TARGET_RARE_PACK']
                if all_rare and is_target and (not all_wonder):
                    handle_way = config_data['HANDLE_NONWONDER_TARGET_RARE_PACK']

                logger.debug(f'HYJJPGIZRN handle_way: {handle_way}')

                if handle_way == 'STOP':
                    logger.debug(f'YXJNLZDDAN STOP')
                    sys.exit(0)
                if handle_way == 'BACKUP':
                    logger.debug(f'PUOWNPVFXS BACKUP')
                    force_copyemu_name = config_data['LD_EMU_NAME'] + '-' + str(t)
                    force_copyemu_resetapp = True
                    continue

                exist_cost4 = any(map(is_cost4, gacha_result))
                logger.debug(f'DBGPBUKKWV exist_cost4: {exist_cost4}')

                # when it is cost-4 pack, reset app without remove account
                # let other player to get the wonder pack
                if config_data['WONDER_SAINT'] and exist_cost4 and all_wonder:
                    logger.debug(f'KRVQOASGCP WONDER_SAINT')
                    force_resetapp = True
                    continue

                # ldagent.tap(150,377)
                ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                state_double_act_state = state
                state_double_act_time = time.time()
                state_double_act_img = img
                time.sleep(TIME_SLEEP)
                continue

            if state == 'xxx-home':
                if TARGET_PACK in ['charizard', 'pikachu', 'mewtwo']:
                    # ldagent.tap(185,154)
                    ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['RB_xy_list']))
                if TARGET_PACK == 'mew':
                    # ldagent.tap(111,154)
                    ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                state_double_act_state = state
                state_double_act_time = time.time()
                state_double_act_img = img
                time.sleep(TIME_SLEEP)
                continue

            if state == 'xxx-swipeup':
                flag_set.add(state)

            if state in state_list.state_to_action_dist:
                action = state_list.state_to_action_dist[state]
                action_action = action['action']
                logger.debug(f'OLOWPQVZMD action={action_action}')
                next_state_double_act_state = state
                if state in ['s06-gacha1-03','s09-wonder-11','s09-wonder-12','s09-wonder-14','s09-wonder-16','xxx-tips16','xxx-tips25']:
                    next_state_double_act_state = None
                if action['action'] == 'click':
                    xy = _get_xy(action['xy_list'])
                    ldagent.tap(*xy)
                    state_double_act_state = next_state_double_act_state
                    state_double_act_time = time.time()
                    state_double_act_img = img
                    time.sleep(TIME_SLEEP)
                    continue
                if action['action'] == 'swipe':
                    from_xy = _get_xy(action['from_xy_list'])
                    to_xy = _get_xy(action['to_xy_list'])
                    # duration = int(action['duration'] / config_data['SPEED_FACTOR'])
                    duration = int(action['duration'])
                    ldagent.swipe(*from_xy, *to_xy, duration)
                    time.sleep(TIME_SLEEP)
                    continue

            if state == 'UNKNOWN':
                state_double_act_state = None
                continue

        except ldagent.LdAgentException as e:
            logger.error(f'MYBPMBYDXK LdAgentException: {e}')
            if config_data['ENABLE_REBOOT']:
                force_rebootemu = True
            else:
                force_killapp = True


def check_disk_space(config_data):
    if config_data['MIN_FREE_DISK_SPACE'] <= 0:
        return
    free_space = shutil.disk_usage(ldagent.LDPLAYER_PATH).free
    if free_space < config_data['MIN_FREE_DISK_SPACE']:
        logger.error(f'XOCKTBIWKG not enough disk space: {free_space}')
        sys.exit(1)

RARE_SUFFIX_LIST = ['_UR', '_IM', '_SR', '_SAR', '_AR']
def is_rare(card_id):
    for suffix in RARE_SUFFIX_LIST:
        if card_id.endswith(suffix):
            return True
    return False

WONDER_SUFFIX_LIST = ['_SR', '_SAR', '_AR', '_RR', '_R', '_U', '_C']
def is_wonder(card_id):
    for suffix in WONDER_SUFFIX_LIST:
        if card_id.endswith(suffix):
            return True
    return False

COST4_SUFFIX_LIST = ['_SR', '_SAR']
def is_cost4(card_id):
    for suffix in COST4_SUFFIX_LIST:
        if card_id.endswith(suffix):
            return True
    return False


def get_config_fn_lock_path(config_fn):
    return f'{config_fn}.lock'

def get_emu_lock_path(ldplayer_path, emu_name):
    return os.path.join(ldplayer_path, 'ptcgp-gl', 'emus', emu_name, 'lock')

def get_instance_lock_path(instance_id):
    return os.path.join(const.APP_PATH, 'var', 'instances', instance_id, 'lock')

def get_version():
    if os.path.exists(const.VERSION_FN):
        with open(const.VERSION_FN, 'rt') as f:
            return f.read().strip()
    else:
        return 'dev'
    

def _get_xy(xy_list):
    idx = random.randint(0, len(xy_list)-1)
    return xy_list[idx]

XXX_GACHA_00_STATE_TARGET_TO_COLOR_DICT = {
    ('charizard','pikachu'): 'B',
    ('charizard','charizard'): 'G',
    ('charizard','mewtwo'): 'RG',
    ('charizard','mew'): 'R',
    ('mewtwo','charizard'): 'B',
    ('mewtwo','mewtwo'): 'G',
    ('mewtwo','pikachu'): 'RG',
    ('mewtwo','mew'): 'R',
    ('pikachu','mewtwo'): 'B',
    ('pikachu','pikachu'): 'G',
    ('pikachu','charizard'): 'RG',
    ('pikachu','mew'): 'R',
    ('mew','mew'): 'G',
    ('mew','charizard'): 'R',
    ('mew','mewtwo'): 'R',
    ('mew','pikachu'): 'R',
}

if __name__ == '__main__':
    main()
