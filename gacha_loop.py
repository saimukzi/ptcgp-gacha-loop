import common
import filelock
import my_path
import os
import random
import sys
import time
import windows_capture_process
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
import shutil

def main():
    global ALLOW_PLATINMODS_SPEED_3_STATE_SET
    parser = argparse.ArgumentParser(description='Gacha loop')
    parser.add_argument('config', type=str, default=None, nargs='?')
    parser.add_argument('--version', action='store_true')
    args = parser.parse_args()

    if args.version:
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
    logger.debug(f'HCJDEXBAEZ INSTANCE_ID={INSTANCE_ID}')

    TARGET_PACK = config_data['TARGET_PACK']
    TARGET_CARD_SET = set(config_data['TARGET_CARD_LIST'])
    USERNAME = config_data['USERNAME']

    START_YYYYMMDDHHMMSS = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
    MY_PID = os.getpid()

    SWIPE_PACK_MS = int(config_data['SWIPE_PACK_SEC'] * 1000)
    SWIPE_UP_SEC = int(config_data['SWIPE_UP_SEC'] * 1000)

    config_fn_lock_path = get_config_fn_lock_path(args_config)
    logger.debug(f'UKKDANILYL config_fn_lock_path={config_fn_lock_path}')
    config_fn_lock = filelock.lock(config_fn_lock_path, f'{START_YYYYMMDDHHMMSS},{MY_PID}')
    if config_fn_lock is None:
        logger.error(f'config file is locked: {args_config}')
        sys.exit(1)

    instance_lock_path = get_instance_lock_path()
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
    
    my_path.makedirs()

    state_list.STATE_DETECT_THRESHOLD = float(config_data['STATE_DETECT_THRESHOLD'])

    force_resetapp = False
    force_rebootemu = False
    force_killapp = False
    force_copyemu_resetapp = False
    force_copyemu_name = None

    INSTANCE_VAR_FOLDER = my_path.instance_var()
    USER_IDX_PATH = os.path.join(INSTANCE_VAR_FOLDER, 'user_idx.txt')
    user_idx = 0
    try:
        if os.path.exists(USER_IDX_PATH):
            with open(USER_IDX_PATH, 'r') as f:
                user_idx = int(f.read())
    except:
        logger.error(f'DKZEUSMNFN user_idx load error')
        user_idx = 0

    my_ldagent = ldagent.get_ldagent(config_data)

    check_disk_space(config_data)

    ret = my_ldagent.lock_emu()
    if not ret:
        logger.error(f'FYPBSVTUKY emu is locked')
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
    state_double_act_time = 0
    def avoid_double_act():
        nonlocal state_double_act_state
        nonlocal state_double_act_time
        if state_history[-1] == state:
            if state_double_act_state != state:
                state_double_act_state = state
                state_double_act_time = time.time()
            if time.time() - state_double_act_time < 1:
                logger.debug(f'YLLQZHFCHD avoid_double_act state={state}')
                return True
            state_double_act_state = None
            logger.debug(f'BBYLQOAYDP avoid_double_act pass state={state}')
        else:
            time.sleep(1.1/30) # one frame avoid first click too quick
        return False

    platinmods_speed = None
    allow_platinmods_speed_3 = False
    target_platinmods_speed = 3
    target_platinmods_speed_1_timer = None
    platinmods_menu_enable_time = 0
    last_swipe_time = 0

    ALLOW_PLATINMODS_SPEED_3_STATE_SET |= state_list.state_prefix('xxx-gacha')

    last_set_wait_state_args = None
    state_mask_set = None
    state_mask_timeout = None
    def set_wait_state(wait_set, timeout=None):
        nonlocal last_set_wait_state_args
        nonlocal state_mask_set
        nonlocal state_mask_timeout
        set_wait_state_args = (wait_set,timeout)
        if wait_set is None:
            state_mask_set = None
        else:
            state_mask_set = set(wait_set)
        if timeout is None:
            state_mask_timeout = None
        else:
            if set_wait_state_args != last_set_wait_state_args:
                state_mask_timeout = time.time()+timeout
        last_set_wait_state_args = set_wait_state_args

    # in long UNKNOWN, give up state_mask_set
    unknown_time = None
    unknown_check_pid_done = False
    # in long stable state, give up state_mask_set, flag_set
    stable_state = None
    stable_time = None
    # giveup time
    last_giveup_time = 0

    state_delay_state = None
    state_delay_time = 0
    def avoid_state_delay_state():
        nonlocal state_delay_state
        nonlocal state_delay_time
        if state_delay_state != state or state_history[-1] != state:
            state_delay_state = state
            state_delay_time = time.time()
        if time.time() - state_delay_time < 1:
            logger.debug(f'EUUCQCFRYP avoid state_delay state={state}')
            return True
        logger.debug(f'NRXLYRQKCM force accept state={state}')
        state_delay_state = None
        return False

    # in xxx-gacha-04, with pm, if time too long, go normal speed
    xxxgacha03_start_time = None

    S11_HOURGLASS_00_NOHAND = common.load_img_matcher(
        os.path.join(const.MY_PATH, 'res', 's11-hourglass-00', 'nohand.max.png'),
        os.path.join(const.MY_PATH, 'res', 's11-hourglass-00', 'nohand.min.png'),
        os.path.join(const.MY_PATH, 'res', 's11-hourglass-00', 'nohand.svmax.png'),
        os.path.join(const.MY_PATH, 'res', 's11-hourglass-00', 'nohand.svmin.png'),
        os.path.join(const.MY_PATH, 'res', 's11-hourglass-00', 'nohand.mask.png'),
        state_list_mask255f,
    )

    last_gacha_result = None

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
                if not my_ldagent.killapp():
                    if config_data['ENABLE_REBOOT']:
                        force_rebootemu = True
                    continue
                emu_ok = False
                if not my_ldagent.resetapp():
                    if config_data['ENABLE_REBOOT']:
                        force_rebootemu = True
                    continue
                allow_platinmods_speed_3 = False
                force_killapp = False
                check_cycle_last_reset = time.time()
                force_resetapp = False
                continue

            if force_killapp:
                logger.debug(f'NFTCLCTTHC force_killapp')
                if not my_ldagent.killapp():
                    continue
                emu_ok = False
                force_killapp = False
                continue

            # the bot did not finish the cycle of "create account" -> "gacha" -> "remove account"
            # there must be something wrong
            # force reset app to avoid infinite loop
            if (config_data['CHECK_CYCLE_SECONDS'] is not None) and (time.time() - check_cycle_last_reset > config_data['CHECK_CYCLE_SECONDS']):
                logger.warning(f'PNOCLZOWIW cycle timeout')
                write_warning_img(img)
                check_cycle_last_reset = time.time()
                force_resetapp = True
                continue

            if not emu_ok:
                logger.debug(f'URNYXLHHXQ recover emu')
                my_ldagent.recover()
                emu_ok = True
                flag_set = set()
                state_mask_set = None
                state_history = ['UNKNOWN']*10
                platinmods_speed = None
                target_platinmods_speed = 1
                continue

            if state != 'UNKNOWN':
                state_history.append(state)
            state_history = state_history[-5:]

            #my_ldagent.keep_process_alive()
            try:
                img, img_mask = my_ldagent.screencap()
            except windows_capture_process.ProcessDownException:
                logger.debug('QPMFTJDLMP ProcessDownException')
                my_ldagent.keep_process_alive()
                continue
            except windows_capture_process.RPCTimeoutException:
                logger.debug('OVKEDBSEUP RPCTimeoutException')
                if config_data['ENABLE_REBOOT']:
                    force_rebootemu = True
                continue
            except windows_capture_process.FrameTimeoutException:
                logger.debug('OGTZBUNCSJ FrameTimeoutException')
                if config_data['ENABLE_REBOOT']:
                    force_rebootemu = True
                continue
            img = img.astype(np.float32)

            if state_mask_set is not None:
                _state_mask_set = set(state_mask_set)
                if time.time() - platinmods_menu_enable_time < 3:
                    _state_mask_set.add('platinmods-menu-1')
                    _state_mask_set.add('platinmods-menu-2')
                    _state_mask_set.add('platinmods-menu-3')
            else:
                _state_mask_set = None
            logger.debug(f'JMKSJZGZVD state_mask_set={state_mask_set}')
            logger.debug(f'FGFDLRKKFP _state_mask_set={_state_mask_set}')
            state = state_list.get_state(img, img_mask, _state_mask_set)
            if state_double_act_state != state:
                state_double_act_state = None
            if state_delay_state != state:
                state_delay_state = None

            if state == 'UNKNOWN':
                if unknown_time is None:
                    unknown_time = time.time()
                if time.time() - unknown_time > 10:
                    if (state_mask_timeout is None) or (time.time()>state_mask_timeout):
                        logger.warning(f'FTLJDAXKYE long UNKNOWN, give up state_mask_set')
                        if time.time() - last_giveup_time > 10:
                            write_warning_img(img)
                            state_mask_set = None
                            flag_set = set()
                            last_giveup_time = time.time()
                        if not unknown_check_pid_done:
                            if my_ldagent.get_pid() is None:
                                logger.warning(f'TMLOUKGSMO app not running, force resetapp')
                                force_resetapp = True
                                continue
                            unknown_check_pid_done = True
                    else:
                        logger.debug('WTRWLSZEJT state_mask_timeout')
            else:
                unknown_time = None
                unknown_check_pid_done = False

            if state == stable_state:
                if time.time() - stable_time > 30:
                    if (state_mask_timeout is None) or (time.time()>state_mask_timeout):
                        logger.warning(f'KOROVAKOML long stable state, give up state_mask_set, flag_set')
                        if time.time() - last_giveup_time > 10:
                            write_warning_img(img)
                            state_mask_set = None
                            flag_set = set()
                            last_giveup_time = time.time()
                    else:
                        logger.debug('RTMSNSWYYJ state_mask_timeout')
            else:
                stable_state = state
                stable_time = time.time()

            if my_ldagent.screencap_require_calibrate():
                logger.debug(f'YKLZVQOJNZ screencap_require_calibrate')
                if state in state_list.state_to_calibrate_mask_hwaf1_dict:
                    calibrate_mask_hwaf1 = state_list.state_to_calibrate_mask_hwaf1_dict[state]
                    my_ldagent.calibrate_screencap(calibrate_mask_hwaf1)
                    continue

            # reset_mywait()

            if state == 'xxx-gacha-05-U':
                state = 'UNKNOWN'

            if config_data['DEBUG_IMG']:
                logger.debug(f'CNRSFFOMKV debug_img_idx={debug_img_idx}, state={state}')
                debug_img_fn = os.path.join(my_path.instance_debug(), 'img_history', '%03d.png'%debug_img_idx)
                os.makedirs(os.path.dirname(debug_img_fn), exist_ok=True)
                try:
                    common.cv2_imwrite(debug_img_fn, img)
                except:
                    pass
                debug_img_idx += 1
                debug_img_idx %= 1000

            logger.debug(f'PSDLSJCDBB state_history={state_history}')
            logger.debug(f'WJPUTEHGOE state={state}')
            logger.debug(f'YAISJIINTI flag_set={flag_set}')

            if state == 'xxx-gacha-05-U':
                state = 'UNKNOWN'

            if (config_data['ENABLE_PLATINMODS']):
                if (not allow_platinmods_speed_3) and (state in ALLOW_PLATINMODS_SPEED_3_STATE_SET):
                    allow_platinmods_speed_3 = True

                # s06-gacha1-04: first swipe up
                # xxx-gacha-03-: open pack
                # s03-start-01-skip-anime: create acc first anime
                # last_swipe_time: may retry swipe
                # xxxgacha03_start_time: open pack first 1 sec
                # xxxgacha03_start_time: open pack after 10 sec, may have video
                if  (not allow_platinmods_speed_3) \
                    or (state in ['s06-gacha1-04']) \
                    or (state.startswith('xxx-gacha-03-')) \
                    or (xxxgacha03_start_time is not None and time.time()-xxxgacha03_start_time<1) \
                    or ('s03-start-01-skip-anime' in flag_set) \
                    or (time.time()-last_swipe_time<1) \
                    or (xxxgacha03_start_time is not None and time.time()-xxxgacha03_start_time>10 and 'xxx-gacha-03-after' in flag_set):
                    target_platinmods_speed = 1
                    target_platinmods_speed_1_timer = time.time()
                elif state.startswith('platinmods-menu-'):
                    # avoid pm mod menu remain in screen and flip
                    pass
                elif (target_platinmods_speed_1_timer is not None and state == 'UNKNOWN' and time.time()-target_platinmods_speed_1_timer<2):
                    # avoid pm mod menu remain in screen and flip
                    pass
                else:
                    target_platinmods_speed = 3
                    target_platinmods_speed_1_timer = None

                logger.debug(f'AIVEEZCDJS platinmods_speed={platinmods_speed} target_platinmods_speed={target_platinmods_speed}')

                if state == 'platinmods-menu-1':
                    platinmods_speed = 1
                if state == 'platinmods-menu-2':
                    platinmods_speed = 2
                if state == 'platinmods-menu-3':
                    platinmods_speed = 3
                if (target_platinmods_speed != platinmods_speed):
                    platinmods_menu_enable_time = time.time()
                    if not state.startswith('platinmods-menu-'):
                        my_ldagent.tap(18, 125)
                        continue
                    if target_platinmods_speed == 1:
                        my_ldagent.tap(35, 214)
                        continue
                    if target_platinmods_speed == 2:
                        my_ldagent.tap(109, 214)
                        continue
                    if target_platinmods_speed == 3:
                        my_ldagent.tap(182, 214)
                        continue
                if (target_platinmods_speed == platinmods_speed):
                    if state.startswith('platinmods-menu-'):
                        if avoid_double_act(): continue
                        my_ldagent.tap(170, 324)
                        continue
                    
            logger.debug(f'IWFCYLNYDB state={state} flag_set={flag_set}')

            if state == 'err-launch-00':
                force_resetapp = True
                continue

            if state == 'err-launch-01':
                force_resetapp = True
                continue

            if state == 'err-nostoredata':
                force_resetapp = True
                continue

            if state.startswith('xxx-dialog-b'):
                logger.debug(f'ZDMLKMCYPA reset state_mask_set/flag_set on state={state}')
                state_mask_set = None
                flag_set = set()

            if state == 's00-cover':
                check_disk_space(config_data)

                s99_done = 's99_done' in flag_set

                flag_set = set()

                # [ZRTRNAFFLV] restart emu to free memory
                if      config_data['ENABLE_REBOOT'] \
                    and (config_data['FREEMEM_SECONDS'] is not None) \
                    and (time.time() - freemem_last_reset > config_data['FREEMEM_SECONDS']):
                    logger.debug(f'OOHKRSARJM freemem')
                    force_rebootemu = True
                    continue
                    
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                if s99_done:
                    flag_set.add('s99_done')
                    set_wait_state({state,'s01-info-00'})
                else:
                    set_wait_state(None)
                continue

            if state == 's01-info-00':
                flag_set.discard('s99_done')
                if avoid_double_act(): continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s01-info-01'})
                continue

            if state == 's01-info-01':
                if avoid_double_act(): continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s01-info-02'})
                continue

            if state == 's01-info-02':
                if avoid_double_act(): continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s01-info-03'})
                continue

            if state == 's01-info-03':
                if avoid_double_act(): continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s01-info-04','s01-info-05'})
                continue

            if state == 's01-info-05':
                if avoid_double_act(): continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s01-info-06'})
                continue

            if state == 's01-info-06':
                if avoid_double_act(): continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s01-info-07'})
                continue

            if state == 's01-info-07':
                if avoid_double_act(): continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s01-info-04'})
                continue

            if state == 's01-info-04':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({'s02-toc-00','xxx-dialog-swc'}) 
                continue

            if state == 's02-toc-00':
                if avoid_double_act(): continue
                if check_cycle_loop_state in [None, 's12-end-00']:
                    logger.debug(f'JVUDJTQGFR check_cycle_loop_state={state}')
                    check_cycle_loop_state = state
                    check_cycle_last_reset = time.time()

                if 's02-toc-01' not in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    set_wait_state({'s02-toc-01'})
                    continue
                flag_set.discard('s02-toc-01')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                set_wait_state({state,'s02-toc-02'})
                continue

            if state == 's02-toc-01':
                if avoid_double_act(): continue
                flag_set.add(state)
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s02-toc-00','s02-toc-02'})
                continue

            if state == 's02-toc-02':
                if avoid_double_act(): continue
                if 's02-toc-01' not in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    set_wait_state({state,'s02-toc-01'})
                    continue
                flag_set.discard('s02-toc-01')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                set_wait_state({state,'s02-toc-04'})
                continue

            if state == 's02-toc-04':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s03-start-00'})
                continue

            if state == 's03-start-00':
                if avoid_double_act(): continue
                if check_cycle_loop_state in [None, 's02-toc-00']:
                    logger.debug(f'JVUDJTQGFR check_cycle_loop_state={state}')
                    check_cycle_loop_state = state
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s03-start-01'})
                continue

            if state == 's03-start-01':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                flag_set.add('s03-start-01-skip-anime')
                set_wait_state({'s03-start-01','xxx-dialog-swc', 'xxx-dialog-sc', 'xxx-dialog-lw','s04-welcome-00'}, timeout=120)
                continue

            if 's03-start-01-skip-anime' in flag_set:
                # playing fking opening animation
                if state not in {'s03-start-01', 'xxx-dialog-swc', 'xxx-dialog-sc', 'xxx-dialog-lw','s04-welcome-00'}:
                    my_ldagent.tap(275,378)
                    my_ldagent.tap(275,378)
                    continue
                if state in {'s03-start-01', 's04-welcome-00'}:
                    flag_set.discard('s03-start-01-skip-anime')

            if state == 's04-welcome-00':
                flag_set.discard('s03-start-01-skip-anime')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({'xxx-dialog-lwc','s05-name-00'})
                continue

            if state == 's05-name-00':
                if avoid_double_act(): continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s05-name-01'})
                continue

            if state == 's05-name-01':
                if avoid_double_act(): continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s05-name-02','s05-name-02-empty'})
                continue

            if state == 's05-name-02':
                for _ in range(10):
                    my_ldagent.keyevent(67)
                    time.sleep(0.2) # speed of typing
                set_wait_state({state,'s05-name-02-empty'})
                continue

            if state == 's05-name-02-empty':
                flag_set.discard('s05-name-err')
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
                set_wait_state({'s05-name-03'})
                continue

            if state == 's05-name-03':
                if avoid_double_act(): continue
                if 's05-name-err' in flag_set:
                    for _ in range(10):
                        my_ldagent.keyevent(67)
                        time.sleep(0.2) # speed of typing
                    set_wait_state({state,'s05-name-02-empty'})
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                flag_set.add('s05-name')
                set_wait_state({state,'s05-name-04','xxx-dialog-bsc','s05-name-06'})
                continue # possible error msg here

            if state == 's05-name-06':
                if avoid_double_act(): continue
                if 's05-name-err' in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    set_wait_state({state,'s05-name-03'})
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                flag_set.add('s05-name')
                set_wait_state({state,'s05-name-04','xxx-dialog-bsc'})
                continue # possible error msg here

            if state == 's05-name-04':
                if avoid_double_act(): continue
                if 's05-name-err' in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    set_wait_state({'s05-name-01'})
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                flag_set.add('s05-name')
                set_wait_state({state,'s05-name-05','xxx-dialog-bsc'})
                continue # possible error msg here

            if state == 's05-name-05':
                if avoid_double_act(): continue
                if 's05-name-err' in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    set_wait_state({'s05-name-04'})
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                flag_set.add('s05-name-05-after')
                set_wait_state({state,'s06-gacha1-00','xxx-dialog-bsc'})
                continue

            if 's05-name' in flag_set:
                if state in ['xxx-dialog-bsc']:
                    flag_set.add('s05-name-err')
                    flag_set.discard('s05-name-05-after')

            if 's05-name-05-after' in flag_set:
                if state not in {'s06-gacha1-00','xxx-dialog-bsc'}:
                    my_ldagent.tap(10,10)
                    continue

            if state == 's06-gacha1-00':
                flag_set.discard('s05-name')
                flag_set.discard('s05-name-05-after')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({'s06-gacha1-01'})
                continue

            if state == 's06-gacha1-01':
                # [FIRST_SWIPE_UP_KILL_APP] kill app to avoid lock in swipe state
                if config_data['FIRST_SWIPE_UP_KILL_APP']:
                    flag_set.add('FIRST_SWIPE_UP_KILL_APP')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                flag_set.add('s06-gacha1-01-after')
                set_wait_state(state_list.state_prefix('xxx-gacha-03-'),timeout=20)
                continue

            # 's06-gacha1-03' spam
            # may delay to 'xxx-gacha-04'
            # may back to 'xxx-gacha-03-mewtwo'
            if  (flag_set.issuperset({'s06-gacha1-01-after','xxx-gacha-03-after'})) or \
                state == 's06-gacha1-03':
                if (state not in {'s06-gacha1-04'}) and (not state.startswith('xxx-gacha-03-')):
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist['s06-gacha1-03']['xy_list']))
                    continue
                else:
                    flag_set.discard('s06-gacha1-01-after')
                    flag_set.discard('xxx-gacha-03-after')
                    xxxgacha03_start_time = None
            
            # swipe up hell
            if state == 's06-gacha1-04':
                flag_set.discard('s06-gacha1-01-after')
                flag_set.discard('xxx-gacha-03-after')
                xxxgacha03_start_time = None
                action = state_list.state_to_action_dist[state]
                from_xy = _get_xy(action['from_xy_list'])
                to_xy = _get_xy(action['to_xy_list'])
                my_ldagent.swipe(*from_xy, *to_xy, SWIPE_UP_SEC)
                set_wait_state({state,'xxx-msg','s06-gacha1-06'}, timeout=20)
                continue

            # may delay to 'xxx-msg' and back
            if state == 's06-gacha1-06':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-msg','s06-gacha1-07'}, timeout=20)
                continue

            # move card in diff angle
            if state == 's06-gacha1-07':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-dialog-swc','s07-mission-00'})
                continue # long unknown stupid wait

            if state == 's07-mission-00':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-msg','s07-mission-02'})
                continue

            # may delay to 'xxx-msg' and back
            if state == 's07-mission-02':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-msg','s07-mission-03'})
                continue

            if state == 's07-mission-03':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s07-mission-04'})
                continue

            if state == 's07-mission-04':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-msg','s08-gacha2-02'})
                continue


            if state == 's08-gacha2-02':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s08-gacha2-04','xxx-dialog-lc'})
                continue

            if state == 's08-gacha2-04':
                flag_set.add('GACHA2-ING')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                flag_set.add('xxx-gacha-02-spam')
                set_wait_state({'xxx-gacha-02-mewtwo','xxx-gacha-03-mewtwo'},timeout=20)
                continue


            if state == 's09-wonder-00':
                flag_set.discard('xxx-cardlist-spam')
                # double click may skip 's09-wonder-01', just do it
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s09-wonder-01','xxx-msg','s09-wonder-04'})
                continue

            if state == 's09-wonder-01':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-msg','s09-wonder-04'})
                continue

            # may delay to 'xxx-msg' and back to 's09-wonder-04'
            if state == 's09-wonder-04':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-msg','s09-wonder-11','s07-mission-00'})
                continue

            # low msg
            if state == 's09-wonder-11':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-dialog-lw','xxx-dialog-lww','xxx-dialog-lwc','xxx-msg','s09-wonder-12'})
                continue

            # finger icon click wonder pack
            # may delay to 'xxx-dialog-lw' and back
            # may delay to 'xxx-msg' and back
            if state == 's09-wonder-12':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s09-wonder-13','xxx-dialog-lw','xxx-dialog-lww','xxx-dialog-lwc','xxx-msg'})
                continue

            # ok to wonder pack
            if state == 's09-wonder-13':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                flag_set.add('s09-wonder-13-after')
                set_wait_state({state,'s09-wonder-14'})
                continue

            # wonder shuffle SE skip btn
            if ('s09-wonder-13-after' in flag_set):
                if state != 's09-wonder-14':
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist['s09-wonder-23']['xy_list']))
                    continue

            # wonder 5 choose 1
            if state == 's09-wonder-14':
                # double click may skip 's09-wonder-15'
                if avoid_double_act(): continue
                flag_set.discard('s09-wonder-13-after')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s09-wonder-15'})
                continue

            # wonder result big card
            if state == 's09-wonder-15':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                flag_set.add('GACHA2-DONE')
                flag_set.add('WONDER-DONE')
                # if first gacha have cPK_20_000010_00_FUSHIGIDANE_AR
                # will direct to 's09-wonder-16'
                set_wait_state({state,'xxx-swipeup','s09-wonder-16'})
                continue

            # wonder result 5 cards
            if state == 's09-wonder-16':
                flag_set.discard('xxx-cardlist-spam')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-dialog-lw','xxx-dialog-lww','xxx-dialog-lwc','xxx-msg','xxx-home'})
                continue

            # dialog-lc
            # 若開包力用完了
            if state == 's11-hourglass-02':
                flag_set.add('GACHA4-DONE')
                flag_set.add('s11-hourglass')
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s11-hourglass-00','xxx-msg'})
                continue

            # click '開封一包'
            # may delay to 'xxx-msg', then back to 's11-hourglass-00'
            # in very rare case, click before xxx-msg appear may cause error
            if state == 's11-hourglass-00':
                # detect no hand
                if common.img_match(img, img_mask, S11_HOURGLASS_00_NOHAND) < 1:
                    continue
                if ('GACHA4-DONE' not in flag_set) or (state_history[-1] != 'xxx-msg'):
                    if avoid_state_delay_state(): continue
                flag_set.add('GACHA4-DONE')
                # btn 開封1包
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-msg','xxx-dialog-lw','xxx-dialog-lwc','s11-hourglass-01'})
                continue

            # click use hourglass to open pack, btn ok
            # may delay to 'xxx-msg', then back to 's11-hourglass-00'
            # may delay to 'xxx-dialog-lw', then back to 's11-hourglass-00'
            if state == 's11-hourglass-01':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                flag_set.add('xxx-gacha-02-spam')
                flag_set.discard('GACHA4-DONE')
                flag_set.add('GACHA5-ING')
                set_wait_state(state_list.state_prefix('xxx-gacha-02-')|state_list.state_prefix('xxx-gacha-03-')|{state,'xxx-msg','xxx-dialog-lw','xxx-dialog-lwc'},timeout=20)
                continue

            # no energy
            # no double click
            if state == 's12-end-00':
                if avoid_double_act(): continue
                flag_set.discard('xxx-cardlist-spam')
                flag_set.add('GACHA5-DONE') # mark energy burn out
                if check_cycle_loop_state in [None, 's03-start-00']:
                    logger.debug(f'JVUDJTQGFR check_cycle_loop_state={state}')
                    check_cycle_loop_state = state
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'s12-end-01'})
                continue

            # menu appear, click other
            # double click ok, avoided next state
            if state == 's12-end-01':
                if 'GACHA5-DONE' in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'G_xy_list']))
                    set_wait_state({state,'s12-end-02'})
                    continue
                else:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'R_xy_list']))
                    set_wait_state(None)
                    continue
            flag_set.discard('s12-end-01-remain')

            # menu > other appear, click acc
            # G double click ok, avoided next state
            if state == 's12-end-02':
                if 'GACHA5-DONE' in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'G_xy_list']))
                    set_wait_state({state,'s12-end-03'})
                    continue
                else:
                    if avoid_double_act(): continue
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'R_xy_list']))
                    set_wait_state(None)
                    continue
            flag_set.discard('s12-end-02-remain')

            # menu > acc, click del
            # G double click ok, avoided next state
            if state == 's12-end-03':
                if avoid_double_act(): continue
                if 'GACHA5-DONE' in flag_set:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'G_xy_list']))
                    set_wait_state({state,'xxx-dialog-lwr','xxx-dialog-swr','xxx-dialog-sc','s00-cover'},timeout=20)
                    flag_set.add('s99_done')
                    continue
                else:
                    if avoid_double_act(): continue
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'R_xy_list']))
                    set_wait_state(None)
                    continue

            if 'xxx-gacha-00-before-spam' in flag_set:
                if (not state.startswith('xxx-gacha-00-')) and \
                    state not in {'xxx-home','xxx-msg','xxx-dialog-lw','xxx-dialog-lww','xxx-dialog-lwc'}:
                    my_ldagent.tap(10,10)
                    continue
                else:
                    flag_set.discard('xxx-gacha-00-before-spam')

            # may auto delay to new pack notification
            if state.startswith('xxx-gacha-00-'):
                flag_set.discard('xxx-gacha-00-before-spam')

                state_pack = state[13:]
                color = XXX_GACHA_00_STATE_TARGET_TO_COLOR_DICT[(state_pack, TARGET_PACK)]
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state][f'{color}_xy_list']))

                next_state_set = {state}
                if color == 'R':
                    next_state_set.add('xxx-home')
                if color == 'G':
                    next_state_set.add(f'xxx-gacha-01-{state_pack}')
                set_wait_state(next_state_set)
                continue

            # may delay to s11-hourglass-02
            if state.startswith('xxx-gacha-01-'):
                flag_set.discard('xxx-cardlist-spam')
                # may delay to s11-hourglass-02
                if match_state_mask_set('s11-hourglass-02', state_mask_set):
                    if avoid_state_delay_state(): continue
                state_pack = state[13:]
                if state_pack != TARGET_PACK:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    set_wait_state({f'xxx-gacha-00-{state_pack}','s11-hourglass-02'})
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                flag_set.add('xxx-gacha-02-spam')
                for i in range(6):
                    if f'GACHA{i}-DONE' in flag_set:
                        flag_set.discard(f'GACHA{i}-DONE')
                        flag_set.add(f'GACHA{i+1}-ING')
                set_wait_state({state,f'xxx-gacha-02-{state_pack}',f'xxx-gacha-03-{state_pack}'},timeout=20)
                continue

            # may delay to s11-hourglass-00
            if state.startswith('xxx-gacha-06-'):
                flag_set.discard('xxx-cardlist-spam')
                # may delay to s11-hourglass-02
                if match_state_mask_set('s11-hourglass-00', state_mask_set):
                    if avoid_state_delay_state(): continue
                state_pack = state[13:]
                if state_pack != TARGET_PACK:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['R_xy_list']))
                    set_wait_state({f'xxx-gacha-00-{state_pack}','s11-hourglass-02'})
                    continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                flag_set.add('xxx-gacha-02-spam')
                for i in range(6):
                    if f'GACHA{i}-DONE' in flag_set:
                        flag_set.discard(f'GACHA{i}-DONE')
                        flag_set.add(f'GACHA{i+1}-ING')
                set_wait_state({state,f'xxx-gacha-02-{state_pack}',f'xxx-gacha-03-{state_pack}'},timeout=20)
                continue

            # gacha pack, fly in animation
            if 'xxx-gacha-02-spam' in flag_set:
                # case from 's11-hourglass-01'
                if  (not state.startswith('xxx-gacha-01-')) and \
                    (not state.startswith('xxx-gacha-03-')) and \
                    (state not in {'xxx-msg','xxx-dialog-lw','xxx-dialog-lwc'}):
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist['xxx-gacha-02-pikachu']['xy_list']))
                    flag_set.add('xxx-gacha-02-after')
                    continue
                else:
                    flag_set.discard('xxx-gacha-02-spam')

            # gacha pack, choose from ring
            if state.startswith('xxx-gacha-02-'):
                state_pack = state[13:]
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                flag_set.add('xxx-gacha-02-after')
                set_wait_state(state_list.state_prefix('xxx-gacha-03-'))
                continue

            # gacha pack, swipe right
            # src: s06-gacha1-01, xxx-gacha-02-*
            if state.startswith('xxx-gacha-03-'):
                flag_set.discard('xxx-gacha-02-spam')
                # [FIRST_SWIPE_UP_KILL_APP] kill app to avoid lock in swipe state
                if 'FIRST_SWIPE_UP_KILL_APP' in flag_set:
                    force_killapp = True
                    continue
                action = state_list.state_to_action_dist[state]
                from_xy = _get_xy(action['from_xy_list'])
                to_xy = _get_xy(action['to_xy_list'])
                my_ldagent.swipe(*from_xy, *to_xy, SWIPE_PACK_MS)
                last_swipe_time = time.time()
                flag_set.add('xxx-gacha-03-after')
                xxxgacha03_start_time = time.time()
                next_state_set = {state}
                if 'GACHA1-ING' in flag_set:
                    next_state_set.add('s06-gacha1-04') # spam 's06-gacha1-03'
                elif {'GACHA2-ING','GACHA3-ING','GACHA4-ING','GACHA5-ING'} & flag_set:
                    next_state_set.add('xxx-gacha-05') # spam 'xxx-gacha-04*'
                else:
                    next_state_set.add('s06-gacha1-03')
                    next_state_set.add('s06-gacha1-04')
                    next_state_set.add('xxx-gacha-04')
                    next_state_set.add('xxx-gacha-05')
                set_wait_state(next_state_set, timeout=60)
                continue # swipe may fail

            # gacha pack, after swipe, show one by one
            # 'xxx-gacha-04' / 'xxx-gacha-04-x'
            # may back to 'xxx-gacha-03-*'
            if  (flag_set.issuperset({'xxx-gacha-02-after','xxx-gacha-03-after'})) or \
                state in {'xxx-gacha-04'}:
                if state not in {'xxx-gacha-05'}:
                    my_ldagent.tap(150,304)
                    my_ldagent.tap(281,381)
                    my_ldagent.tap(281,381)
                    continue
                else:
                    flag_set.discard('xxx-gacha-02-after')
                    flag_set.discard('xxx-gacha-03-after')
                    xxxgacha03_start_time = None

            # gacha result
            if state == 'xxx-gacha-05':
                flag_set.discard('xxx-gacha-02-after')
                flag_set.discard('xxx-gacha-03-after')
                xxxgacha03_start_time = None

                for i in range(2,6):
                    if f'GACHA{i}-ING' in flag_set:
                        flag_set.discard(f'GACHA{i}-ING')
                        flag_set.add(f'GACHA{i}-DONE')

                t = int(time.time())
                logger.debug(f'ZNHRHBHGMT GACHA_RESULT: {t}')
                instance_id = config_data['INSTANCE_ID']
                ret_fn = os.path.join(my_path.instance_debug(), 'gacha_result', f'{t}-{instance_id}.png')
                common.cv2_imwrite(ret_fn, img)

                gacha_result = card_list.read_gacha_result(img)

                if gacha_result == 'GRAY':
                    state = 'xxx-gacha-05-gray'
                    logger.warning('GACHA_RESULT: GRAY')
                    continue

                check_disk_space(config_data)

                # 20250116-2344: I saw it let a leaf get away, very sus
                # possible first click no response
                if (state != state_history[-1]) and (gacha_result!=last_gacha_result):
                    ret_fn = os.path.join(my_path.global_gacha_result(), f'{t}-{instance_id}.png')
                    common.cv2_imwrite(ret_fn, img)

                    last_gacha_result = gacha_result
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
                        logger.debug(f'PUOWNPVFXS BACKUP {t}')
                        ret_fn = os.path.join(my_path.global_bingo(), f'{t}-{instance_id}.png')
                        common.cv2_imwrite(ret_fn, img)
                        force_copyemu_name = config_data['LD_EMU_NAME'] + '-' + str(t)
                        force_copyemu_resetapp = True
                        check_cycle_last_reset = time.time()
                        continue

                    exist_cost4 = any(map(is_cost4, gacha_result))
                    logger.debug(f'DBGPBUKKWV exist_cost4: {exist_cost4}')

                    # when it is cost-4 pack, reset app without remove account
                    # let other player to get the wonder pack
                    if config_data['WONDER_SAINT'] and exist_cost4 and all_wonder:
                        logger.debug(f'KRVQOASGCP WONDER_SAINT')
                        flag_set.add('WONDER_SAINT')

                    if ('WONDER_SAINT' in flag_set) and ('s11-hourglass' in flag_set):
                        logger.debug(f'TDODGWPXQR WONDER_SAINT force_resetapp')
                        force_resetapp = True
                        check_cycle_last_reset = time.time()
                        continue
                else:
                    logger.debug(f'EWUJYXTFAN same state, should be double click')

                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                next_state_set = {state}
                if 'GACHA2-DONE' in flag_set:
                    next_state_set.add('xxx-swipeup')
                elif 'GACHA3-DONE' in flag_set:
                    next_state_set.add('xxx-tips16')
                elif 'GACHA4-DONE' in flag_set:
                    next_state_set.add('xxx-swipeup')
                elif 'GACHA5-DONE' in flag_set:
                    next_state_set.add('xxx-tips25')
                else:
                    next_state_set.add('xxx-tips16')
                    next_state_set.add('xxx-swipeup')
                    next_state_set.add('xxx-tips25')
                set_wait_state(next_state_set, timeout=20)
                continue

            # from 's09-wonder-16', delay to 'xxx-msg','xxx-dialog-l*' and back
            if state == 'xxx-home':
                if TARGET_PACK in ['charizard', 'pikachu', 'mewtwo']:
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['RB_xy_list']))
                if TARGET_PACK == 'mew':
                    my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['G_xy_list']))
                flag_set.add('xxx-gacha-00-before-spam')

                set_wait_state({state,'xxx-msg','xxx-dialog-lw','xxx-dialog-lww','xxx-dialog-lwc'}|state_list.state_prefix('xxx-gacha-00-'))
                continue

            if state == 'xxx-swipeup':
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))

                next_state_set = {state,'xxx-cont','xxx-cardlist'}
                if 'GACHA2-DONE' in flag_set:
                    if not 'WONDER-DONE' in flag_set:
                        next_state_set.add('s09-wonder-00')
                    else:
                        next_state_set.add('s09-wonder-16')
                elif 'GACHA3-DONE' in flag_set:
                    next_state_set |= state_list.state_prefix('xxx-gacha-01-')
                elif 'GACHA4-DONE' in flag_set:
                    next_state_set.add('s11-hourglass-02')
                elif 'GACHA5-DONE' in flag_set:
                    next_state_set.add('s12-end-00')
                else:
                    next_state_set |= {'s09-wonder-00','s09-wonder-16'}
                    next_state_set |= state_list.state_prefix('xxx-gacha-01-')
                    next_state_set.add('s11-hourglass-02')
                    next_state_set.add('s12-end-00')

                set_wait_state(next_state_set)
                continue
            
            if state == 'xxx-cardlist':
                if avoid_double_act(): continue
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist['xxx-cardlist']['xy_list']))
                next_state_set = {state,'xxx-cont'}
                if 'GACHA2-DONE' in flag_set:
                    if not 'WONDER-DONE' in flag_set:
                        next_state_set.add('s09-wonder-00')
                    else:
                        next_state_set.add('s09-wonder-16')
                elif 'GACHA3-DONE' in flag_set:
                    next_state_set |= state_list.state_prefix('xxx-gacha-01-')
                elif 'GACHA4-DONE' in flag_set:
                    next_state_set.add('s11-hourglass-02')
                elif 'GACHA5-DONE' in flag_set:
                    next_state_set.add('s12-end-00')
                else:
                    next_state_set |= {'s09-wonder-00','s09-wonder-16'}
                    next_state_set |= state_list.state_prefix('xxx-gacha-01-')
                    next_state_set.add('s11-hourglass-02')
                    next_state_set.add('s12-end-00')
                set_wait_state(next_state_set)
                continue

            # 'xxx-tips16' / 'xxx-tips25'
            if state.startswith('xxx-tips'):
                my_ldagent.tap(*_get_xy(state_list.state_to_action_dist[state]['xy_list']))
                set_wait_state({state,'xxx-swipeup'})
                continue

            if state in state_list.state_to_action_dist:
                if state not in {'xxx-msg','xxx-dialog-lw','xxx-dialog-lww'}:
                    if avoid_double_act(): continue
                action = state_list.state_to_action_dist[state]
                action_action = action['action']
                logger.debug(f'OLOWPQVZMD action={action_action}')
                if action['action'] == 'click':
                    xy = _get_xy(action['xy_list'])
                    my_ldagent.tap(*xy)
                    continue
                if action['action'] == 'swipe':
                    from_xy = _get_xy(action['from_xy_list'])
                    to_xy = _get_xy(action['to_xy_list'])
                    duration = int(action['duration'])
                    my_ldagent.swipe(*from_xy, *to_xy, duration)
                    last_swipe_time = time.time()
                    continue

        except ldagent.LdAgentException as e:
            logger.error(f'MYBPMBYDXK LdAgentException: {e}')
            if config_data['ENABLE_REBOOT']:
                force_rebootemu = True
            else:
                force_killapp = True


