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
    try:
        if os.path.exists(USER_IDX_PATH):
            with open(USER_IDX_PATH, 'r') as f:
                user_idx = int(f.read())
    except:
        logger.error(f'DKZEUSMNFN user_idx load error')
        user_idx = 0

    # ldagent.config(config_data)
    my_ldagent = ldagent.get_ldagent(config_data)

    check_disk_space(config_data)

    ret = my_ldagent.lock_emu()
    if not ret:
        logger.error(f'FYPBSVTUKY emu is locked')
        sys.exit(1)
    # emu_lock_path = get_emu_lock_path(ldagent.LDPLAYER_PATH, str(ldagent.EMU_IDX))
    # logger.debug(f'XFLZMQZROH emu_lock_path={emu_lock_path}')
    # emu_lock = filelock.lock(emu_lock_path, f'{START_YYYYMMDDHHMMSS},{MY_PID}')
    # if emu_lock is None:
    #     logger.error(f'emu is locked: {ldagent.EMU_IDX}')
    #     sys.exit(1)

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

    # mywait
    last_mywait_time = time.time()
    def reset_mywait():
        nonlocal last_mywait_time
        last_mywait_time = time.time()
    def mywait(id):
        nonlocal last_mywait_time
        sec = config_data[id]
        while isinstance(sec, str):
            sec = config_data[sec]
        wait_time = last_mywait_time + sec + config_data['UIWAIT_OFFSET'] - time.time()
        wait_time = wait_time/30
        wait_time = max(1.1/30, wait_time) # one frame
        time.sleep(wait_time)
        last_mywait_time = time.time()

    while True:
        try:
            update_logger(config_data)
            logger.debug('MMNRYHUKFQ tick')

            if force_copyemu_resetapp:
                logger.debug(f'KQZSYHRWME force_copyemu')
                assert(force_copyemu_name!=None)
                my_ldagent.killemu()
                freemem_last_reset = time.time()
                emu_ok = False
                my_ldagent.copyemu(force_copyemu_name)
                force_copyemu_name = None
                force_resetapp = True
                force_rebootemu = False
                force_killapp = False
                force_copyemu_resetapp = False
                continue

            if force_rebootemu:
                logger.debug(f'KKTWULVBBG force_restart')
                my_ldagent.killemu()
                freemem_last_reset = time.time()
                emu_ok = False
                force_rebootemu = False
                force_killapp = False
                continue

            if force_resetapp and my_ldagent.is_emu_running():
                logger.debug(f'SRDWQJYJIR force_resetapp')
                my_ldagent.killapp()
                emu_ok = False
                my_ldagent.resetapp()
                force_resetapp = False
                force_killapp = False
                continue

            if force_killapp:
                logger.debug(f'NFTCLCTTHC force_killapp')
                my_ldagent.killapp()
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
                my_ldagent.recover()
                emu_ok = True
                flag_set = set()
                platinmods_speed = 1
                target_platinmods_speed = 3
                continue

            if state != 'UNKNOWN':
                state_history.append(state)
            state_history = state_history[-5:]

            img = my_ldagent.screencap().astype(np.float32)

            state = state_list.get_state(img)

            reset_mywait()

            if state == 'xxx-gacha-05-U':
                state = 'UNKNOWN'

            if config_data['DEBUG_IMG']:
                logger.debug(f'CNRSFFOMKV debug_img_idx={debug_img_idx}, state={state}')
                debug_img_fn = os.path.join(INSTANCE_VAR_FOLDER, 'debug_img', '%02d.png'%debug_img_idx)
                os.makedirs(os.path.dirname(debug_img_fn), exist_ok=True)
                if os.path.exists(debug_img_fn):
                    os.remove(debug_img_fn)
                img_encode = cv2.imencode('.png', img)[1]
                with open(debug_img_fn, 'wb') as f:
                    f.write(img_encode)
                # cv2.imwrite(debug_img_fn, img)
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
                    or ('s03-start-01-skip-anime' in flag_set) \
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
                    if not state.startswith('platinmods-menu-'):
                        my_ldagent.tap(18, 125)
                        time.sleep(TIME_SLEEP/2)
                    if target_platinmods_speed == 1:
                        my_ldagent.tap(35, 214)
                        platinmods_speed = 1
                        time.sleep(TIME_SLEEP/2)
                    if target_platinmods_speed == 2:
                        my_ldagent.tap(109, 214)
                        platinmods_speed = 2
                        time.sleep(TIME_SLEEP/2)
                    if target_platinmods_speed == 3:
                        my_ldagent.tap(182, 214)
                        platinmods_speed = 3
                        time.sleep(TIME_SLEEP/2)
                    my_ldagent.tap(170, 324)
                    time.sleep(TIME_SLEEP/2)
                    continue
                if (target_platinmods_speed == platinmods_speed):
                    if state.startswith('platinmods-menu-'):
                        my_ldagent.tap(170, 324)
                        time.sleep(TIME_SLEEP/2)
                        continue
                    
            # if 'xxx-gacha-03' in flag_set:
            #     # after gacha, may play fking animation
            #     if state not in ['xxx-gacha-05','s06-gacha1-03','s06-gacha1-04'] and (not state.startswith('xxx-gacha-03')):
            #         my_ldagent.tap(150,304)
            #         my_ldagent.tap(281,381)
            #         my_ldagent.tap(281,381)
            #         time.sleep(TIME_SLEEP/2)
            #         continue
            #     if state in ['xxx-gacha-05','s06-gacha1-03','s06-gacha1-04']:
            #         flag_set.remove('xxx-gacha-03')

            logger.debug(f'IWFCYLNYDB state={state} flag_set={flag_set}')

            # if (state == state_double_act_state) and (time.time() - state_double_act_time < STATE_DOUBLE_ACT_WAIT):
            #     is_double_act = True
            #     if state in state_list.state_to_forget_img_dict:
            #         mask_img = state_list.state_to_forget_img_dict[state]
            #         img_diff = np.abs(img - state_double_act_img)
            #         img_diff = img_diff * mask_img
            #         img_diff = img_diff.sum() / mask_img.sum() / img_diff.shape[2]
            #         logger.debug(f'LZKXOWTZMK img_diff={img_diff}')
            #         if img_diff > 5:
            #             is_double_act = False
            #     if is_double_act:
            #         logger.debug(f'AXTNCKYONS double_act')
            #         time.sleep(TIME_SLEEP/2)
            #         continue

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

            if state == 's01-info-00':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_INFO_OPEN_YEAR')
                state = 's01-info-01'

            if state == 's01-info-01':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_INFO_SELECT_YEAR')
                state = 's01-info-02'

            if state == 's01-info-02':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_INFO_OPEN_MONTH')
                state = 's01-info-03'

            if state == 's01-info-03':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_INFO_SELECT_MONTH')
                continue

            if state == 's01-info-05':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_INFO_OPEN_REGION')
                state = 's01-info-06'

            if state == 's01-info-06':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_INFO_SELECT_REGION')
                state = 's01-info-07'

            if state == 's01-info-07':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_INFO_REGION_OK')
                state = 's01-info-04'

            if state == 's01-info-04':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_INFO_OK_0')
                state = 'xxx-dialog-swc'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_INFO_OK_1')
                continue

            if state == 's02-toc-00':
                if check_cycle_loop_state in [None, 's12-end-00']:
                    check_cycle_loop_state = state
                    check_cycle_last_reset = time.time()

                if 's02-toc-01' not in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    mywait('UIWAIT_TOC_OPEN_TOC')
                    # state = 's02-toc-01'
                    continue
                    # my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                    # mywait('UIWAIT_TOC_CLOSE_TOC')
                    # state = 's02-toc-00'
                flag_set.discard('s02-toc-01')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                mywait('UIWAIT_TOC_AGREE_TOC')
                # state = 's02-toc-02'
                continue

            if state == 's02-toc-01':
                flag_set.add(state)

            if state == 's02-toc-02':
                if 's02-toc-01' not in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    mywait('UIWAIT_TOC_OPEN_PRIVACY')
                    # state = 's02-toc-01'
                    continue
                    # my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                    # mywait('UIWAIT_TOC_CLOSE_PRIVACY')
                    # state = 's02-toc-02'
                flag_set.discard('s02-toc-01')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                mywait('UIWAIT_TOC_AGREE_PRIVACY')
                # state = 's02-toc-04'
                continue

            if state == 's02-toc-04':
                if 's02-toc-04-remain' in flag_set:
                    flag_set.discard('s02-toc-04-remain')
                    time.sleep(TIME_SLEEP/2)
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_TOC_OK')
                flag_set.add('s02-toc-04-remain')
                continue
            flag_set.discard('s02-toc-04-remain')

            if state == 's03-start-00':
                if check_cycle_loop_state in [None, 's02-toc-00']:
                    check_cycle_loop_state = state
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_ACC_START')
                state = 's03-start-01'

            if state == 's03-start-01':
                flag_set.add('s03-start-01-skip-anime')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_ACC_NO_LINK')
                continue

            if 's03-start-01-skip-anime' in flag_set:
                # playing fking opening animation
                if state not in ['xxx-dialog-swc', 'xxx-dialog-sc', 'xxx-dialog-lw','s04-welcome-00']:
                    my_ldagent.tap(275,378)
                    my_ldagent.tap(275,378)
                    time.sleep(TIME_SLEEP/2)
                    continue
                if state == 's04-welcome-00':
                    flag_set.discard('s03-start-01-skip-anime')

            if state == 's04-welcome-00':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WELCOME_DIALOG_0')
                state = 's04-welcome-01'

            if state == 's04-welcome-01':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WELCOME_DIALOG_1')
                continue

            if state == 's05-name-00':
                if 's05-name-nonempty' in flag_set:
                    if state_history[-1] != state:
                        time.sleep(TIME_SLEEP/2)
                        continue
                    flag_set.discard('s05-name-nonempty')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_NAME_ICONNAME_INPUTBOX')
                state = 's05-name-01'

            if state == 's05-name-01':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_NAME_NAME_INPUTBOX')
                continue

            if state == 's05-name-02':
                # need double check
                for _ in range(10):
                    my_ldagent.keyevent(67)
                    time.sleep(0.2) # speed of typing
                time.sleep(TIME_SLEEP)
                continue

            if state == 's05-name-02-empty':
                flag_set.discard('err-badname')
                flag_set.discard('s05-name-nonempty')
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
                my_ldagent.input_text(username)
                user_idx += 1
                user_idx %= 10000
                try:
                    with open(USER_IDX_PATH, 'w') as f:
                        f.write(str(user_idx))
                except:
                    pass
                state = 's05-name-03'

            if state == 's05-name-03':
                if 'err-badname' in flag_set:
                    for _ in range(10):
                        my_ldagent.keyevent(67)
                        time.sleep(0.2) # speed of typing
                    time.sleep(TIME_SLEEP)
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                mywait('UIWAIT_NAME_NAME_OK')
                flag_set.add('s05-name-nonempty')
                continue # possible error msg here

            if state == 's05-name-04':
                if 'err-badname' in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    time.sleep(TIME_SLEEP)
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                mywait('UIWAIT_NAME_ICONNAME_OK_0')
                continue # possible error msg here

            if state == 's05-name-05':
                if 'err-badname' in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    time.sleep(TIME_SLEEP)
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                mywait('UIWAIT_NAME_ICONNAME_OK_1')
                continue

            if state == 's06-gacha1-00':
                flag_set.discard('s05-name-nonempty')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA1_SELECTPACK')
                state = 's06-gacha1-01'

            if state == 's06-gacha1-01':
                # [FIRST_SWIPE_UP_KILL_APP] kill app to avoid lock in swipe state
                if config_data['FIRST_SWIPE_UP_KILL_APP']:
                    flag_set.add('FIRST_SWIPE_UP_KILL_APP')
                # flag_set.add('s06-gacha1-03-combo') # 
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA1_CONFIRMPACK')
                continue # 'xxx-gacha-03-'

            if state == 's06-gacha1-03':
                # double confirm, mix with 'xxx-gacha-04'
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
                if 'xxx-gacha-03' in flag_set:
                    flag_set.discard('xxx-gacha-03')
                    for _ in range(12):
                        my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                        mywait('UIWAIT_COMMON_GACHA_RESULT_1CARD')
                    continue # 's06-gacha1-04', swipe up hell
                else:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                    time.sleep(TIME_SLEEP)
                    continue

            if state == 's06-gacha1-05':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA1_MSG')
                state = 's06-gacha1-06'

            if state == 's06-gacha1-06':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                # mywait('UIWAIT_GACHA1_CARDLIST_CLICK')
                time.sleep(TIME_SLEEP)
                continue

            if state == 's06-gacha1-07':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA1_NEXT')
                state = 'xxx-dialog-swc'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA1_END_WHITE')
                flag_set.add('target-s07')
                continue # long unknown stupid wait

            if state == 's07-mission-00':
                flag_set.discard('target-s07')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_MISSION_SE_BUTTON')
                state = 's07-mission-01'

            if state == 's07-mission-01':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_MISSION_MSG_0')
                state = 's07-mission-02'

            if state == 's07-mission-02':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_MISSION_CLICK_MISSION')
                state = 's07-mission-03'

            if state == 's07-mission-03':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_MISSION_CLICK_COMPLETE')
                state = 's07-mission-04'

            if state == 's07-mission-04':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_MISSION_OK')
                continue

            if state == 's08-gacha2-05':
                if 's08-gacha2-05' in state_history:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                    time.sleep(TIME_SLEEP)
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA2_MSG_0')
                state = 's08-gacha2-06'

            if state == 's08-gacha2-06':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA2_MSG_1')
                state = 's08-gacha2-02'

            if state == 's08-gacha2-02':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA2_CLICK_PACK')
                continue

            if state == 's08-gacha2-07':
                state = 'xxx-dialog-lc'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA2_DIALOG')
                state = 's08-gacha2-04'

            if state == 's08-gacha2-04':
                flag_set.add('GACHA2-ING')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                # mywait('UIWAIT_GACHA2_OPEN_PACK')
                time.sleep(TIME_SLEEP)
                flag_set.add('xxx-gacha-02-spam')
                continue
                # state = 'xxx-gacha-02-mewtwo'


            if state == 's09-wonder-00':
                # one more frame
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_UNLOCK')
                flag_set.add('s09-wonder-01-ok')
                state = 's09-wonder-01'

            if state == 's09-wonder-01':
                # short time fix with s09-wonder-00
                if ('s09-wonder-01-ok' not in flag_set) and (state_history[-1] != state):
                    time.sleep(TIME_SLEEP/2)
                    continue
                flag_set.discard('s09-wonder-01-ok')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_CONT')
                # s09-wonder-02
                continue

            if state == 's09-wonder-02':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_MSG_0')
                state = 's09-wonder-03'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_MSG_1')
                state = 's09-wonder-04'

            if state == 's09-wonder-04':
                # short time mix with s07-mission-00
                if 'target-s07' in flag_set:
                    time.sleep(TIME_SLEEP/2)
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_WONDER_BTN')
                # state = 's09-wonder-11'
                continue

            if state == 's09-wonder-11':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_MSG_2')
                state = 's09-wonder-17'

            if state == 's09-wonder-17':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_DIALOG_0')
                state = 's09-wonder-18'

            if state == 's09-wonder-18':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_DIALOG_1')
                state = 's09-wonder-19'

            if state == 's09-wonder-19':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_DIALOG_2')
                state = 's09-wonder-20'

            if state == 's09-wonder-20':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_DIALOG_3')
                state = 's09-wonder-21'

            if state == 's09-wonder-21':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_DIALOG_4')
                state = 's09-wonder-22'

            if state == 's09-wonder-22':
                # state = 'xxx-msg'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_MSG_3')
                state = 's09-wonder-12'

            if state == 's09-wonder-12':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_CLICK_WONDERITEM')
                state = 's09-wonder-13'

            # wonder shuffle SE skip btn
            if state == 's09-wonder-13':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_OK')
                flag_set.add('s09-wonder-13')
                continue

            # wonder 5 choose 1
            if ('s09-wonder-13' in flag_set) and (state != 's09-wonder-14'):
                state = 's09-wonder-23'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_SHUFFLE_SKIP')
                continue

            if state == 's09-wonder-14':
                flag_set.discard('s09-wonder-13')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_CLICK_CARD')
                state = 's09-wonder-15'

            if state == 's09-wonder-15':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_WONDER_CLICK_RESULT1')
                state = 'xxx-swipeup'

            if state == 's09-wonder-16':
                for _ in range(5):
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                    time.sleep(TIME_SLEEP/2)
                time.sleep(TIME_SLEEP)
                continue

            if state == 's10-tutorialend-00':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_TUTORIALEND_DIALOG_0')
                state = 's10-tutorialend-01'

            if state == 's10-tutorialend-01':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_TUTORIALEND_DIALOG_1')
                state = 's10-tutorialend-02'

            if state == 's10-tutorialend-02':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_TUTORIALEND_DIALOG_2')
                state = 's10-tutorialend-03'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_TUTORIALEND_MSG_0')
                state = 's10-tutorialend-04'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_TUTORIALEND_MSG_1')
                state = 's10-tutorialend-05'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_TUTORIALEND_MSG_2')
                continue


            if state == 's11-hourglass-02':
                flag_set.add('s11-hourglass')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA5_DIALOG_0')
                state = 's11-hourglass-04'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA5_MSG_0')
                flag_set.add('s11-hourglass-00-pass')
                state = 's11-hourglass-00'

            if state == 's11-hourglass-00':
                # double confirm
                if ('s11-hourglass-00-pass' not in flag_set) and (state_history[-1] != state):
                    time.sleep(TIME_SLEEP/2)
                    continue
                flag_set.discard('s11-hourglass-00-pass')
                flag_set.add('GACHA4-DONE')
                # btn 開封1包
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA5_BTN_0')
                state = 'xxx-msg'
                # msg 1個開包沙漏
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_MSG_SKIP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA5_MSG_1')
                state = 's11-hourglass-03'

            if state == 's11-hourglass-03':
                # dialog 開包沙漏可透過玩家等級提升
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA5_DIALOG_1')
                state = 'xxx-dialog-lwc'
                # dialog 購買特級護照
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA5_DIALOG_2')
                state = 's11-hourglass-01'

            if state == 's11-hourglass-01':
                # btn OK
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_GACHA5_BTN_1')
                flag_set.add('xxx-gacha-02-spam')
                continue

            if state == 's12-end-00':
                # remain
                if 's12-end-00-remain' in flag_set:
                    flag_set.discard('s12-end-00-remain')
                    time.sleep(TIME_SLEEP/2)
                    continue
                flag_set.add(state)
                if check_cycle_loop_state in [None, 's03-start-00']:
                    check_cycle_loop_state = state
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_END_CLICK_MENU')
                flag_set.add('s12-end-00-remain')
                flag_set.add('s12-end-01-pass')
                # state = 's12-end-01'
                continue
            flag_set.discard('s12-end-00-remain')

            if state == 's12-end-01':
                # remain
                if 's12-end-01-remain' in flag_set:
                    flag_set.discard('s12-end-01-remain')
                    time.sleep(TIME_SLEEP/2)
                    continue
                # short moment
                if (not 's12-end-01-pass' in flag_set) and (state_history[-1] != state):
                    time.sleep(TIME_SLEEP/2)
                    continue
                flag_set.discard('s12-end-01-pass')
                if 's12-end-00' in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'G_xy_list']))
                    mywait('UIWAIT_END_CLICK_OTHER')
                    flag_set.add('s12-end-01-remain')
                    flag_set.add('s12-end-02-pass')
                    # state = 's12-end-02'
                    continue
                else:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'R_xy_list']))
                    time.sleep(TIME_SLEEP)
                    continue
            flag_set.discard('s12-end-01-remain')

            if state == 's12-end-02':
                # remain
                if 's12-end-02-remain' in flag_set:
                    flag_set.discard('s12-end-02-remain')
                    time.sleep(TIME_SLEEP/2)
                    continue
                # short moment
                if (not 's12-end-02-pass' in flag_set) and (state_history[-1] != state):
                    time.sleep(TIME_SLEEP/2)
                    continue
                flag_set.discard('s12-end-02-pass')
                if 's12-end-00' in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'G_xy_list']))
                    mywait('UIWAIT_END_CLICK_ACCOUNT')
                    flag_set.add('s12-end-02-remain')
                    flag_set.add('s12-end-03-pass')
                    # state = 's12-end-03'
                    continue
                else:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'R_xy_list']))
                    time.sleep(TIME_SLEEP)
                    continue
            flag_set.discard('s12-end-02-remain')

            if state == 's12-end-03':
                # remain
                if 's12-end-03-remain' in flag_set:
                    flag_set.discard('s12-end-03-remain')
                    time.sleep(TIME_SLEEP/2)
                    continue
                # short moment
                if (not 's12-end-03-pass' in flag_set) and (state_history[-1] != state):
                    time.sleep(TIME_SLEEP/2)
                    continue
                flag_set.discard('s12-end-03-pass')
                if 's12-end-00' in flag_set:
                    flag_set.add(state)
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'G_xy_list']))
                    mywait('UIWAIT_END_CLICK_DEL')
                    state = 'xxx-dialog-lwr'
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'xy_list']))
                    mywait('UIWAIT_END_DIALOG_0')
                    state = 'xxx-dialog-swr'
                    flag_set.add('s12-end-03-confirm')
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'xy_list']))
                    # state = 'xxx-dialog-sc'
                    # loading here
                    time.sleep(TIME_SLEEP)
                    flag_set.add('s12-end-03-remain')
                    continue
                else:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'R_xy_list']))
                    time.sleep(TIME_SLEEP)
                    continue
            flag_set.discard('s12-end-03-remain')

            if state == 'xxx-dialog-swr':
                if 's12-end-03' in flag_set:
                    flag_set.add('s12-end-03-confirm')

            if state.startswith('xxx-gacha-00-'):
                # not stable
                if ('xxx-gacha-00-pass' not in flag_set) and (state_history[-1] != state):
                    logger.debug(f'KVIUGILTOC xxx-gacha-00- state_history[-1] != state')
                    time.sleep(TIME_SLEEP/2)
                    continue
                flag_set.discard('xxx-gacha-00-pass')
                state_pack = state[13:]
                color = XXX_GACHA_00_STATE_TARGET_TO_COLOR_DICT[(state_pack, TARGET_PACK)]
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'{color}_xy_list']))
                if state_pack != TARGET_PACK:
                    time.sleep(TIME_SLEEP)
                    continue
                flag_set.add('xxx-gacha-01-pass')
                mywait('UIWAIT_GACHA_SELECT_PACK')
                if flag_set & {'GACHA2-DONE','GACHA3-DONE','GACHA4-DONE'}:
                    state = f'xxx-gacha-01-{state_pack}'
                else:
                    continue

            if state.startswith('xxx-gacha-01-'):
                # double confirm
                if ('xxx-gacha-01-pass' not in flag_set) and (state_history[-1] != state):
                    time.sleep(TIME_SLEEP/2)
                    continue
                flag_set.discard('xxx-gacha-01-pass')
                state_pack = state[13:]
                if state_pack != TARGET_PACK:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    time.sleep(TIME_SLEEP)
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                mywait('UIWAIT_GACHA_CONFIRM_PACK')
                flag_set.add('xxx-gacha-02-spam')
                # state = f'xxx-gacha-02-{state_pack}'
                for i in range(6):
                    if f'GACHA{i}-DONE' in flag_set:
                        flag_set.discard(f'GACHA{i}-DONE')
                        flag_set.add(f'GACHA{i+1}-ING')
                time.sleep(TIME_SLEEP)
                continue

            if ('xxx-gacha-02-spam' in flag_set) and (not state.startswith('xxx-gacha-03-')):
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist['xxx-gacha-02-pikachu']['xy_list']))
                time.sleep(TIME_SLEEP)
                continue

            if state.startswith('xxx-gacha-02-'):
                state_pack = state[13:]
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_GACHA_PACK_RING')
                state = f'xxx-gacha-03-{state_pack}'

            if state.startswith('xxx-gacha-03-'):
                flag_set.discard('xxx-gacha-02-spam')
                # [FIRST_SWIPE_UP_KILL_APP] kill app to avoid lock in swipe state
                if 'FIRST_SWIPE_UP_KILL_APP' in flag_set:
                    force_killapp = True
                    continue
                action = state_list.state_to_action_dist[state]
                from_xy = _get_xy(action['from_xy_list'])
                to_xy = _get_xy(action['to_xy_list'])
                duration = int(action['duration'] / swipe_speed_factor)
                my_ldagent.swipe(*from_xy, *to_xy, duration)
                last_swipe_time = time.time()
                flag_set.add('xxx-gacha-03')
                time.sleep(TIME_SLEEP)
                continue # swipe may fail

            if (state == 'xxx-gacha-04') or (state == 'xxx-gacha-04-x'):
                flag_set.add('xxx-gacha-04')
                if 'xxx-gacha-03' in flag_set:
                    flag_set.discard('xxx-gacha-03')
                    for _ in range(4):
                        my_ldagent.tap(150,304)
                        my_ldagent.tap(281,381)
                        my_ldagent.tap(281,381)
                        mywait('UIWAIT_COMMON_GACHA_RESULT_1CARD')
                my_ldagent.tap(150,304)
                my_ldagent.tap(281,381)
                my_ldagent.tap(281,381)
                mywait('UIWAIT_COMMON_GACHA_RESULT_LASTCARD')
                continue

            # fking video
            if ('xxx-gacha-04' in flag_set) and (state == 'UNKNOWN'):
                my_ldagent.tap(150,304)
                my_ldagent.tap(281,381)
                my_ldagent.tap(281,381)
                mywait('UIWAIT_COMMON_GACHA_RESULT_LASTCARD')
                continue

            # gacha result
            if state == 'xxx-gacha-05':
                flag_set.discard('xxx-gacha-04')
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
                    flag_set.add('WONDER_SAINT')
                    # force_resetapp = True

                if ('WONDER_SAINT' in flag_set) and ('s11-hourglass' in flag_set):
                    force_resetapp = True
                    continue

                # ldagent.tap(150,377)
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_GACHA_RESULT_5CARD')
                continue

            if state == 'xxx-home':
                # double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
                if TARGET_PACK in ['charizard', 'pikachu', 'mewtwo']:
                    # ldagent.tap(185,154)
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['RB_xy_list']))
                if TARGET_PACK == 'mew':
                    # ldagent.tap(111,154)
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                mywait('UIWAIT_HOME_CLICK_PACK')
                flag_set.add('xxx-gacha-00-pass')
                # 'xxx-gacha-00-'
                continue

            if state == 'xxx-swipeup':
                for i in range(2,6):
                    if f'GACHA{i}-ING' in flag_set:
                        flag_set.discard(f'GACHA{i}-ING')
                        flag_set.add(f'GACHA{i}-DONE')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_SWIPEUP')
                state = 'xxx-cardlist'
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                mywait('UIWAIT_COMMON_CARDLIST')
                if 'GACHA3-DONE' in flag_set:
                    flag_set.add('xxx-gacha-01-pass')
                continue
                

            # if ('xxx-swipeup' in flag_set):
            #     # fking add img to album animation
            #     if state in ['UNKNOWN']:
            #         my_ldagent.tap(275,378)
            #         time.sleep(TIME_SLEEP)
            #         continue
            #     flag_set.remove('xxx-swipeup')

            if state in state_list.state_to_action_dist:
                action = state_list.state_to_action_dist[state]
                action_action = action['action']
                logger.debug(f'OLOWPQVZMD action={action_action}')
                # next_state_double_act_state = state
                # if state in ['s06-gacha1-03','s07-mission-02','s09-wonder-11','s09-wonder-12','s09-wonder-14','s09-wonder-16','xxx-tips16','xxx-tips25']:
                #     next_state_double_act_state = None
                if action['action'] == 'click':
                    xy = _get_xy(action['xy_list'])
                    my_ldagent.tap(*xy)
                    # state_double_act_state = next_state_double_act_state
                    # state_double_act_time = time.time()
                    # state_double_act_img = img
                    time.sleep(TIME_SLEEP)
                    continue
                if action['action'] == 'swipe':
                    from_xy = _get_xy(action['from_xy_list'])
                    to_xy = _get_xy(action['to_xy_list'])
                    duration = int(action['duration'] / swipe_speed_factor)
                    # duration = int(action['duration'])
                    my_ldagent.swipe(*from_xy, *to_xy, duration)
                    last_swipe_time = time.time()
                    time.sleep(TIME_SLEEP)
                    continue

            # if state == 'UNKNOWN':
            #     state_double_act_state = None
            #     continue
            
            time.sleep(TIME_SLEEP/2)

        except ldagent.LdAgentException as e:
            logger.error(f'MYBPMBYDXK LdAgentException: {e}')
            if config_data['ENABLE_REBOOT']:
                force_rebootemu = True
            else:
                force_killapp = True


def check_disk_space(config_data):
    if config_data['MIN_FREE_DISK_SPACE'] <= 0:
        return
    free_space = shutil.disk_usage(ldagent.get_ldplayer_path(config_data)).free
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
