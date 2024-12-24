import filelock
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

    TIME_SLEEP = 0.5 / config_data['SPEED_FACTOR']
    logger.debug(f'IMLIDECFNW TIME_SLEEP={TIME_SLEEP}')
    if config_data['SWIPE_PACK_SEC'] is not None:
        SWIPE_PACK_MS = int(config_data['SWIPE_PACK_SEC'] * 1000)
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

    state_list.load_state()
    card_list.load_card_img()

    config.check(config_data)

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

    # [EJUUQPPRST] check if the state go pass these states in order
    # - s02-toc-00
    # - s03-start-00
    # - s12-end-00
    check_cycle_loop_state = None
    check_cycle_last_reset = time.time()

    # [ZRTRNAFFLV] restart emu to free memory
    freemem_last_reset = time.time()

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
                continue

            if state != 'UNKNOWN':
                state_history.append(state)
            state_history = state_history[-5:]

            img = ldagent.screencap().astype(np.float32)

            # old_state = None
            # while True:
            #     state = state_list.get_state(img)
            #     if state == old_state:
            #         break
            #     old_state = state
            #     time.sleep(0.1)
            state = state_list.get_state(img)

            # print(state_history, state)
            logger.debug(f'PSDLSJCDBB state_history={state_history}')
            logger.debug(f'WJPUTEHGOE state={state}')
            logger.debug(f'YAISJIINTI flag_set={flag_set}')

            if state == 'xxx-gacha-05-U':
                state = 'UNKNOWN'

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
                if state not in ['xxx-cont']:
                    # ldagent.tap(275,378)
                    time.sleep(TIME_SLEEP/2)
                    continue
                flag_set.remove('xxx-swipeup')

            if state == 'err-badname':
                ldagent.tap(150, 280)
                flag_set.add(state)
                time.sleep(TIME_SLEEP)
                continue
            if 'err-badname' in flag_set:
                if state == 'xxx-dialog-sc':
                    state = 's05-name-00'
                if state == 'xxx-dialog-swc':
                    ldagent.tap(150, 179)
                    time.sleep(TIME_SLEEP)
                    state = 's05-name-02'

            logger.debug(f'IWFCYLNYDB state={state}')
            logger.debug(f'IWFCYLNYDB flag_set={flag_set}')

            if state == 'err-launch-00':
                force_resetapp = True
                continue
                # ldagent.tap(150, 247)
                # time.sleep(TIME_SLEEP)
                # continue
            if state == 'err-launch-01':
                force_resetapp = True
                continue
                # ldagent.tap(200, 277)
                # time.sleep(TIME_SLEEP)
                # continue

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

                ldagent.tap(150, 200)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's01-info-00':
                ldagent.tap(100, 292)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's01-info-01':
                ldagent.tap(100, 196)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's01-info-02':
                ldagent.tap(200, 292)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's01-info-03':
                ldagent.tap(198, 204)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's01-info-04':
                ldagent.tap(153, 361)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's02-toc-00':
                if check_cycle_loop_state in [None, 's12-end-00']:
                    check_cycle_loop_state = state
                    check_cycle_last_reset = time.time()
                if state_history[-1] != 's02-toc-01':
                    ldagent.tap(149, 207)
                    time.sleep(TIME_SLEEP)
                    continue
                else:
                    ldagent.tap(74, 268)
                    time.sleep(TIME_SLEEP)
                    continue
            if state == 's02-toc-01':
                ldagent.tap(150, 360)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's02-toc-02':
                if state_history[-1] != 's02-toc-01':
                    ldagent.tap(150, 240)
                    time.sleep(TIME_SLEEP)
                    continue
                else:
                    ldagent.tap(73, 294)
                    time.sleep(TIME_SLEEP)
                    continue
            # if state == 's02-toc-03':
            #     ldagent.tap(150, 360)
            #     time.sleep(TIME_SLEEP)
            #     continue
            if state == 's02-toc-04':
                ldagent.tap(150, 360)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's03-start-00':
                if check_cycle_loop_state in [None, 's02-toc-00']:
                    check_cycle_loop_state = state
                ldagent.tap(150, 248)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's03-start-01':
                ldagent.tap(150, 340)
                flag_set.add(state)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's05-name-00':
                # need double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
                ldagent.tap(150, 171)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's05-name-01':
                ldagent.tap(150, 179)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's05-name-02':
                # need double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
                for _ in range(10):
                    ldagent.keyevent(67)
                    time.sleep(0.2) # speed of typing
                if 'err-badname' in flag_set:
                    flag_set.remove('err-badname')
                continue
            if state == 's05-name-02-empty':
                # need double check
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
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
                time.sleep(TIME_SLEEP)
                ldagent.tap(250, 364)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's06-gacha1-00':
                ldagent.tap(150,200)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's06-gacha1-01':
                ldagent.tap(150,312)
                time.sleep(TIME_SLEEP)
                continue
            # if state == 's06-gacha1-02':
            #     ldagent.tap()
            #     time.sleep(TIME_SLEEP)
            #     continue
            if state == 's06-gacha1-03':
                ldagent.tap(150,200)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's06-gacha1-04':
                ldagent.swipe(150,300,150,100,int(50/config_data['SPEED_FACTOR']))
                time.sleep(TIME_SLEEP)
                continue
            # if state == 's06-gacha1-05':
            #     ldagent.tap(150,268)
            #     time.sleep(10)
            #     continue
            if state == 's06-gacha1-06':
                ldagent.tap(150,268)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's06-gacha1-07':
                ldagent.tap(150,360)
                time.sleep(TIME_SLEEP)
                continue
            # if state == 's06-gacha1-08':
            #     ldagent.tap()
            #     time.sleep(TIME_SLEEP)
            #     continue
            if state == 's07-mission-00':
                ldagent.tap(273,347)
                time.sleep(TIME_SLEEP)
                continue
            # if state == 's07-mission-01':
            #     ldagent.tap(150,194)
            #     time.sleep(3)
            #     continue
            if state == 's07-mission-02':
                ldagent.tap(150,194)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's07-mission-03':
                ldagent.tap(150,375)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's07-mission-04':
                ldagent.tap(150,257)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's08-gacha2-02':
                ldagent.tap(150,155)
                time.sleep(TIME_SLEEP)
                continue
            # if state == 's08-gacha2-03':
            #     ldagent.tap(150,313)
            #     time.sleep(5)
            #     continue
            if state == 's08-gacha2-04':
                ldagent.tap(150,313)
                time.sleep(TIME_SLEEP)
                continue

            if state == 's09-wonder-00':
                ldagent.tap(150,256)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's09-wonder-01':
                ldagent.tap(150,373)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's09-wonder-04':
                ldagent.tap(100,289)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's09-wonder-10':
                ldagent.tap(150,373)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's09-wonder-11':
                ldagent.tap(150,200)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's09-wonder-12':
                ldagent.tap(184,257)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's09-wonder-13':
                ldagent.tap(200,341)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's09-wonder-14':
                ldagent.tap(184,250)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's09-wonder-15':
                ldagent.tap(150,380)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's09-wonder-16':
                ldagent.tap(150,373)
                time.sleep(TIME_SLEEP)
                continue

            if state == 's11-hourglass-00':
                if state_history[-1] != state:
                    time.sleep(TIME_SLEEP/2)
                    continue
                ldagent.tap(200,311)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's11-hourglass-01':
                ldagent.tap(200,340)
                time.sleep(TIME_SLEEP)
                continue

            if state == 's12-end-00':
                if check_cycle_loop_state in [None, 's03-start-00']:
                    check_cycle_loop_state = state
                ldagent.tap(263,385)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's12-end-01':
                ldagent.tap(161,325)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's12-end-02':
                ldagent.tap(150,173)
                time.sleep(TIME_SLEEP)
                continue
            if state == 's12-end-03':
                flag_set.add(state)
                ldagent.tap(150,327)
                time.sleep(TIME_SLEEP)
                continue


            if state == 'xxx-cont':
                ldagent.tap(150, 360)
                time.sleep(TIME_SLEEP)
                continue

            if state == 'xxx-dialog-lc':
                ldagent.tap(150, 318)
                time.sleep(TIME_SLEEP)
                continue
            if state == 'xxx-dialog-lw':
                ldagent.tap(150, 318)
                time.sleep(TIME_SLEEP)
                continue
            if state == 'xxx-dialog-lwc':
                ldagent.tap(200, 318)
                time.sleep(TIME_SLEEP)
                continue
            if state == 'xxx-dialog-lwr':
                ldagent.tap(200, 318)
                time.sleep(TIME_SLEEP)
                continue
            if state == 'xxx-dialog-lww':
                ldagent.tap(200, 318)
                time.sleep(TIME_SLEEP)
                continue

            if state == 'xxx-dialog-sc':
                ldagent.tap(150, 266)
                time.sleep(TIME_SLEEP)
                continue
            if state == 'xxx-dialog-swc':
                ldagent.tap(200, 266)
                time.sleep(TIME_SLEEP)
                continue
            if state == 'xxx-dialog-swr':
                if 's12-end-03' in flag_set:
                    flag_set.add('s12-end-03-confirm')
                ldagent.tap(200, 266)
                time.sleep(TIME_SLEEP)
                continue

            if state == 'xxx-gacha-00-charizard':
                if TARGET_PACK == 'pikachu':
                    ldagent.tap(85,214)
                    time.sleep(TIME_SLEEP)
                    continue
                if TARGET_PACK == 'mewtwo':
                    ldagent.tap(218,221)
                    time.sleep(TIME_SLEEP)
                    continue
                if TARGET_PACK == 'mew':
                    ldagent.tap(150,347)
                    time.sleep(TIME_SLEEP)
                    continue
                ldagent.tap(150,200)
                time.sleep(TIME_SLEEP)
                continue
            if state == 'xxx-gacha-00-mew':
                if TARGET_PACK != 'mew':
                    ldagent.tap(150,347)
                    time.sleep(TIME_SLEEP)
                    continue
                ldagent.tap(150,200)
                time.sleep(TIME_SLEEP)
                continue
            if state == 'xxx-gacha-00-mewtwo':
                if TARGET_PACK == 'charizard':
                    ldagent.tap(85,214)
                    time.sleep(TIME_SLEEP)
                    continue
                if TARGET_PACK == 'pikachu':
                    ldagent.tap(218,221)
                    time.sleep(TIME_SLEEP)
                    continue
                if TARGET_PACK == 'mew':
                    ldagent.tap(150,347)
                    time.sleep(TIME_SLEEP)
                    continue
                ldagent.tap(150,200)
                time.sleep(TIME_SLEEP)
                continue
            if state == 'xxx-gacha-00-pikachu':
                if TARGET_PACK == 'mewtwo':
                    ldagent.tap(85,214)
                    time.sleep(TIME_SLEEP)
                    continue
                if TARGET_PACK == 'charizard':
                    ldagent.tap(218,221)
                    time.sleep(TIME_SLEEP)
                    continue
                if TARGET_PACK == 'mew':
                    ldagent.tap(150,347)
                    time.sleep(TIME_SLEEP)
                    continue
                ldagent.tap(150,200)
                time.sleep(TIME_SLEEP)
                continue

            if state.startswith('xxx-gacha-01-'):
                if TARGET_PACK != state[13:]:
                    ldagent.tap(150,348)
                    time.sleep(TIME_SLEEP)
                    continue
                ldagent.tap(150,313)
                time.sleep(TIME_SLEEP)
                continue

            if state.startswith('xxx-gacha-02-'):
                ldagent.tap(275,378)
                time.sleep(TIME_SLEEP)
                continue

            if state.startswith('xxx-gacha-03-'):
                ldagent.swipe(20,231,280,231,SWIPE_PACK_MS)
                flag_set.add('xxx-gacha-03')
                time.sleep(TIME_SLEEP)
                continue

            if state == 'xxx-gacha-04':
                ldagent.tap(275,378)
                flag_set.add('xxx-gacha-03')
                time.sleep(TIME_SLEEP)
                continue
            if state == 'xxx-gacha-04-x':
                ldagent.tap(275,378)
                flag_set.add('xxx-gacha-03')
                time.sleep(TIME_SLEEP)
                continue

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
                # if set(gacha_result) & TARGET_CARD_SET:
                #     sys.exit(0)
                all_wonder = gacha_result
                all_wonder = map(is_wonder, all_wonder)
                all_wonder = all(all_wonder)
                logger.debug(f'ZQFNRKRJXO all_wonder: {all_wonder}')
                # if all_wonder:
                #     logger.debug(f'KGGOWYOTZH WONDER_RARE_PACK: {t}')
                #     if config_data['STOP_AT_WONDER_RARE_PACK']:
                #         sys.exit(0)
                all_rare = gacha_result
                all_rare = map(is_rare, all_rare)
                all_rare = all(all_rare)
                logger.debug(f'CJAIBNJRCL all_rare: {all_rare}')
                # if all_rare:
                #     logger.debug(f'DESRVSSAZQ NONWONDER_RARE_PACK: {t}')
                #     if config.data['STOP_AT_NONWONDER_RARE_PACK']:
                #         sys.exit(0)

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

                ldagent.tap(150,377)
                time.sleep(TIME_SLEEP)
                continue

            if state == 'xxx-home':
                if TARGET_PACK in ['charizard', 'pikachu', 'mewtwo']:
                    ldagent.tap(185,154)
                if TARGET_PACK == 'mew':
                    ldagent.tap(111,154)
                time.sleep(TIME_SLEEP)
                continue

            if state == 'xxx-msg':
                ldagent.tap(150,200)
                time.sleep(TIME_SLEEP)
                continue

            if state == 'xxx-noitem':
                ldagent.tap(100,280)
                time.sleep(TIME_SLEEP)
                continue

            if state == 'xxx-swipeup':
                ldagent.tap(275,378)
                flag_set.add(state)
                time.sleep(TIME_SLEEP)
                continue

            if state.startswith('xxx-tips'):
                ldagent.tap(150,377)
                time.sleep(TIME_SLEEP)
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

        # if state == 'center':
        #     ldagent.tap(150,200)
        #     time.sleep(TIME_SLEEP)
        #     continue
        # if state == 'skip':
        #     ldagent.tap(275,378)
        #     time.sleep(TIME_SLEEP)
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
    

if __name__ == '__main__':
    main()