def match_state_mask_set(state,state_mask_set):
    if state_mask_set is None:
        return True
    if '-' in state_mask_set:
        return state not in state_mask_set
    else:
        return state in state_mask_set


def check_disk_space(config_data):
    if config_data['MIN_FREE_DISK_SPACE'] <= 0:
        return
    free_space = shutil.disk_usage(ldagent.get_ldplayer_path(config_data)).free
    if free_space < config_data['MIN_FREE_DISK_SPACE']:
        logger.error(f'XOCKTBIWKG not enough disk space: {free_space}')
        sys.exit(1)


def write_warning_img(img):
    if img is None:
        logger.warning(f'EVDFRJINGC write_warning_img: img is None')
        return
    img = img.astype(np.uint8)
    t = int(time.time())
    ret_fn = os.path.join(my_path.instance_debug(), 'warning_img', f'{t}.png')
    os.makedirs(os.path.dirname(ret_fn), exist_ok=True)
    logger.debug(f'CTXXIWQWYT write_warning_img: {ret_fn}')
    common.cv2_imwrite(ret_fn, img)


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

def get_instance_lock_path():
    return os.path.join(my_path.instance_var(), 'lock')

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

# download path with overspeed will cause download fail
# seeing following states means download successed
ALLOW_PLATINMODS_SPEED_3_STATE_SET = {
    's04-welcome-00',
    's05-name-00',
    's06-gacha1-00',
    's07-mission-00',
    's08-gacha2-02',
    's09-wonder-00',
    's10-tutorialend-00',
    's11-hourglass-00',
    's12-end-00',
    'xxx-gacha-00',
    'xxx-gacha-01',
}

if __name__ == '__main__':
    main()
